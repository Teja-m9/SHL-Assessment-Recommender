import importlib
import sys

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_chat_endpoints():
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    chat = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "I need a cognitive assessment for a mid-level Java engineer"}]},
    )
    assert chat.status_code == 200
    data = chat.json()
    assert "reply" in data
    assert "recommendations" in data
    assert "reply_source" in data


def test_api_supports_browser_requests():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"


def test_chat_accepts_session_id_and_returns_it():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "session_id": "demo-session",
            "messages": [{"role": "user", "content": "I want senior level java skills assessment"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "demo-session"


def test_chat_generates_session_id_when_missing():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "I need a cognitive assessment for a mid-level Java engineer"}]},
    )

    assert response.status_code == 200
    assert response.json()["session_id"]


def test_agent_uses_default_database_when_uri_has_no_db_name(monkeypatch):
    class FakeCollection:
        def __init__(self, name: str = "chat_sessions") -> None:
            self.name = name

    class FakeDatabase:
        def get_collection(self, name: str):
            return FakeCollection(name)

    class FakeClient:
        def __init__(self, uri: str, serverSelectionTimeoutMS: int = 3000) -> None:
            self.uri = uri
            self.server_selection_timeout_ms = serverSelectionTimeoutMS

        def __getitem__(self, name: str):
            return FakeDatabase()

    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:pass@cluster0.reuka.mongodb.net/")
    monkeypatch.setitem(sys.modules, "pymongo", type("FakePyMongo", (), {"MongoClient": FakeClient}))

    import app.agent as agent_module

    importlib.reload(agent_module)
    service = agent_module.AgentService()

    assert service.mongo_collection is not None
    assert service.mongo_collection.name == "chat_sessions"
