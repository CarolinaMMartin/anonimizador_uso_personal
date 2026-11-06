import pytest
from fastapi.testclient import TestClient

from app.detection import pipeline
from app.main import app
from app.models.store import store
from scripts.check_identity_flow import verify, verify_case_boundaries


@pytest.mark.parametrize('nlp', [False, True])
@pytest.mark.parametrize('checker', [verify, verify_case_boundaries])
def test_caption_parties_and_aliases_remain_consistent_through_exports(monkeypatch, nlp, checker):
    monkeypatch.setattr(pipeline, 'ENABLE_SPACY', nlp)
    monkeypatch.setattr(pipeline, 'ENABLE_PRESIDIO', nlp)
    sessions = []
    try:
        with TestClient(app) as client:
            def call(method, path, payload=None, file=None, raw=False):
                response = client.request(method, path, json=payload, files={'file': file} if file else None)
                assert response.status_code == 200, response.text
                data = response.content if raw else response.json()
                if path == '/api/upload':
                    sessions.append(data['session_id'])
                return data
            results = checker(call)
        assert all(all(result['checks'].values()) for result in results), results
    finally:
        for session_id in sessions:
            store.delete(session_id)
