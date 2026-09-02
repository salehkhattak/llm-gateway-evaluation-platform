from pydantic import BaseModel, Field
from typing import Any, Literal

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: Any

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    evaluate: bool = True

class ChatResponse(BaseModel):
    request_id: str
    model: str
    content: str
    latency_ms: float
    usage: dict[str, int]
    estimated_cost_usd: float
    quality_score: float | None = None

class CompareRequest(BaseModel):
    prompt: str
    models: list[str] = Field(min_length=2, max_length=8)
    system_prompt: str | None = None
    judge_model: str | None = None

class CompareResult(BaseModel):
    model: str
    success: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    quality_score: float | None = None
    response: str | None = None
    error: str | None = None

class CompareResponse(BaseModel):
    prompt: str
    results: list[CompareResult]
