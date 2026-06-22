"""Cancelación cooperativa de análisis largos."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_cancelled: set[str] = set()


class AnalysisCancelledError(Exception):
    """El usuario canceló el análisis en curso."""


def request_cancel(session_id: str) -> None:
    with _lock:
        _cancelled.add(session_id)


def clear_cancel(session_id: str) -> None:
    with _lock:
        _cancelled.discard(session_id)


def check_cancel(session_id: str | None) -> None:
    if not session_id:
        return
    with _lock:
        if session_id in _cancelled:
            _cancelled.discard(session_id)
            raise AnalysisCancelledError()
