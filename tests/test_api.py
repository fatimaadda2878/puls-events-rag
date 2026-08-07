import os
os.environ.setdefault("REBUILD_API_KEY","secret")
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").status_code==200
def test_empty_question(): assert client.post("/ask",json={"question":""}).status_code==422
def test_rebuild_protected(): assert client.post("/rebuild").status_code==401
