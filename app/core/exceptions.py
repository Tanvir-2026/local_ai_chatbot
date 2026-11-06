from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class OllamaUnavailableError(AppError):
    status_code = 503
    detail = "Cannot connect to Ollama. Is it running?"


class OllamaTimeoutError(AppError):
    status_code = 504
    detail = "Ollama request timed out."


class ModelNotFoundError(AppError):
    status_code = 404
    detail = "Model not found."


class ConversationNotFoundError(AppError):
    status_code = 404
    detail = "Conversation not found."

class WeatherError(AppError):
    status_code = 502
    detail = "Weather service error."


class WeatherNotConfiguredError(WeatherError):
    status_code = 503
    detail = "Weather service is not configured (missing OPENWEATHER_API_KEY)."


class CityNotFoundError(WeatherError):
    status_code = 404
    detail = "City not found."


class WeatherTimeoutError(WeatherError):
    status_code = 504
    detail = "The weather service timed out."


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Missing or invalid API key."


class AuthNotConfiguredError(AppError):
    status_code = 503
    detail = "Server authentication is not configured (missing API_KEY)."

    
def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})