import pytest

from app.core.exceptions import (
    CityNotFoundError,
    WeatherNotConfiguredError,
    WeatherTimeoutError,
)
from app.services import weather_service

SAMPLE = {
    "city": "Dhaka", "country": "BD", "description": "haze",
    "temperature_c": 31.5, "feels_like_c": 36.0, "humidity": 70, "wind_speed_ms": 3.2,
}


# ------------------------------------------------- detection and extraction
@pytest.mark.parametrize(
    "message,city",
    [
        ("What's the weather in Dhaka today?", "Dhaka"),
        ("Is it raining in London?", "London"),
        ("weather in New York", "New York"),
        ("forecast for Paris tomorrow", "Paris"),
        ("Paris weather", "Paris"),
    ],
)
def test_city_extraction(message, city):
    assert weather_service.is_weather_question(message)
    assert weather_service.extract_city(message) == city


def test_non_weather_message_is_ignored():
    assert not weather_service.is_weather_question("Tell me a joke")


def test_weather_question_without_city():
    assert weather_service.is_weather_question("What's the weather?")
    assert weather_service.extract_city("What's the weather?") is None


# --------------------------------------------------------- through the chat API
def test_weather_data_reaches_the_model_and_response(client, fake_ollama, monkeypatch):
    monkeypatch.setattr(weather_service, "fetch_weather", lambda city: SAMPLE)
    body = client.post("/api/chat", json={"message": "weather in Dhaka today"}).json()

    assert body["weather"]["city"] == "Dhaka"
    assert body["weather"]["temperature_c"] == 31.5
    prompt = fake_ollama.system_prompt()
    assert "LIVE WEATHER DATA" in prompt and "31.5" in prompt


def test_normal_chat_does_not_call_weather(client, fake_ollama, monkeypatch):
    def should_not_run(city):
        raise AssertionError("weather API must not be called")
    monkeypatch.setattr(weather_service, "fetch_weather", should_not_run)
    body = client.post("/api/chat", json={"message": "Tell me a joke"}).json()
    assert body["weather"] is None
    assert "LIVE WEATHER DATA" not in fake_ollama.system_prompt()


@pytest.mark.parametrize(
    "error",
    [CityNotFoundError("City 'Asdfghjkl' was not found."),
     WeatherTimeoutError(),
     WeatherNotConfiguredError()],
    ids=["invalid-city", "timeout", "missing-key"],
)
def test_weather_failures_never_fabricate(client, fake_ollama, monkeypatch, error):
    def fail(city):
        raise error
    monkeypatch.setattr(weather_service, "fetch_weather", fail)

    r = client.post("/api/chat", json={"message": "weather in Asdfghjkl"})
    assert r.status_code == 200  # the chat still answers
    assert r.json()["weather"] is None
    prompt = fake_ollama.system_prompt()
    assert "failed" in prompt
    assert "Do not guess or invent" in prompt