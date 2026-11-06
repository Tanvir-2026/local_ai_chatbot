from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    backend: bool
    ollama: bool
    default_model: str
    default_model_available: bool