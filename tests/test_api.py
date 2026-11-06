from app.core.exceptions import AppError, OllamaUnavailableError
from app.services import ollama_service


# ------------------------------------------------------------ auth (Task 9)
def test_missing_api_key_is_rejected(anon_client):
    r = anon_client.get("/api/health")
    assert r.status_code == 401


def test_wrong_api_key_is_rejected(anon_client):
    r = anon_client.get("/api/health", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"]


def test_server_without_configured_key_fails_closed(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_key", "")
    assert client.get("/api/health").status_code == 503


# ------------------------------------------------- health and models (Task 2)
def test_health_ok(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["ollama"] is True
    assert body["default_model_available"] is True


def test_health_degraded_when_ollama_down(client, monkeypatch):
    def boom():
        raise OllamaUnavailableError()
    monkeypatch.setattr(ollama_service, "list_models", boom)
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["ollama"] is False


def test_list_models(client):
    body = client.get("/api/models").json()
    names = [m["name"] for m in body["models"]]
    assert names == ["qwen2.5:3b", "llama3.2:3b"]


# ------------------------------------------------------ chat and memory (Task 3)
def test_chat_creates_conversation_and_returns_usage(client):
    r = client.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "Hello from fake model"
    assert body["model"] == "qwen2.5:3b"
    assert body["conversation_id"]
    assert body["usage"]["prompt_tokens"] == 10
    assert body["usage"]["completion_tokens"] == 5
    assert body["usage"]["total_tokens"] == 15
    assert body["usage"]["response_time_ms"] >= 0
    assert body["weather"] is None


def test_second_message_includes_history(client, fake_ollama):
    first = client.post("/api/chat", json={"message": "My name is Tanvir"}).json()
    client.post(
        "/api/chat",
        json={"message": "What is my name?", "conversation_id": first["conversation_id"]},
    )
    sent = fake_ollama.calls[-1]["messages"]
    contents = [m["content"] for m in sent]
    assert "My name is Tanvir" in contents
    assert sent[-1] == {"role": "user", "content": "What is my name?"}


def test_conversation_list_get_and_delete(client):
    cid = client.post("/api/chat", json={"message": "hello"}).json()["conversation_id"]

    listing = client.get("/api/conversations").json()
    assert len(listing) == 1 and listing[0]["message_count"] == 2

    detail = client.get(f"/api/conversations/{cid}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert all(m["created_at"] for m in detail["messages"])

    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.get("/api/conversations").json() == []


# ------------------------------------------------------- error handling (Task 10)
def test_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_missing_message_field_is_rejected(client):
    assert client.post("/api/chat", json={}).status_code == 422


def test_unknown_conversation_returns_404(client):
    r = client.post("/api/chat", json={"message": "hi", "conversation_id": "nope"})
    assert r.status_code == 404
    assert client.get("/api/conversations/nope").status_code == 404
    assert client.delete("/api/conversations/nope").status_code == 404


def test_uninstalled_model_returns_404_listing_installed(client):
    r = client.post("/api/chat", json={"message": "hi", "model": "qwen2.5:99b"})
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "qwen2.5:99b" in detail and "qwen2.5:3b" in detail


def test_model_can_be_switched_per_request(client, fake_ollama):
    a = client.post("/api/chat", json={"message": "hi", "model": "qwen2.5:3b"}).json()
    b = client.post(
        "/api/chat",
        json={"message": "hi again", "model": "llama3.2:3b",
              "conversation_id": a["conversation_id"]},
    ).json()
    assert a["model"] == "qwen2.5:3b"
    assert b["model"] == "llama3.2:3b"
    assert [c["model"] for c in fake_ollama.calls] == ["qwen2.5:3b", "llama3.2:3b"]


def test_short_model_name_resolves_to_latest_tag(client, monkeypatch):
    monkeypatch.setattr(
        ollama_service, "list_models",
        lambda: [{"name": "mistral:latest", "size_bytes": 1, "modified_at": None}],
    )
    r = client.post("/api/chat", json={"message": "hi", "model": "mistral"})
    assert r.json()["model"] == "mistral:latest"


def test_ollama_down_returns_503_and_saves_nothing(client, fake_ollama):
    fake_ollama.error = OllamaUnavailableError()
    r = client.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 503
    assert client.get("/api/conversations").json() == []


# ----------------------------------------------------------- usage (Task 8)
def test_usage_summary(client):
    cid = client.post("/api/chat", json={"message": "one"}).json()["conversation_id"]
    client.post("/api/chat", json={"message": "two", "conversation_id": cid})

    body = client.get("/api/usage").json()
    assert body["total"]["requests"] == 2
    assert body["total"]["prompt_tokens"] == 20
    assert body["total"]["completion_tokens"] == 10
    assert body["total"]["total_tokens"] == 30
    assert body["by_model"][0]["model"] == "qwen2.5:3b"

    scoped = client.get(f"/api/usage?conversation_id={cid}").json()
    assert scoped["total"]["requests"] == 2
    assert client.get("/api/usage?conversation_id=abc").status_code == 404


# ------------------------------------------------------- streaming (Task 6)
class _FakeResponse:
    def close(self):
        pass


def _patch_stream(monkeypatch, chunks, fail_after: int | None = None):
    def fake_open(messages, model):
        return _FakeResponse(), _FakeResponse()

    def fake_iter(response):
        for i, chunk in enumerate(chunks):
            if fail_after is not None and i == fail_after:
                raise AppError("Connection to Ollama was lost during streaming.")
            yield chunk

    monkeypatch.setattr(ollama_service, "open_chat_stream", fake_open)
    monkeypatch.setattr(ollama_service, "iter_chat_stream", fake_iter)


STREAM_CHUNKS = [
    {"message": {"content": "Hel"}, "done": False},
    {"message": {"content": "lo"}, "done": False},
    {"message": {"content": ""}, "done": True, "prompt_eval_count": 7, "eval_count": 2},
]


def test_stream_sends_tokens_then_done_and_saves(client, monkeypatch):
    _patch_stream(monkeypatch, STREAM_CHUNKS)
    r = client.post("/api/chat/stream", json={"message": "hi"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    text = r.text
    assert text.index("event: start") < text.index("event: token") < text.index("event: done")
    assert text.count("event: token") == 2
    assert '"total_tokens": 9' in text

    convo = client.get("/api/conversations").json()
    assert len(convo) == 1
    messages = client.get(f"/api/conversations/{convo[0]['id']}").json()["messages"]
    assert messages[1]["content"] == "Hello"


def test_stream_failure_midway_sends_error_and_saves_nothing(client, monkeypatch):
    _patch_stream(monkeypatch, STREAM_CHUNKS, fail_after=1)
    r = client.post("/api/chat/stream", json={"message": "hi"})
    assert r.status_code == 200  # headers were already sent
    assert "event: error" in r.text
    assert "event: done" not in r.text
    assert client.get("/api/conversations").json() == []


def test_stream_with_unknown_model_returns_http_404(client):
    r = client.post("/api/chat/stream", json={"message": "hi", "model": "nope:1b"})
    assert r.status_code == 404