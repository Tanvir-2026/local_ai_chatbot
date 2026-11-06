import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.exceptions import AuthNotConfiguredError, UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Security(api_key_header)) -> None:
    if not settings.api_key:
        raise AuthNotConfiguredError()
    if not provided:
        raise UnauthorizedError("Missing API key. Send it in the X-API-Key header.")
    if not secrets.compare_digest(provided.encode(), settings.api_key.encode()):
        raise UnauthorizedError("Invalid API key.")