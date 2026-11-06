import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Mention
from app.models.store import store
from app.resolution.cluster import build_clusters, mentions_to_detections


@pytest.fixture
def review():
    sid = store.create()
    state = store.get(sid)
    with TestClient(app) as client:
        yield client, state
    store.delete(sid)


def seed(state, surfaces, detected):
    state.doc_text = '\n\n'.join(surfaces)
    positions = []
    start = 0
    for i, surface in enumerate(surfaces):
        positions.append((start, start + len(surface)))
        if i in detected:
            state.mentions.append(Mention(id=f'm{i}', cat='PERSONA', surface=surface,
                start=start, end=start + len(surface)))
        start += len(surface) + 2
    state.clusters = build_clusters(state.mentions, state.doc_text)
    state.detections = mentions_to_detections(state.mentions, 'cat', state.clusters)
    return positions


def add(client, state, positions, index, endpoint='/api/manual-detection', cat='PERSONA'):
    start, end = positions[index]
    body = {'session_id': state.session_id, 'cat': cat, 'original': state.doc_text[start:end]}
    if endpoint == '/api/search-and-anonymize':
        body['positions'] = [{'start': start, 'end': end, 'raw': body['original']}]
    else:
        body.update(start=start, end=end)
    response = client.post(endpoint, json=body)
    assert response.status_code == 200, response.text
    assert 'clusters' in response.json()
    return response.json()['detection']


