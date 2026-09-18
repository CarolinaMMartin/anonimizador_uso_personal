"""General identity rules: formats, unknown names and ambiguous aliases."""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.anonymize.apply import anonymize_text
from app.main import app
from app.models.schemas import Mention, SessionState
from app.models.store import store
from app.resolution.cluster import build_clusters, mentions_to_detections
from app.services.clusters import (
    add_detections_to_cluster, confirm_cluster, create_cluster_from_detections,
    merge_clusters, remove_surface_from_cluster, split_cluster,
)
from app.services.detections import add_bulk_detection, remove_detection, update_detection


def make_state(surfaces):
    text, mentions = '', []
    for index, surface in enumerate(surfaces):
        start = len(text)
        text += surface + '\n\n'
        mentions.append(Mention(id=f'm{index}', cat='PERSONA', surface=surface,
                                start=start, end=start + len(surface)))
    clusters = build_clusters(mentions, text)
    return SessionState(session_id='synthetic', doc_text=text, mentions=mentions,
                        clusters=clusters, detections=mentions_to_detections(mentions, 'cat', clusters))


@pytest.mark.parametrize('surfaces', [
    ['Zorvik, Eliana', 'Eliana Zorvik', 'ZORVIK, ELIANA', 'Eliana', 'Zorvik'],
    ['Vorst Zelkin, Nerea', 'Nerea Vorst Zelkin', 'Vorst Zelkin', 'Nerea', 'Zelkin'],
    ['De la Quirna, Óscar', 'OSCAR DE LA QUIRNA', 'Óscar', 'Quirna'],
    ['Luan O’Kelan', "O'Kelan, Luan", 'Luan', "O'Kelan"],
    ['Fenna Ros-Vaak', 'Ros Vaak, Fenna', 'Fenna Ros Vaak', 'Fenna'],
    ['李, 明', '明 李', '明 李'],
    ['Li Qorvik', 'Li', 'Qorvik'],
    ['Marcos Adrian Zelvik', 'M. A. Zelvik', 'Marcos Zelvik', 'Zelvik'],
    ['Marcos Adrian Zelvik', 'M.A. Zelvik', 'Zelvik, M.A.'],
    ['Nolvik, Irina', 'Nolvik Irina', 'Irina Nolvik', 'I. Nolvik'],
    ['El Dr. Zella Vorik', 'Zella Vorik', 'Vorik, Zella'],
    ['Quirna, Doña Ágata', 'Ágata Quirna', 'Quirna'],
])
def test_unique_formats_and_aliases(surfaces):
    state = make_state(surfaces)
    assert len(state.clusters) == 1
    assert set(state.clusters[0].mention_ids) == {m.id for m in state.mentions}
    assert {d.cluster_id for d in state.detections} == {state.clusters[0].cluster_id}
    assert not any(d.cluster_confirmed for d in state.detections)
    confirm_cluster(state, state.clusters[0].cluster_id)
    assert len({d.placeholder for d in state.detections}) == 1
    assert all(d.cluster_confirmed for d in state.detections)
    assert anonymize_text(state.doc_text, state.detections).count(state.clusters[0].placeholder) == len(surfaces)


@pytest.mark.parametrize('full_names, ambiguous', [
    (['Eliana Vorst', 'Eliana Zelkin'], 'Eliana'),
    (['Nerea Vorst', 'Zella Vorst'], 'Vorst'),
    (['Marcos Zelvik', 'Mateo Zelvik'], 'M. Zelvik'),
    (['Ana Maria Vorst', 'Ana Luisa Vorst'], 'Ana Vorst'),
    (['Vorst Zelkin, Nerea', 'Vorst Zelkin, Zella'], 'Vorst Zelkin'),
    (['Li Qorvik', 'Liam Qorvik'], 'L. Qorvik'),
])
def test_ambiguous_alias_cannot_bridge_people(full_names, ambiguous):
    state = make_state([*full_names, *full_names, ambiguous, ambiguous])
    owners = {mid: c.cluster_id for c in state.clusters for mid in c.mention_ids}
    assert owners['m0'] != owners['m1']
    assert owners['m4'] not in {owners['m0'], owners['m1']}
    assert all(len({full for full in full_names if full in c.surfaces}) <= 1 for c in state.clusters)


