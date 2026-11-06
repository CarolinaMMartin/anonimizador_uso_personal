"""Assign one monotonic order to each successful public review action."""
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps

from app.models.schemas import Detection, SessionState


@dataclass
class _Action:
    state: SessionState
    initial_order: int
    affected: set[int] = field(default_factory=set)
    reviewed: bool = False


_actions: ContextVar[tuple[_Action, ...]] = ContextVar('review_actions', default=())


@contextmanager
def manual_action(state: SessionState):
    """Nested calls on the same session collect IDs until the outer action succeeds."""
    current = next((action for action in reversed(_actions.get()) if action.state is state), None)
    if current is not None:
        yield current
        return
    action = _Action(state, max(state.review_sequence,
                              max((d.manual_order for d in state.detections), default=0)))
    token = _actions.set((*_actions.get(), action))
    try:
        yield action
    except BaseException:
        # Public services validate before mutation. A failed action never
        # receives a review sequence or review flag.
        raise
    else:
        if action.reviewed:
            state.review_sequence = max(action.initial_order, state.review_sequence,
                                        max((d.manual_order for d in state.detections), default=0)) + 1
            for detection in state.detections:
                if detection.id in action.affected:
                    detection.manual_order = state.review_sequence
            state.has_review = True
    finally:
        _actions.reset(token)


def mark_manual_decision(state: SessionState, detections: Iterable[Detection | int] = ()) -> None:
    """Record affected identities; empty successful actions still count as review."""
    action = next((action for action in reversed(_actions.get()) if action.state is state), None)
    if action is None:
        raise RuntimeError('Manual decisions require a manual_action context')
    action.affected.update(item.id if isinstance(item, Detection) else item for item in detections)
    action.reviewed = True


def manual_decision(function):
    @wraps(function)
    def wrapped(state: SessionState, *args, **kwargs):
        with manual_action(state):
            return function(state, *args, **kwargs)
    return wrapped
