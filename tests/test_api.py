import asyncio
import importlib
import sys

import httpx

from app.main import app


async def _request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def test_health_and_chat_endpoints():
    health = asyncio.run(_request("GET", "/health"))
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    chat = asyncio.run(
        _request(
            "POST",
            "/chat",
            json={"messages": [{"role": "user", "content": "I need a cognitive assessment for a mid-level Java engineer"}]},
        )
    )
    assert chat.status_code == 200
    data = chat.json()
    assert set(data.keys()) == {
        "reply",
        "recommendations",
        "end_of_conversation",
        "state",
        "comparison_summary",
        "reply_source",
        "llm_model",
    }


def test_api_supports_browser_requests():
    response = asyncio.run(_request("GET", "/health", headers={"Origin": "http://localhost:5173"}))
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"


def test_chat_is_stateless_and_rejects_session_fields():
    response = asyncio.run(
        _request(
            "POST",
            "/chat",
            json={
                "session_id": "demo-session",
                "messages": [{"role": "user", "content": "I want senior level java skills assessment"}],
            },
        )
    )

    assert response.status_code == 422


def test_agent_uses_catalog_without_persistence_settings(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:pass@cluster0.reuka.mongodb.net/")

    import app.agent as agent_module

    importlib.reload(agent_module)
    service = agent_module.AgentService()

    assert not hasattr(service, "mongo_collection")
    assert service.catalog.items