def act(client, state, cluster_id, action, body=None):
    response = client.post(f'/api/clusters/{cluster_id}/{action}',
        params={'session_id': state.session_id}, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def patch(client, state, detection_id, **changes):
    response = client.patch(f'/api/detections/{detection_id}',
        json={'session_id': state.session_id, **changes})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('endpoint', ['/api/manual-detection', '/api/detections/manual', '/api/search-and-anonymize'])
def test_manual_full_name_refreshes_unique_given_and_compound_surname_variants(review, endpoint):
    client, state = review
    surfaces = ['Vorst Zelkin, Nerea', 'Nerea', 'Vorst Zelkin', 'Texto reservado']
    positions = seed(state, surfaces, {1, 2})
    state.detections[0].placeholder = '[TESTIGO]'
    state.detections[0].manual_placeholder = True
    before = {d.id: (d.placeholder, d.manual_placeholder, list(d.positions)) for d in state.detections}
    add(client, state, positions, 0, endpoint)
    assert len(state.clusters) == 1
    cluster = state.clusters[0]
    assert set(cluster.surfaces) == set(surfaces[:3])
    assert cluster.status == 'suggested'
    for detection in state.detections:
        if detection.id in before:
            assert (detection.placeholder, detection.manual_placeholder, list(detection.positions)) == before[detection.id]
    stable_id = cluster.cluster_id
    unrelated = add(client, state, positions, 3, cat='OTRO')
    patch(client, state, unrelated['id'], enabled=False)
    assert state.clusters[0].cluster_id == stable_id
    assert not next(d for d in state.detections if d.id == unrelated['id']).enabled


def test_category_correction_and_removing_ambiguous_full_name_refresh_proposals(review):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Eliana Zelkin', 'Eliana'], {0, 1})
    added = add(client, state, positions, 2, cat='EMPRESA')
    patch(client, state, added['id'], cat='PERSONA')
    assert state.clusters == []
    other = next(d for d in state.detections if d.original == 'Eliana Zelkin')
    response = client.delete(f'/api/detections/{other.id}', params={'session_id': state.session_id})
    assert response.status_code == 200
    assert len(state.clusters) == 1
    assert set(state.clusters[0].surfaces) == {'Eliana Vorst', 'Eliana'}


def test_disabling_a_bad_anchor_refreshes_without_reenabling_or_renumbering_rows(review):
    client, state = review
    seed(state, ['Eliana Vorst', 'Eliana Zelkin', 'Eliana'], {0, 1, 2})
    before = {d.id: (d.placeholder, d.original, list(d.positions)) for d in state.detections}
    other = next(d for d in state.detections if d.original == 'Eliana Zelkin')
    patch(client, state, other.id, enabled=False)
    assert set(state.clusters[0].surfaces) == {'Eliana Vorst', 'Eliana'}
    assert not other.enabled and other.cluster_id is None
    assert {d.id: (d.placeholder, d.original, list(d.positions)) for d in state.detections} == before


def test_rejected_group_does_not_return_after_add_update_or_remove(review):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Vorst', 'Zella Quirna'], {0, 1})
    act(client, state, state.clusters[0].cluster_id, 'reject')
    assert state.clusters == []
    assert all(d.grouping_excluded for d in state.detections)
    extra = add(client, state, positions, 2)
    patch(client, state, 0, enabled=False)
    patch(client, state, 0, enabled=True)
    response = client.delete(f'/api/detections/{extra["id"]}', params={'session_id': state.session_id})
    assert response.status_code == 200
    assert state.clusters == []
    assert all(d.grouping_excluded for d in state.detections)


def test_explicit_split_is_not_joined_again_by_new_matching_variant(review):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Eliana', 'Vorst', 'VORST, ELIANA'], {0, 1, 2})
    act(client, state, state.clusters[0].cluster_id, 'split', {'mention_ids': ['m2']})
    before = {c.cluster_id: c.model_dump() for c in state.clusters}
    add(client, state, positions, 3)
    assert {c.cluster_id: c.model_dump() for c in state.clusters} == before
    assert len({mid for c in state.clusters for mid in c.mention_ids}) == 3


@pytest.mark.parametrize('decision', ['confirm', 'reject'])
def test_new_variant_is_only_incorporated_into_confirmed_identity_after_confirmation(review, decision):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Vorst', 'Eliana', 'Otro dato'], {0, 1})
    target = state.clusters[0]
    act(client, state, target.cluster_id, 'confirm')
    response = client.patch(f'/api/clusters/{target.cluster_id}',
        params={'session_id': state.session_id}, json={'placeholder': '[TESTIGO_7]'})
    assert response.status_code == 200
    before = target.model_dump()
    original_rows = [d.model_dump() for d in state.detections]
    added = add(client, state, positions, 2)
    assert target.model_dump() == before
    assert [d.model_dump() for d in state.detections[:2]] == original_rows
    proposal = next(c for c in state.clusters if c.target_cluster_id == target.cluster_id)
    assert proposal.surfaces == ['Eliana']
    assert added['placeholder'] != '[TESTIGO_7]'
    result = act(client, state, proposal.cluster_id, decision)
    assert len(result['clusters']) == 1
    row = next(d for d in state.detections if d.id == added['id'])
    if decision == 'confirm':
        assert row.cluster_id == target.cluster_id and row.cluster_confirmed
        assert row.placeholder == '[TESTIGO_7]'
        assert set(target.surfaces) == {'Eliana Vorst', 'Vorst', 'Eliana'}
        assert client.post('/api/export/preview', json={'session_id': state.session_id}).json()['text'].count('[TESTIGO_7]') == 3
    else:
        assert target.model_dump() == before
        assert row.grouping_excluded and row.cluster_id is None
        add(client, state, positions, 3, cat='OTRO')
        assert not any(c.target_cluster_id for c in state.clusters)


def test_ambiguous_variant_is_not_assigned_to_one_of_two_confirmed_people(review):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Eliana Vorst', 'Eliana Zelkin', 'Eliana Zelkin', 'Eliana'], {0, 1, 2, 3})
    for cluster in list(state.clusters):
        act(client, state, cluster.cluster_id, 'confirm')
    before = [c.model_dump() for c in state.clusters]
    row = add(client, state, positions, 4)
    assert row['cluster_id'] is None
    assert [c.model_dump() for c in state.clusters] == before


def test_invalid_manual_request_does_not_refresh_or_change_the_review(review):
    client, state = review
    seed(state, ['Eliana Vorst', 'Vorst'], {0, 1})
    before = state.model_dump()
    response = client.post('/api/manual-detection', json={
        'session_id': state.session_id, 'cat': 'PERSONA', 'original': 'texto ajeno', 'start': 0, 'end': 3,
    })
    assert response.status_code == 400
    assert state.model_dump() == before


def test_explicit_assignment_can_override_a_previous_rejection(review):
    client, state = review
    seed(state, ['Eliana Vorst', 'Vorst'], {0, 1})
    act(client, state, state.clusters[0].cluster_id, 'reject')
    created = client.post('/api/assign-cluster', json={
        'session_id': state.session_id, 'detection_id': 0, 'cluster_id': '__new__',
    })
    assert created.status_code == 200
    cluster_id = created.json()['cluster']['cluster_id']
    assert not state.detections[0].grouping_excluded
    assert state.detections[1].grouping_excluded
    joined = client.post('/api/assign-cluster', json={
        'session_id': state.session_id, 'detection_id': 1, 'cluster_id': cluster_id,
    })
    assert joined.status_code == 200
    assert not any(d.grouping_excluded for d in state.detections)
    assert len(state.clusters) == 1 and set(state.clusters[0].surfaces) == {'Eliana Vorst', 'Vorst'}


def test_manually_edited_pending_group_keeps_its_replacement_and_members(review):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Vorst', 'Eliana'], {0, 1})
    group = state.clusters[0]
    response = client.patch(f'/api/clusters/{group.cluster_id}',
        params={'session_id': state.session_id}, json={'placeholder': '[REVISADO]'})
    assert response.status_code == 200
    before = group.model_dump()
    add(client, state, positions, 2)
    assert group.model_dump() == before
    assert state.clusters == [group]


@pytest.mark.parametrize('endpoint', ['/api/manual-detection', '/api/search-and-anonymize'])
def test_reselecting_existing_detection_does_not_lock_automatic_grouping(review, endpoint):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Eliana', 'Eliana Zelkin'], {0, 1})
    add(client, state, positions, 1, endpoint)
    assert not any(reason.startswith('manual') for c in state.clusters for reason in c.reasons)
    add(client, state, positions, 2)
    short = next(d for d in state.detections if d.original == 'Eliana')
    assert short.cluster_id is None or all(
        c.surfaces == ['Eliana'] for c in state.clusters if c.cluster_id == short.cluster_id
    )
    assert not any('Eliana' in c.surfaces and len(c.surfaces) > 1 for c in state.clusters)


@pytest.mark.parametrize('change', ['delete', 'reclassify', 'reject'])
def test_edited_incorporation_survives_invalidated_destination_as_independent_group(review, change):
    client, state = review
    positions = seed(state, ['Eliana Vorst', 'Vorst', 'Eliana'], {0, 1})
    target = state.clusters[0]
    act(client, state, target.cluster_id, 'confirm')
    add(client, state, positions, 2)
    proposal = next(c for c in state.clusters if c.target_cluster_id)
    response = client.patch(f'/api/clusters/{proposal.cluster_id}',
        params={'session_id': state.session_id}, json={'placeholder': '[VARIANTE_REVISADA]'})
    assert response.status_code == 200
    if change == 'delete':
        for detection_id in (0, 1):
            assert client.delete(f'/api/detections/{detection_id}',
                params={'session_id': state.session_id}).status_code == 200
    elif change == 'reclassify':
        assert client.patch(f'/api/clusters/{target.cluster_id}',
            params={'session_id': state.session_id}, json={'cat': 'EMPRESA'}).status_code == 200
    else:
        act(client, state, target.cluster_id, 'reject')
    assert proposal in state.clusters and proposal.target_cluster_id is None
    assert proposal.placeholder == '[VARIANTE_REVISADA]'
    result = act(client, state, proposal.cluster_id, 'confirm')
    assert result['cluster']['placeholder'] == '[VARIANTE_REVISADA]'
    assert next(d for d in state.detections if d.original == 'Eliana').placeholder == '[VARIANTE_REVISADA]'
