from app.agent import AgentService
from app.schemas import ChatRequest, Message


def test_clarify_when_query_is_vague():
    agent = AgentService()
    request = ChatRequest(messages=[Message(role="user", content="Help me find a test")])

    response = agent.handle_chat(request)

    assert response.end_of_conversation is False
    assert response.recommendations == []
    assert "need a little more" in response.reply.lower()


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

    assert response.end_of_conversation is False
    assert len(response.recommendations) >= 1
    assert response.recommendations[0].name
    assert response.recommendations[0].url


def test_refine_with_follow_up_constraint():
    agent = AgentService()
    request = ChatRequest(
        messages=[
            Message(role="user", content="I need a cognitive assessment for a mid-level Java engineer"),
            Message(role="assistant", content="I found a shortlist for this role."),
            Message(role="user", content="Add personality tests too"),
        ]
    )

    response = agent.handle_chat(request)

    assert response.end_of_conversation is False
    assert len(response.recommendations) >= 1
    assert any("personality" in item.test_type.lower() for item in response.recommendations)


def test_compare_named_assessments():
    agent = AgentService()
    request = ChatRequest(
        messages=[Message(role="user", content="Compare SHL Cognitive Ability Test and SHL Java Programming Test")]
    )

    response = agent.handle_chat(request)

    assert response.end_of_conversation is False
    assert response.state == "comparing"
    assert response.comparison_summary
    assert len(response.recommendations) >= 2
    assert any("Cognitive" in item.name for item in response.recommendations)
    assert any("Java" in item.name for item in response.recommendations)


def test_refinement_returns_refining_state():
    agent = AgentService()
    request = ChatRequest(
        messages=[
            Message(role="user", content="I need a cognitive assessment for a mid-level Java engineer"),
            Message(role="assistant", content="I found a shortlist for this role."),
            Message(role="user", content="Add personality tests too"),
        ]
    )

    response = agent.handle_chat(request)

    assert response.state == "refining"


def test_recommend_for_senior_java_skills_request():
    agent = AgentService()
    request = ChatRequest(messages=[Message(role="user", content="I want senior level java skills assessment")])

    response = agent.handle_chat(request)

    assert response.end_of_conversation is False
    assert len(response.recommendations) >= 1
    assert any("Java" in item.name for item in response.recommendations)
    assert response.state == "recommending"


def test_groq_fallback_uses_catalog_reply_when_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    agent = AgentService()

    reply, reply_source, llm_model = agent._maybe_enhance_reply(
        "I want senior java assessment",
        "Catalog fallback",
        [],
        intent="recommendation",
    )

    assert reply == "Catalog fallback"
    assert reply_source == "catalog"
    assert llm_model is None


def test_groq_response_metadata_is_exposed(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "demo-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")

    class FakeGroqClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class FakeMessage:
                        content = "Shortlisted a grounded SHL recommendation for your Java hiring need."

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

    assert response.reply_source == "groq"
    assert response.llm_model == "llama-3.1-8b-instant"


def test_mongo_read_failure_falls_back_to_memory():
    class FailingCollection:
        def find_one(self, query):
            raise RuntimeError("mongo unavailable")

    agent = AgentService()
    agent.mongo_collection = FailingCollection()
    agent.session_store["demo-session"] = [Message(role="user", content="cached")]

    loaded = agent._load_session("demo-session")

    assert loaded[0].content == "cached"
    assert agent.mongo_collection is None


def test_mongo_write_failure_does_not_break_chat():
    class FailingCollection:
        def update_one(self, *args, **kwargs):
            raise RuntimeError("mongo unavailable")

    agent = AgentService()
    agent.mongo_collection = FailingCollection()

    response = agent.handle_chat(
        ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="I am hiring for a mid-level Java software engineer and want a cognitive assessment",
                )
            ]
        ),
        session_id="render-debug",
    )

    assert response.reply
    assert response.session_id == "render-debug"
    assert agent.mongo_collection is None
