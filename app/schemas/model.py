from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    size_bytes: int | None = None
    modified_at: str | None = None


class ModelsResponse(BaseModel):
    default_model: str
    models: list[ModelInfo]