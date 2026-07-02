from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: List[Message] = Field(default_factory=list)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    url: str
    test_type: str
    confidence: float | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False
    state: str = "recommending"
    comparison_summary: str | None = None
    reply_source: Literal["catalog", "groq"] = "catalog"
    llm_model: str | None = None
