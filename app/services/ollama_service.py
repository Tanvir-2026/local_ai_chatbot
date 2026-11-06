import httpx
import json
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    ModelNotFoundError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


def list_models() -> list[dict]:
    try:
        r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=10)
        r.raise_for_status()
    except httpx.ConnectError:
        raise OllamaUnavailableError()
    except httpx.TimeoutException:
        raise OllamaTimeoutError()
    except httpx.HTTPStatusError as e:
        raise AppError(f"Ollama error: {e.response.text}")
    return [
        {
            "name": m["name"],
            "size_bytes": m.get("size"),
            "modified_at": m.get("modified_at"),
        }
        for m in r.json().get("models", [])
    ]


def generate_reply(messages: list[dict], model: str) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": _options(),
    }
    try:
        r = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
            timeout=settings.request_timeout,
        )
        r.raise_for_status()
    except httpx.ConnectError:
        raise OllamaUnavailableError()
    except httpx.TimeoutException:
        raise OllamaTimeoutError()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ModelNotFoundError(
                f"Model '{model}' not found. Run: ollama pull {model}"
            )
        raise AppError(f"Ollama error: {e.response.text}")

    data = r.json()
    return {
        "content": data["message"]["content"],
        "prompt_tokens": data.get("prompt_eval_count"),
        "completion_tokens": data.get("eval_count"),
    }

def open_chat_stream(messages: list[dict], model: str):
    """Opens a streaming chat request. Returns (client, response).
    The caller must close both. Raises mapped errors before any data is sent."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": _options(),
    }
    timeout = httpx.Timeout(
        connect=10, read=settings.request_timeout, write=10, pool=10
    )
    client = httpx.Client(timeout=timeout)
    try:
        request = client.build_request(
            "POST", f"{settings.ollama_url}/api/chat", json=payload
        )
        response = client.send(request, stream=True)
        if response.status_code != 200:
            body = response.read().decode(errors="replace")
            response.close()
            if response.status_code == 404:
                raise ModelNotFoundError(
                    f"Model '{model}' not found. Run: ollama pull {model}"
                )
            raise AppError(f"Ollama error: {body}")
        return client, response
    except httpx.ConnectError:
        client.close()
        raise OllamaUnavailableError()
    except httpx.TimeoutException:
        client.close()
        raise OllamaTimeoutError()
    except Exception:
        client.close()
        raise


def iter_chat_stream(response):
    """Yields Ollama's JSON chunks. Raises AppError subclasses on failure."""
    try:
        for line in response.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                raise AppError("Received malformed data from Ollama.")
            if "error" in chunk:
                raise AppError(f"Ollama error: {chunk['error']}")
            yield chunk
    except httpx.TimeoutException:
        raise OllamaTimeoutError()
    except httpx.TransportError:
        raise OllamaUnavailableError("Connection to Ollama was lost during streaming.")

def resolve_model(requested: str) -> str:
    """Returns the installed model name matching `requested`, or raises a 404
    that lists the installed models. 'llama3.2' matches 'llama3.2:latest'."""
    installed = [m["name"] for m in list_models()]
    candidates = [requested] if ":" in requested else [requested, f"{requested}:latest"]
    for name in candidates:
        if name in installed:
            return name
    raise ModelNotFoundError(
        f"Model '{requested}' is not installed. "
        f"Installed models: {', '.join(installed) or 'none'}. "
        f"Install it with: ollama pull {requested}"
    )

def _options() -> dict:
    return {
        "temperature": settings.temperature,
        "top_p": settings.top_p,
        "num_predict": settings.max_tokens,
    }