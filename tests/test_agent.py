from app.agent import AgentService
from app.schemas import ChatRequest, Message


def test_clarify_when_query_is_vague():
    agent = AgentService()
    request = ChatRequest(messages=[Message(role="user", content="Help me find a test")])

    response = agent.handle_chat(request)

    assert response.end_of_conversation is False
    assert response.recommendations == []
    assert response.state == "clarifying"
    assert any(token in response.reply.lower() for token in {"role", "seniority", "assessment"})


def test_recommend_when_context_is_sufficient():
    agent = AgentService()
    request = ChatRequest(
        messages=[
            Message(
                role="user",
                content="I am hiring for a mid-level Java software engineer and want a cognitive assessment",
            )
        ]
    )

    response = agent.handle_chat(request)

    assert response.end_of_conversation is True
    assert 1 <= len(response.recommendations) <= 10
    assert response.recommendations[0].name
    assert response.recommendations[0].url
    assert response.recommendations[0].confidence is not None
    assert 0 <= response.recommendations[0].confidence <= 1


def test_refine_with_follow_up_constraint():
    agent = AgentService()
    request = ChatRequest(
        messages=[
            Message(role="user", content="I need a cognitive assessment for a mid-level Java engineer"),
            Message(role="assistant", content="Share any additional constraints."),
            Message(role="user", content="Add personality tests too"),
        ]
    )

    response = agent.handle_chat(request)

    assert response.end_of_conversation is True
    assert len(response.recommendations) >= 1
    assert any("personality" in item.test_type.lower() for item in response.recommendations)
    assert response.state == "refining"


def test_compare_named_assessments():
    agent = AgentService()
    request = ChatRequest(
        messages=[Message(role="user", content="Compare SHL Cognitive Ability Test and SHL Java Programming Test")]
    )

    response = agent.handle_chat(request)

    assert response.end_of_conversation is True
    assert len(response.recommendations) == 2
    assert any("Cognitive" in item.name for item in response.recommendations)
    assert any("Java" in item.name for item in response.recommendations)
    assert response.comparison_summary is not None


def test_offtopic_request_is_refused_without_recommendations():
    agent = AgentService()
    response = agent.handle_chat(
        ChatRequest(messages=[Message(role="user", content="Give me legal advice about hiring tests")])
    )

    assert response.recommendations == []
    assert response.end_of_conversation is False
    assert response.state == "refuse"


def test_groq_fallback_uses_catalog_reply_when_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    agent = AgentService()

    reply = agent._maybe_enhance_reply(
        "I want senior java assessment",
        "Catalog fallback",
        [],
        intent="recommendation",
    )

    assert reply == ("Catalog fallback", "catalog", None)


def test_groq_response_does_not_change_schema(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "demo-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")

    class FakeGroqClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class FakeMessage:
                        content = "Here is a grounded SHL shortlist for your Java hiring need."

                    class FakeChoice:
                        message = FakeMessage()

                    class FakeResponse:
                        choices = [FakeChoice()]

                    return FakeResponse()

    def fake_init(self):
        return FakeGroqClient()

    monkeypatch.setattr(AgentService, "_init_groq_client", fake_init)
    agent = AgentService()

    response = agent.handle_chat(
        ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="I am hiring for a mid-level Java software engineer and want a cognitive assessment",
                )
            ]
        )
    )

    assert set(response.model_dump().keys()) == {
        "reply",
        "recommendations",
        "end_of_conversation",
        "state",
        "comparison_summary",
        "reply_source",
        "llm_model",
    }
    assert response.reply_source in {"catalog", "groq"}
