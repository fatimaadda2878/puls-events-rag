import os

os.environ.setdefault("REBUILD_API_KEY", "test-secret")

from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["retrieval"] == "faiss+mistral-embed"
    assert body["generation"] == "mistral"


def test_empty_question():
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_rebuild_protected():
    assert client.post("/rebuild").status_code == 401


def test_rebuild_accepted(monkeypatch):
    monkeypatch.setattr(main.rebuild_manager, "start", lambda on_success=None: True)
    response = client.post(
        "/rebuild",
        headers={"x-rebuild-key": "test-secret"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
