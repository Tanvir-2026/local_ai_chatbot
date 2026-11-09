import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import ollama_service

API_KEY = "test-key"
INSTALLED = [
    {"name": "qwen2.5:3b", "size_bytes": 1, "modified_at": None},
    {"name": "llama3.2:3b", "size_bytes": 1, "modified_at": None},
]


class FakeOllama:
    """Records what the backend sends to the model and returns canned replies."""

    def __init__(self):
        self.calls: list[dict] = []
        self.error: Exception | None = None

    def generate_reply(self, messages, model):
        if self.error:
            raise self.error
        self.calls.append({"messages": messages, "model": model})
        return {"content": "Hello from fake model", "prompt_tokens": 10, "completion_tokens": 5}

    def system_prompt(self, call_index: int = -1) -> str:
        return self.calls[call_index]["messages"][0]["content"]


@pytest.fixture
def fake_ollama(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr(ollama_service, "list_models", lambda: INSTALLED)
    monkeypatch.setattr(ollama_service, "generate_reply", fake.generate_reply)
    return fake


@pytest.fixture
def client(tmp_path, monkeypatch, fake_ollama):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "api_key", API_KEY)
    monkeypatch.setattr(settings, "openweather_api_key", "fake-weather-key")
    with TestClient(app) as c:  # "with" runs startup, which creates the tables
        c.headers.update({"X-API-Key": API_KEY})
        yield c


@pytest.fixture
def anon_client(client):
    """Same app, but without the API key header."""
    client.headers.pop("X-API-Key")
    return client

@pytest.fixture(autouse=True)
def no_memory_by_default(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", False)