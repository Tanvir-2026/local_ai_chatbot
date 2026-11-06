# Local AI Chatbot Backend

A FastAPI backend for a chatbot powered by local LLMs (Ollama). It supports conversation memory in SQLite, live weather lookups (OpenWeatherMap), streaming responses, multiple models, token/performance tracking, and API-key authentication.

**Stack:** Python, FastAPI, Ollama (Qwen 2.5 3B / Llama 3.2 3B), SQLite (raw SQL), OpenWeatherMap, pytest

## Setup

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/download)

```bash
# 1. Download the models (~2 GB each)
ollama pull qwen2.5:3b
ollama pull llama3.2:3b

# 2. Install dependencies
uv sync

```


## Environment variables

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Key clients must send in `X-API-Key` (**required**) | none |
| `OPENWEATHER_API_KEY` | OpenWeatherMap key ([get one](https://openweathermap.org/api)) | none |
| `OLLAMA_URL` | Ollama server address | `http://localhost:11434` |
| `DEFAULT_MODEL` | Model used when a request names none | `qwen2.5:3b` |
| `TEMPERATURE` | Generation temperature | `0.7` |
| `TOP_P` | Nucleus sampling | `0.9` |
| `MAX_TOKENS` | Max tokens per reply | `512` |
| `REQUEST_TIMEOUT` | Ollama timeout in seconds | `180` |
| `WEATHER_TIMEOUT` | Weather API timeout in seconds | `10` |
| `MAX_HISTORY_MESSAGES` | Past messages sent to the model | `20` |
| `SYSTEM_PROMPT` | The assistant's role and rules | see `.env.example` |
| `DATABASE_PATH` | SQLite file location | `chatbot.db` |



## Run

```bash
uv run uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs (click **Authorize** and paste your API key)
- The SQLite tables are created automatically on first start.

## API

All `/api` endpoints require the header `X-API-Key: <your key>`. A missing or invalid key returns `401`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Send a message, get a full reply |
| POST | `/api/chat/stream` | Same, streamed token by token (SSE) |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get a conversation with all messages |
| DELETE | `/api/conversations/{id}` | Delete a conversation (`204`) |
| GET | `/api/models` | List installed local models |
| GET | `/api/health` | Backend and model availability |
| GET | `/api/usage` | Token and timing summary (optional `?conversation_id=`) |



### Errors

| Status | Meaning |
|---|---|
| 401 | Missing or invalid API key |
| 404 | Unknown conversation, or model not installed (the message lists installed models) |
| 422 | Invalid request body |
| 503 | Ollama not running, or `API_KEY` not configured on the server |
| 504 | Ollama timed out |

## Tests

```bash
uv run pytest -v
```

The tests mock Ollama and OpenWeatherMap and use a temporary database, so they run without Ollama, internet, or API keys.

## Project structure

```
app/
├── main.py          # app setup, router registration
├── core/            # config (env), security (API key), exceptions
├── db/              # SQLite connection and schema
├── models/          # raw SQL queries per table
├── schemas/         # Pydantic request/response models
├── routes/          # URL definitions
├── controllers/     # business logic
└── services/        # Ollama and OpenWeatherMap clients
tests/               # pytest suite
```