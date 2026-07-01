from typing import List

from app.agent import AgentService
from app.schemas import ChatRequest, Message


class EvaluationHarness:
    def __init__(self, agent: AgentService | None = None) -> None:
        self.agent = agent or AgentService()

    def run_trace(self, trace: List[str]) -> dict:
        messages = [Message(role="user", content=content) for content in trace]
        response = self.agent.handle_chat(ChatRequest(messages=messages))
        return {
            "reply": response.reply,
            "recommendation_count": len(response.recommendations),
            "end_of_conversation": response.end_of_conversation,
        }

    def run_traces(self, traces: List[List[str]]) -> List[dict]:
        return [self.run_trace(trace) for trace in traces]
