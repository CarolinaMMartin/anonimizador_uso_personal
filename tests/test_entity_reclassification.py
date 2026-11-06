import io

import pdfplumber
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.anonymize.placeholders import build_detections_from_mentions
from app.main import app
from app.models.schemas import Mention
from app.models.store import store
from app.services.clusters import confirm_cluster, create_cluster_from_detections


@pytest.fixture
def review():
    sid = store.create()
    state = store.get(sid)
    samples = [
        ('PERSONA', 'PEREZ LUCÍA ANDREA'),
        ('EMPRESA', 'PEREZ LUCÍA ANDREA Fecha de Emisión'),
        ('EMPRESA', 'Perez Lucía Andrea'),
        ('EMPRESA', 'PEREZ LUCÍA ANDREA Fecha de Emisión'),
    ]
    state.doc_text = '\n'.join(surface for _, surface in samples)
    start = 0
    for index, (cat, surface) in enumerate(samples):
        state.mentions.append(Mention(id=f'm{index}', cat=cat, surface=surface,
            start=start, end=start + len(surface)))
        start += len(surface) + 1
    state.detections = build_detections_from_mentions(state.mentions, 'cat')
    target = create_cluster_from_detections(state, [0])
    source = create_cluster_from_detections(state, [1, 2])
    confirm_cluster(state, target.cluster_id)
    target.placeholder = target.canonical_label = '[PERSONA_9]'
    state.detections[0].placeholder = target.placeholder
    with TestClient(app) as client:
        yield client, state, source, target
    store.delete(sid)


def assert_single_identity(state, target, original_positions):
    assert state.clusters == [target]
    assert target.status == 'confirmed'
    assert all(d.cat == 'PERSONA' and d.cluster_id == target.cluster_id for d in state.detections)
    assert all(d.placeholder == '[PERSONA_9]' and d.cluster_confirmed for d in state.detections)
    assert {m.cat for m in state.mentions} == {'PERSONA'}
    assert set(target.mention_ids) == {m.id for m in state.mentions}
    assert [[p.model_dump() for p in d.positions] for d in state.detections] == original_positions


@pytest.mark.parametrize('reclassify_first', [False, True])
def test_explicit_correction_and_merge_preserve_review_and_exports(review, reclassify_first):
    client, state, source, target = review
    positions = [[p.model_dump() for p in d.positions] for d in state.detections]
    if reclassify_first:
        response = client.patch(f'/api/clusters/{source.cluster_id}',
            params={'session_id': state.session_id}, json={'cat': 'PERSONA'})
        assert response.status_code == 200, response.text
        assert source.cat == 'PERSONA' and source.status == 'suggested'
        assert all(d.cat == 'PERSONA' for d in state.detections)
        assert all(d.placeholder.startswith('[PERSONA_') for d in state.detections)
    response = client.post(f'/api/clusters/{target.cluster_id}/absorb',
        params={'session_id': state.session_id},
        json={'source_cluster_id': source.cluster_id, 'reclassify': not reclassify_first})
    assert response.status_code == 200, response.text
    assert_single_identity(state, target, positions)
    payload = {'session_id': state.session_id}
    texts = [client.post('/api/export/preview', json=payload).json()['text']]
    word = client.post('/api/export/docx', json=payload)
    texts.append('\n'.join(p.text for p in Document(io.BytesIO(word.content)).paragraphs))
    pdf = client.post('/api/export/pdf', json=payload)
    with pdfplumber.open(io.BytesIO(pdf.content)) as exported:
        texts.append('\n'.join(p.extract_text() or '' for p in exported.pages))
    for text in texts:
        assert text.count('[PERSONA_9]') == 4
        assert 'EMPRESA' not in text and 'PEREZ' not in text and 'Lucía' not in text


def test_cross_category_merge_requires_explicit_choice_and_invalid_targets_do_not_mutate(review):
    client, state, source, target = review
    before = state.model_dump()
    for target_id, payload in [
        (target.cluster_id, {'source_cluster_id': source.cluster_id}),
        ('missing', {'source_cluster_id': source.cluster_id, 'reclassify': True}),
    ]:
        response = client.post(f'/api/clusters/{target_id}/absorb',
            params={'session_id': state.session_id}, json=payload)
        assert response.status_code == 400
        assert state.model_dump() == before


def test_confirmed_group_category_change_keeps_membership_and_disabled_choices(review):
    client, state, source, target = review
    confirm_cluster(state, source.cluster_id)
    state.detections[2].enabled = False
    positions = [[p.model_dump() for p in d.positions] for d in state.detections]
    response = client.patch(f'/api/clusters/{source.cluster_id}',
        params={'session_id': state.session_id}, json={'cat': 'PERSONA'})
    assert response.status_code == 200, response.text
    assert source.status == 'confirmed' and source.cat == 'PERSONA'
    assert source.placeholder != target.placeholder
    assert source.placeholder.startswith('[PERSONA_')
    assert state.detections[1].placeholder == state.detections[2].placeholder == source.placeholder
    assert not state.detections[2].enabled
    assert [[p.model_dump() for p in d.positions] for d in state.detections] == positions
    assert not set(source.mention_ids).intersection(target.mention_ids)


@pytest.mark.parametrize('endpoint', ['assign', 'add'])
def test_one_detection_can_be_reclassified_and_moved_without_moving_its_siblings(review, endpoint):
    client, state, source, target = review
    payload = {'reclassify': True}
    if endpoint == 'assign':
        url, params = '/api/assign-cluster', None
        payload.update(session_id=state.session_id, detection_id=1, cluster_id=target.cluster_id)
    else:
        url, params = f'/api/clusters/{target.cluster_id}/add', {'session_id': state.session_id}
        payload['detection_ids'] = [1]
    response = client.post(url, params=params, json=payload)
    assert response.status_code == 200, response.text
    moved, remaining = state.detections[1:]
    assert moved.cat == 'PERSONA' and moved.cluster_id == target.cluster_id
    assert moved.placeholder == target.placeholder
    assert remaining.cat == 'EMPRESA' and remaining.cluster_id == source.cluster_id
    assert not set(source.mention_ids).intersection(target.mention_ids)


def test_invalid_group_patch_and_batch_add_are_atomic(review):
    client, state, source, target = review
    before = state.model_dump()
    response = client.patch(f'/api/clusters/{source.cluster_id}',
        params={'session_id': state.session_id}, json={'cat': 'PERSONA', 'placeholder': ' '})
    assert response.status_code == 400
    assert state.model_dump() == before
    response = client.post(f'/api/clusters/{target.cluster_id}/add',
        params={'session_id': state.session_id}, json={'detection_ids': [1, 999], 'reclassify': True})
    assert response.status_code == 404
    assert state.model_dump() == before
