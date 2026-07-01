from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import Message

if __package__ in {None, ""}:
    from app.agent import AgentService
    from app.schemas import ChatRequest, ChatResponse
else:
    from .agent import AgentService
    from .schemas import ChatRequest, ChatResponse

class ChatRequestWithSession(BaseModel):
    session_id: str | None = None
    messages: list[dict] = []


class ClearSessionRequest(BaseModel):
    session_id: str | None = None


app = FastAPI(title="SHL Assessment Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
agent = AgentService()


@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["access-control-allow-origin"] = "*"
    response.headers["access-control-allow-credentials"] = "true"
    return response


@app.options("/{path:path}")
async def preflight(path: str) -> Response:
    return Response(
        status_code=200,
        headers={
            "access-control-allow-origin": "*",
            "access-control-allow-credentials": "true",
            "access-control-allow-methods": "*",
            "access-control-allow-headers": "*",
        },
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequestWithSession) -> ChatResponse:
    normalized_messages = []
    for message in request.messages:
        if isinstance(message, dict):
            normalized_messages.append(Message(**message))
        else:
            normalized_messages.append(message)

    payload = ChatRequest(messages=normalized_messages)
    response = agent.handle_chat(payload, session_id=request.session_id)
    return response


@app.post("/sessions/clear")
def clear_session(request: ClearSessionRequest) -> dict:
    agent.clear_session(request.session_id)
    return {"cleared": True, "session_id": request.session_id}