@pytest.mark.parametrize('left, right', [
    ('Ana Vorst', 'Anna Vorst'),
    ('Juan Vorst', 'Juana Vorst'),
    ('Li Vorst', 'Liam Vorst'),
    ('M. A. Vorst', 'Marcos Bruno Vorst'),
    ('Marcos Adrian Vorst', 'Marcos Alfredo Vorst'),
    ('Ana Maria Vorst', 'Maria Vorst'),
    ('Vorst, Ana Maria', 'Vorst, Maria'),
    ('Maria, Ana', 'Vorst, Ana Maria'),
    ('J. P.', 'Juan Perez'),
])
def test_different_information_stays_separate(left, right):
    state = make_state([left, right, left, right])
    assert len(state.clusters) == 2
    assert all(len(set(c.surfaces)) == 1 for c in state.clusters)


def test_catalog_coverage_not_required(monkeypatch):
    from app.detection import dictionaries
    monkeypatch.setattr(dictionaries, 'get_nombres', lambda: set())
    monkeypatch.setattr(dictionaries, 'get_apellidos', lambda: set())
    state = make_state(['Zorvik, Eliana', 'Eliana Zorvik', 'Eliana', 'Zorvik'])
    assert len(state.clusters) == 1 and len(state.clusters[0].mention_ids) == 4


def test_nearby_identifier_does_not_override_ambiguity():
    state = make_state(['Ana Vorst', 'Anna Vorst', 'Vorst'])
    state.mentions.append(Mention(id='dni', cat='DNI', surface='12345678', start=1, end=9))
    assert build_clusters(state.mentions, state.doc_text) == []


def test_group_order_is_deterministic():
    state = make_state(['Zorvik, Eliana', 'Eliana Zorvik', 'Eliana', 'Zella Vorst', 'Vorst'])
    assert [c.model_dump() for c in state.clusters] == [
        c.model_dump() for c in build_clusters(list(reversed(state.mentions)), state.doc_text)]


def test_exact_duplicates_do_not_raise_partial_confidence():
    state = make_state(['Eliana Vorst', 'Eliana Vorst', 'Vorst'])
    assert state.clusters[0].confidence == 'media'


def test_suggested_groups_do_not_pass_confirmed_only():
    state = make_state(['Eliana Vorst', 'Vorst'])
    assert anonymize_text(state.doc_text, state.detections, confirmed_only=True) == state.doc_text
    confirm_cluster(state, state.clusters[0].cluster_id)
    assert 'Vorst' not in anonymize_text(state.doc_text, state.detections, confirmed_only=True)


