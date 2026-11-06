from fastapi import APIRouter

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.health import HealthResponse
from app.services import ollama_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health():
    ollama_ok, model_ok = False, False
    try:
        names = [m["name"] for m in ollama_service.list_models()]
        ollama_ok = True
        model_ok = settings.default_model in names
    except AppError:
        pass
    return HealthResponse(
        status="ok" if ollama_ok and model_ok else "degraded",
        backend=True,
        ollama=ollama_ok,
        default_model=settings.default_model,
        default_model_available=model_ok,
    )