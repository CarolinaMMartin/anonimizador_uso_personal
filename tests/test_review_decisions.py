"""Manual decisions resolve spatial conflicts without changing row identities."""
import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.anonymize.apply import anonymize_text, build_highlights
from app.main import app
from app.models.schemas import Detection, Position, SessionState
from app.models.store import store
from app.services.clusters import (
    absorb_cluster_into, add_detections_to_cluster, confirm_cluster,
    create_cluster_from_detections, merge_clusters, reclassify_cluster,
    reject_cluster, split_cluster,
)
from app.services.detections import add_bulk_detection, add_manual_detection, remove_detection, update_detection
from app.services.suggestions import refresh_suggestions


def row(index, spans, order=0, cat='PERSONA'):
    return Detection(id=index, cat=cat, original=f'original {index}',
                     placeholder=f'[ROW_{index}]', manual_order=order,
                     positions=[Position(start=start, end=end) for start, end in spans])


@pytest.mark.parametrize('intervals', [
    [(0, 8), (0, 8)], [(0, 12), (3, 8)], [(0, 8), (4, 12)],
    [(0, 6), (4, 10), (8, 12)],
])
@pytest.mark.parametrize('previous_order', [0, 4])
def test_latest_decision_wins_the_entire_overlap_component(intervals, previous_order):
    text = 'abcdefghijkl; tail'
    rows = [row(index, [span], previous_order) for index, span in enumerate(intervals)]
    rows[-1].manual_order = previous_order + 1
    before = [det.model_dump() for det in rows]
    end = max(span[1] for span in intervals)
    expected = rows[-1].placeholder + text[end:]
    assert anonymize_text(text, rows) == expected
    highlights = build_highlights(text, rows)
    assert [(h['start'], h['end'], h['placeholder']) for h in highlights] == [(0, end, rows[-1].placeholder)]
    assert [det.model_dump() for det in rows] == before


def test_winner_changes_only_overlapping_occurrences_and_disabled_rows_do_not_uncover_others():
    state = SessionState(session_id='test', doc_text='abcdefghijkl; abcdef')
    old = row(0, [(0, 6), (14, 20)])
    new = row(1, [(3, 12)], order=7, cat='EMPRESA')
    state.detections = [old, new]
    assert anonymize_text(state.doc_text, state.detections) == '[ROW_1]; [ROW_0]'
    assert build_highlights(state.doc_text, state.detections)[0]['cat'] == 'EMPRESA'
    update_detection(state, 1, enabled=False)
    assert anonymize_text(state.doc_text, state.detections) == '[ROW_0]ghijkl; [ROW_0]'
    update_detection(state, 1, enabled=True)
    assert anonymize_text(state.doc_text, state.detections) == '[ROW_1]; [ROW_0]'
    remove_detection(state, 1)
    assert anonymize_text(state.doc_text, state.detections) == '[ROW_0]ghijkl; [ROW_0]'
    assert old.manual_order == 0


def test_adjacent_components_and_stable_ties_keep_previous_precedence():
    text = 'abcdefghijkl'
    rows = [row(0, [(0, 3)], 4), row(1, [(0, 6)], 4), row(2, [(0, 6)], 4), row(3, [(6, 12)], 1)]
    assert anonymize_text(text, rows) == '[ROW_1][ROW_3]'


def test_confirmed_only_filters_before_resolving_and_invalid_positions_remain_errors():
    rows = [row(0, [(0, 6)]), row(1, [(3, 9)], 7)]
    rows[0].cluster_confirmed = True
    assert anonymize_text('abcdefghijkl', rows, confirmed_only=True) == '[ROW_0]ghijkl'
    rows[1].user_added = True
    assert anonymize_text('abcdefghijkl', rows, confirmed_only=True) == '[ROW_1]jkl'
    rows[1].positions[0].end = 99
    with pytest.raises(ValueError):
        anonymize_text('abcdefghijkl', rows)


def test_successful_actions_use_monotonic_orders_and_failed_updates_are_atomic():
    state = SessionState(session_id='test', doc_text='Ana Beta Ana')
    first = add_manual_detection(state, 'PERSONA', 0, 3)
    assert first.manual_order == state.review_sequence == 1
    assert state.has_review
    add_manual_detection(state, 'PERSONA', 0, 3)
    assert first.manual_order == state.review_sequence == 2
    update_detection(state, first.id, placeholder='[CUSTOM]', enabled=True)
    assert first.manual_order == state.review_sequence == 3
    before = state.model_dump()
    with pytest.raises(ValueError):
        update_detection(state, first.id, cat='EMPRESA', placeholder=' ')
    assert state.model_dump() == before
    with pytest.raises(ValueError):
        add_manual_detection(state, 'PERSONA', 0, 999)
    assert state.model_dump() == before
    first.manual_order = 40
    update_detection(state, first.id, cat='EMPRESA')
    assert first.manual_order == state.review_sequence == 41
    remove_detection(state, first.id)
    assert state.review_sequence == 42 and state.has_review and not state.detections


def grouped_state():
    state = SessionState(session_id='test', doc_text='Ana Beta Gamma Delta')
    for start, end in [(0, 3), (4, 8), (9, 14), (15, 20)]:
        add_manual_detection(state, 'PERSONA', start, end)
    return state


def assert_action_order(state, before, affected):
    assert state.review_sequence == before + 1
    assert all(det.manual_order == state.review_sequence for det in affected)


