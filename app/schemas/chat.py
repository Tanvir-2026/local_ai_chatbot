from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    model: str | None = None


class Usage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    response_time_ms: int


class WeatherData(BaseModel):
    city: str
    country: str | None = None
    description: str | None = None
    temperature_c: float
    feels_like_c: float
    humidity: int
    wind_speed_ms: float | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    model: str
    reply: str
    usage: Usage
    created_at: str
    weather: WeatherData | None = None