def test_split_restores_distinct_labels_and_exclusive_membership():
    state = make_state(['Eliana Vorst', 'Eliana', 'Vorst', 'VORST'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    original_label = cluster.placeholder
    separate = split_cluster(state, cluster.cluster_id, ['m2'])[0]
    short = next(d for d in state.detections if d.original == 'Vorst')
    assert set(separate.mention_ids) == {'m2', 'm3'}
    assert short.placeholder != original_label and not short.cluster_confirmed
    assert set(cluster.mention_ids) == {'m0', 'm1'}
    assert cluster.status == 'confirmed'
    confirm_cluster(state, separate.cluster_id)
    assert short.placeholder != original_label


def test_remove_surface_uses_accent_and_case_normalization():
    state = make_state(['Eliana Vórst', 'Vórst', 'VORST'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    assert len(remove_surface_from_cluster(state, cluster.cluster_id, 'VORST')) == 1
    assert cluster.surfaces == ['Eliana Vórst']


def test_move_and_merge_have_no_stale_owners():
    state = make_state(['Eliana Vorst', 'Eliana', 'Zella Zelkin', 'Zella'])
    first, second = state.clusters
    confirm_cluster(state, first.cluster_id)
    confirm_cluster(state, second.cluster_id)
    det = next(d for d in state.detections if d.original == 'Eliana')
    add_detections_to_cluster(state, second.cluster_id, [det.id])
    assert det.cluster_id == second.cluster_id and det.placeholder == second.placeholder
    assert 'Eliana' not in first.surfaces
    merged = merge_clusters(state, [first.cluster_id, second.cluster_id])
    assert len(state.clusters) == 1
    assert all(d.cluster_id == merged.cluster_id and not d.cluster_confirmed for d in state.detections)
    confirm_cluster(state, merged.cluster_id)
    assert len({d.placeholder for d in state.detections}) == 1


def test_cross_category_group_rejected_without_mutating_state():
    state = make_state(['Eliana Vorst', 'Vorst'])
    other = add_bulk_detection(state, 'OTRO', 'Eliana', [state.detections[0].positions[0]])
    before = state.model_dump()
    assert add_detections_to_cluster(state, state.clusters[0].cluster_id, [other.id]) is None
    assert create_cluster_from_detections(state, [state.detections[0].id, other.id]) is None
    assert state.model_dump() == before


def test_category_edit_and_delete_clean_groups_without_renumbering():
    state = make_state(['Eliana Vorst', 'Eliana', 'Vorst'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    original_id = state.detections[2].id
    update_detection(state, state.detections[1].id, cat='OTRO')
    assert 'Eliana' not in cluster.surfaces
    assert not state.detections[1].cluster_confirmed
    remove_detection(state, state.detections[0].id)
    assert state.detections[-1].id == original_id
    assert cluster.surfaces == ['Vorst']


def test_confirm_keeps_disabled_mentions_disabled():
    state = make_state(['Eliana Vorst', 'Vorst'])
    state.detections[1].enabled = False
    confirm_cluster(state, state.clusters[0].cluster_id)
    assert not state.detections[1].enabled


def test_edit_confirmed_label_updates_whole_identity():
    state = make_state(['Eliana Vorst', 'Vorst'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    update_detection(state, state.detections[1].id, placeholder='[TESTIGO_20]')
    assert cluster.placeholder == '[TESTIGO_20]'
    assert {d.placeholder for d in state.detections} == {'[TESTIGO_20]'}


def test_manual_accent_variant_keeps_existing_group_and_members():
    state = make_state(['Eliana Vórst', 'Vórst'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    det = add_bulk_detection(state, 'PERSONA', 'VORST', [state.detections[1].positions[0]])
    assert len(state.detections) == 2
    assert det.cluster_id == cluster.cluster_id and det.cluster_confirmed
    assert set(det.mention_ids) <= set(cluster.mention_ids)


def test_new_manual_label_does_not_reuse_confirmed_labels():
    state = make_state(['Eliana Vorst', 'Vorst'])
    cluster = confirm_cluster(state, state.clusters[0].cluster_id)
    det = add_bulk_detection(state, 'OTRO', 'Eliana', [state.detections[0].positions[0]])
    update_detection(state, det.id, cat='PERSONA')
    assert det.placeholder != cluster.placeholder


def test_manual_mentions_do_not_reuse_ids_after_deletion():
    state = make_state(['Eliana Vorst', 'Vorst'])
    position = state.detections[0].positions[0]
    first = add_bulk_detection(state, 'OTRO', 'Eliana', [position])
    second = add_bulk_detection(state, 'OTRO', 'Vorst', [position])
    remove_detection(state, first.id)
    add_bulk_detection(state, 'OTRO', 'Eliana', [position])
    ids = [mention.id for mention in state.mentions]
    assert len(ids) == len(set(ids))
    assert set(second.mention_ids) <= set(ids)


def test_invalid_edit_does_not_detach_or_change_group():
    state = make_state(['Eliana Vorst', 'Vorst'])
    confirm_cluster(state, state.clusters[0].cluster_id)
    before = state.model_dump()
    with pytest.raises(ValueError):
        update_detection(state, state.detections[0].id, cat='OTRO', placeholder=' ')
    assert state.model_dump() == before


def test_confirm_export_reject_round_trip():
    state = make_state(['Zorvik, Eliana', 'Eliana Zorvik', 'Eliana', 'Zorvik'])
    state.session_id = store.create()
    store.save(state)
    try:
        with TestClient(app) as client:
            cluster_id = state.clusters[0].cluster_id
            confirmed = client.post(f'/api/clusters/{cluster_id}/confirm', params={'session_id': state.session_id})
            assert confirmed.status_code == 200
            labels = {d['placeholder'] for d in confirmed.json()['detections']}
            assert len(labels) == 1
            payload = {'session_id': state.session_id, 'use_confirmed_only': True}
            preview = client.post('/api/export/preview', json=payload)
            assert preview.status_code == 200
            assert 'Zorvik' not in preview.json()['text'] and 'Eliana' not in preview.json()['text']
            exported = client.post('/api/export/csv', json=payload)
            assert exported.status_code == 200
            rows = list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig')), delimiter=';'))
            assert {row['Sustitución'] for row in rows} == labels
            rejected = client.post(f'/api/clusters/{cluster_id}/reject', params={'session_id': state.session_id})
            assert rejected.status_code == 200
            assert rejected.json()['clusters'] == []
            assert all(d['cluster_id'] is None and not d['cluster_confirmed'] for d in rejected.json()['detections'])
            assert len({d['placeholder'] for d in rejected.json()['detections']}) == len(rows)
            assert client.get('/api/clusters', params={'session_id': state.session_id}).json()['clusters'] == []
    finally:
        store.delete(state.session_id)
