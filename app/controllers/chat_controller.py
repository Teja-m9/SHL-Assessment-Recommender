from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.services.agent_service import AgentService


router = APIRouter()
agent = AgentService()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return agent.handle_chat(request)