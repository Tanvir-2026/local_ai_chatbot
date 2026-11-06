import json
import sqlite3
import time
from collections.abc import Iterator

from app.core.config import settings
from app.core.exceptions import AppError, ConversationNotFoundError, WeatherError
from app.db.database import get_connection
from app.models import conversation as conversation_model
from app.models import message as message_model
from app.schemas.chat import ChatRequest, ChatResponse, Usage
from app.services import ollama_service, weather_service


def _weather_context(message: str) -> tuple[dict | None, str | None]:
    """Returns (weather_data, note_for_the_system_prompt)."""
    if not weather_service.is_weather_question(message):
        return None, None

    city = weather_service.extract_city(message)
    if not city:
        return None, (
            "The user may be asking about the weather but did not name a city. "
            "If they are asking about weather, ask which city. Never guess weather."
        )

    try:
        data = weather_service.fetch_weather(city)
    except WeatherError as e:
        return None, (
            f"A live weather lookup for '{city}' failed: {e.detail} "
            "Tell the user plainly that you could not get the weather right now. "
            "Do not guess or invent any weather values."
        )
    return data, weather_service.format_for_llm(data)


def _prepare(db: sqlite3.Connection, req: ChatRequest):
    """Validates the request and builds the LLM prompt.
    Returns (model, llm_messages, weather_data)."""
    model = ollama_service.resolve_model(req.model or settings.default_model)

    history: list[dict] = []
    if req.conversation_id:
        if not conversation_model.get(db, req.conversation_id):
            raise ConversationNotFoundError()
        history = message_model.recent(
            db, req.conversation_id, settings.max_history_messages
        )

    weather_data, weather_note = _weather_context(req.message)

    system_prompt = settings.system_prompt
    if weather_note:
        system_prompt += "\n\n" + weather_note
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": req.message}]
    )
    return model, llm_messages, weather_data


def _save_turn(
    db: sqlite3.Connection,
    conversation_id: str | None,
    user_text: str,
    reply: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    duration_ms: int,
) -> tuple[str, str]:
    """Saves the user message and assistant reply. Returns (conversation_id, created_at)."""
    if not conversation_id:
        conversation_id = conversation_model.create(db, user_text[:50])["id"]
    message_model.add(db, conversation_id, "user", user_text)
    saved = message_model.add(
        db,
        conversation_id,
        "assistant",
        reply,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration_ms=duration_ms,
    )
    conversation_model.touch(db, conversation_id)
    db.commit()
    return conversation_id, saved["created_at"]


def _total(prompt_t: int | None, completion_t: int | None) -> int | None:
    if prompt_t is None or completion_t is None:
        return None
    return prompt_t + completion_t


# ---------------------------------------------------------------- normal chat
def handle_chat(db: sqlite3.Connection, req: ChatRequest) -> ChatResponse:
    model, llm_messages, weather_data = _prepare(db, req)

    start = time.perf_counter()
    result = ollama_service.generate_reply(llm_messages, model)
    duration_ms = int((time.perf_counter() - start) * 1000)

    conversation_id, created_at = _save_turn(
        db,
        req.conversation_id,
        req.message,
        result["content"],
        model,
        result["prompt_tokens"],
        result["completion_tokens"],
        duration_ms,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        model=model,
        reply=result["content"],
        usage=Usage(
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=_total(result["prompt_tokens"], result["completion_tokens"]),
            response_time_ms=duration_ms,
        ),
        created_at=created_at,
        weather=weather_data,
    )


# ------------------------------------------------------------------ streaming
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def start_chat_stream(req: ChatRequest) -> Iterator[str]:
    """Validates and opens the Ollama stream NOW, so setup problems raise normal
    HTTP errors. Returns a generator of SSE events."""
    start = time.perf_counter()

    db = get_connection()
    try:
        model, llm_messages, weather_data = _prepare(db, req)
    finally:
        db.close()

    client, response = ollama_service.open_chat_stream(llm_messages, model)
    return _stream_events(req, model, weather_data, start, client, response)


def _stream_events(req, model, weather_data, start, client, response) -> Iterator[str]:
    parts: list[str] = []
    prompt_t = completion_t = None
    finished = False
    try:
        yield _sse("start", {"model": model, "weather": weather_data})

        for chunk in ollama_service.iter_chat_stream(response):
            token = chunk.get("message", {}).get("content", "")
            if token:
                parts.append(token)
                yield _sse("token", {"content": token})
            if chunk.get("done"):
                prompt_t = chunk.get("prompt_eval_count")
                completion_t = chunk.get("eval_count")
                finished = True

        if not finished:
            raise AppError("The model stream ended unexpectedly.")

        duration_ms = int((time.perf_counter() - start) * 1000)
        reply = "".join(parts)

        db = get_connection()
        try:
            conversation_id, created_at = _save_turn(
                db, req.conversation_id, req.message, reply,
                model, prompt_t, completion_t, duration_ms,
            )
        finally:
            db.close()

        yield _sse(
            "done",
            {
                "conversation_id": conversation_id,
                "model": model,
                "created_at": created_at,
                "usage": {
                    "prompt_tokens": prompt_t,
                    "completion_tokens": completion_t,
                    "total_tokens": _total(prompt_t, completion_t),
                    "response_time_ms": duration_ms,
                },
            },
        )
    except AppError as e:
        yield _sse("error", {"detail": e.detail})
    except Exception:
        yield _sse("error", {"detail": "Unexpected error while streaming."})
    finally:
        # Also runs when the client disconnects: closing stops Ollama generating.
        response.close()
        client.close()