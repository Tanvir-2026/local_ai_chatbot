from fastapi import APIRouter

from app.core.config import settings
from app.schemas.model import ModelsResponse
from app.services import ollama_service

router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ModelsResponse)
def get_models():
    return ModelsResponse(
        default_model=settings.default_model,
        models=ollama_service.list_models(),
    )