def test_group_actions_share_one_order_including_nested_reclassification_and_merge():
    state = grouped_state()
    target = create_cluster_from_detections(state, [0, 1])
    confirm_cluster(state, target.cluster_id)
    source = create_cluster_from_detections(state, [2, 3])
    reclassify_cluster(state, source.cluster_id, 'EMPRESA')
    before = state.review_sequence
    absorb_cluster_into(state, target.cluster_id, source.cluster_id, reclassify=True)
    assert_action_order(state, before, state.detections)
    assert len(state.clusters) == 1
    before = state.review_sequence
    update_detection(state, 0, placeholder='[IDENTITY]')
    assert_action_order(state, before, state.detections)
    assert all(det.manual_placeholder for det in state.detections)
    assert target.manual_placeholder
    before = state.review_sequence
    split_cluster(state, target.cluster_id, state.detections[0].mention_ids)
    assert_action_order(state, before, state.detections)


def test_group_assignment_confirmation_rejection_and_automatic_refresh():
    state = grouped_state()
    before = state.review_sequence
    target = create_cluster_from_detections(state, [0, 1])
    assert_action_order(state, before, state.detections[:2])
    before = state.review_sequence
    confirm_cluster(state, target.cluster_id)
    assert_action_order(state, before, state.detections[:2])
    before = state.review_sequence
    add_detections_to_cluster(state, target.cluster_id, [2])
    assert_action_order(state, before, state.detections[:3])
    before = state.review_sequence
    orders = [det.manual_order for det in state.detections]
    refresh_suggestions(state)
    assert state.review_sequence == before
    assert [det.manual_order for det in state.detections] == orders
    reject_cluster(state, target.cluster_id)
    assert_action_order(state, before, state.detections[:3])


def test_bulk_existing_confirmed_label_update_consumes_only_one_order():
    state = grouped_state()
    group = create_cluster_from_detections(state, [0, 1])
    confirm_cluster(state, group.cluster_id)
    before = state.review_sequence
    add_bulk_detection(state, 'PERSONA', 'Ana', [Position(start=0, end=3)], '[IDENTITY]')
    assert_action_order(state, before, state.detections[:2])
    before = state.review_sequence
    add_manual_detection(state, 'PERSONA', 0, 3)
    assert_action_order(state, before, state.detections[:1])
    assert state.detections[1].manual_order == before


def test_invalid_group_requests_do_not_mutate_or_consume_orders():
    state = grouped_state()
    one = create_cluster_from_detections(state, [0])
    two = create_cluster_from_detections(state, [1])
    before = state.model_dump()
    assert add_detections_to_cluster(state, one.cluster_id, [2, 99]) is None
    assert absorb_cluster_into(state, one.cluster_id, 'missing') is None
    assert merge_clusters(state, [one.cluster_id, two.cluster_id, 'missing']) is None
    assert state.model_dump() == before


@pytest.mark.parametrize('operation', ['create', 'assign'])
def test_row_without_usable_mentions_is_rejected_before_reclassification(operation):
    state = grouped_state()
    target = create_cluster_from_detections(state, [0])
    state.detections.append(Detection(id=99, cat='EMPRESA', original='Old row',
                                      placeholder='[OLD]', mention_ids=['missing']))
    before = state.model_dump()
    if operation == 'create':
        result = create_cluster_from_detections(state, [99])
    else:
        result = add_detections_to_cluster(state, target.cluster_id, [99], reclassify=True)
    assert result is None
    assert state.model_dump() == before


@pytest.mark.parametrize('include_valid_member', [False, True])
def test_invalid_split_does_not_refresh_or_mutate_the_session(include_valid_member):
    sid = store.create()
    state = store.get(sid)
    state.doc_text = 'Ana Beta'
    add_manual_detection(state, 'PERSONA', 0, 3)
    group = create_cluster_from_detections(state, [0])
    before = state.model_dump()
    mention_ids = ['missing'] + (group.mention_ids if include_valid_member else [])
    try:
        with TestClient(app) as client:
            response = client.post(f'/api/clusters/{group.cluster_id}/split',
                                   params={'session_id': sid}, json={'mention_ids': mention_ids})
            assert response.status_code == 400
            assert state.model_dump() == before
    finally:
        store.delete(sid)


def test_group_patch_and_exports_use_the_same_manual_winner():
    sid = store.create()
    state = store.get(sid)
    state.doc_text = 'Ana Beta Gamma.'
    add_manual_detection(state, 'PERSONA', 0, 8)
    add_manual_detection(state, 'EMPRESA', 4, 14)
    group = create_cluster_from_detections(state, [1])
    confirm_cluster(state, group.cluster_id)
    before = state.review_sequence
    try:
        with TestClient(app) as client:
            response = client.patch(f'/api/clusters/{group.cluster_id}', params={'session_id': sid},
                                    json={'cat': 'OTRO', 'placeholder': '[REVIEWED]'})
            assert response.status_code == 200, response.text
            assert_action_order(state, before, [state.detections[1]])
            assert group.manual_placeholder and state.detections[1].manual_placeholder
            preview = client.get('/api/preview', params={'session_id': sid, 'mode': 'anon'}).json()
            assert preview['text'] == '[REVIEWED].'
            assert preview['highlights'][0]['placeholder'] == '[REVIEWED]'
            assert preview['highlights'][0]['cat'] == 'OTRO'
            payload = {'session_id': sid}
            assert client.post('/api/export/preview', json=payload).json()['text'] == '[REVIEWED].'
            word = client.post('/api/export/docx', json=payload)
            assert '\n'.join(p.text for p in Document(io.BytesIO(word.content)).paragraphs) == '[REVIEWED].'
            pdf = client.post('/api/export/pdf', json=payload)
            with pdfplumber.open(io.BytesIO(pdf.content)) as exported:
                assert '\n'.join(p.extract_text() or '' for p in exported.pages) == '[REVIEWED].'
    finally:
        store.delete(sid)
