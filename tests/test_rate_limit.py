from types import SimpleNamespace

from app.core import rate_limit
from app.core.config import settings
from tests.conftest import API_KEY


def _enable(monkeypatch, limit: int):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", limit)


def test_requests_over_the_limit_get_429(client, monkeypatch):
    _enable(monkeypatch, 2)
    for _ in range(2):
        assert client.post("/api/chat", json={"message": "hi"}).status_code == 200

    r = client.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert "Too many requests" in r.json()["detail"]


def test_stream_endpoint_shares_the_limit(client, monkeypatch):
    _enable(monkeypatch, 1)
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 429


def test_other_endpoints_are_not_limited(client, monkeypatch):
    _enable(monkeypatch, 1)
    for _ in range(5):
        assert client.get("/api/health").status_code == 200


def test_requests_without_a_valid_key_do_not_use_up_the_limit(client, monkeypatch):
    _enable(monkeypatch, 1)
    client.headers.pop("X-API-Key")
    for _ in range(3):
        assert client.post("/api/chat", json={"message": "hi"}).status_code == 401
    client.headers["X-API-Key"] = API_KEY
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 200


def test_limit_resets_after_the_window(client, monkeypatch):
    _enable(monkeypatch, 1)
    clock = {"t": 1000.0}
    monkeypatch.setattr(rate_limit, "time", SimpleNamespace(monotonic=lambda: clock["t"]))

    assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 429

    clock["t"] += settings.rate_limit_window + 1
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 200