from typing import Dict, List

from app.schemas import ChatRequest, Message
from app.services.agent_service import AgentService


DEFAULT_RECRUITER_PERSONA_TRACES: Dict[str, List[str]] = {
    "java_mid_cognitive": [
        "I need a cognitive assessment for a mid-level Java engineer",
    ],
    "engineering_refinement": [
        "I need a cognitive assessment for a mid-level Java engineer",
        "Add personality tests too",
    ],
    "data_analyst_screening": [
        "I am hiring an entry-level data analyst and need numerical or cognitive testing",
    ],
    "stakeholder_comparison": [
        "Compare SHL Cognitive Ability Test and SHL Java Programming Test",
    ],
    "vague_intake": [
        "Help me find a test",
    ],
    "out_of_scope_request": [
        "Give me legal advice about hiring tests",
    ],
}


class EvaluationHarness:
    def __init__(self, agent: AgentService | None = None) -> None:
        self.agent = agent or AgentService()

    def run_trace(self, trace: List[str]) -> dict:
        messages = [Message(role="user", content=content) for content in trace]
        response = self.agent.handle_chat(ChatRequest(messages=messages))
        confidence_values = [item.confidence for item in response.recommendations if item.confidence is not None]
        return {
            "reply": response.reply,
            "recommendation_count": len(response.recommendations),
            "end_of_conversation": response.end_of_conversation,
            "state": response.state,
            "reply_source": response.reply_source,
            "llm_model": response.llm_model,
            "average_confidence": round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None,
        }

    def run_traces(self, traces: List[List[str]]) -> List[dict]:
        return [self.run_trace(trace) for trace in traces]

    def run_recruiter_persona_suite(self, traces: Dict[str, List[str]] | None = None) -> Dict[str, dict]:
        selected_traces = traces or DEFAULT_RECRUITER_PERSONA_TRACES
        return {persona: self.run_trace(trace) for persona, trace in selected_traces.items()}