from fastapi.testclient import TestClient

from app.main import app
from app.rag.ingest import import_knowledge


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["api"] == "ok"


def test_chat_keyword():
    response = client.post("/chat", json={"user_id": "test", "message": "你好"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "keyword"
    assert payload["session_id"]


def test_chat_tool():
    response = client.post("/chat", json={"user_id": "test", "message": "/time 北京"})
    assert response.status_code == 200
    assert response.json()["tool_result"]["tool"] == "time"


def test_chat_rag():
    import_knowledge()
    response = client.post("/chat", json={"user_id": "test", "message": "根据知识库介绍技术栈"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "rag"
    assert payload["sources"]
