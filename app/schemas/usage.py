from pydantic import BaseModel


class UsageStats(BaseModel):
    requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    avg_response_time_ms: float | None = None
    avg_tokens_per_second: float | None = None


class ModelUsage(UsageStats):
    model: str


class UsageResponse(BaseModel):
    conversation_id: str | None = None
    total: UsageStats
    by_model: list[ModelUsage]