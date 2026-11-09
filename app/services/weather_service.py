import re

import httpx

from app.core.config import settings
from app.core.exceptions import (
    CityNotFoundError,
    WeatherError,
    WeatherNotConfiguredError,
    WeatherTimeoutError,
)



WEATHER_KEYWORDS = re.compile(
    r"\b(weather|temperature|forecast|rain(?:ing|y)?|snow(?:ing|y)?|"
    r"humid(?:ity)?|sunny|cloudy|windy|storm(?:y)?)\b",
    re.IGNORECASE,
)


CITY_AFTER_PREPOSITION = re.compile(
    r"\b(?:in|at|for|of|near)\s+([A-Za-z][A-Za-z .'\-]*?)"
    r"(?=\s+(?:today|tomorrow|tonight|now|right now|currently|please|this|like)\b|[?.!,]|$)",
    re.IGNORECASE,
)


CITY_BEFORE_KEYWORD = re.compile(
    r"\b([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)(?:'s)? "
    r"(?:weather|temperature|forecast)\b"
)

NOT_CITIES = {"The", "What", "How", "Today", "Tomorrow", "Current", "Tell", "Show"}


def is_weather_question(message: str) -> bool:
    return bool(WEATHER_KEYWORDS.search(message))


def extract_city(message: str) -> str | None:
    match = CITY_AFTER_PREPOSITION.search(message)
    if match:
        return match.group(1).strip().title()
    match = CITY_BEFORE_KEYWORD.search(message)
    if match and match.group(1) not in NOT_CITIES:
        return match.group(1).strip()
    return None


def fetch_weather(city: str) -> dict:
    if not settings.openweather_api_key:
        raise WeatherNotConfiguredError()

    try:
        r = httpx.get(
            settings.openweather_api_key,
            params={"q": city, "appid": settings.openweather_api_key, "units": "metric"},
            timeout=settings.weather_timeout,
        )
    except httpx.TimeoutException:
        raise WeatherTimeoutError()
    except httpx.HTTPError:
        raise WeatherError("Could not reach the weather service.")

    if r.status_code == 404:
        raise CityNotFoundError(f"City '{city}' was not found.")
    if r.status_code == 401:
        raise WeatherError("The OpenWeatherMap API key is invalid or not activated yet.")
    if r.status_code == 429:
        raise WeatherError("The weather service rate limit was reached.")
    if r.status_code != 200:
        raise WeatherError(f"The weather service returned status {r.status_code}.")

    d = r.json()
    return {
        "city": d.get("name", city),
        "country": d.get("sys", {}).get("country"),
        "description": d["weather"][0]["description"] if d.get("weather") else None,
        "temperature_c": d["main"]["temp"],
        "feels_like_c": d["main"]["feels_like"],
        "humidity": d["main"]["humidity"],
        "wind_speed_ms": d.get("wind", {}).get("speed"),
    }


def format_for_llm(w: dict) -> str:
    place = f"{w['city']}, {w['country']}" if w["country"] else w["city"]
    return (
        "LIVE WEATHER DATA from OpenWeatherMap, retrieved just now:\n"
        f"City: {place}\n"
        f"Conditions: {w['description']}\n"
        f"Temperature: {w['temperature_c']}°C (feels like {w['feels_like_c']}°C)\n"
        f"Humidity: {w['humidity']}%\n"
        f"Wind speed: {w['wind_speed_ms']} m/s\n"
        "Answer the user's weather question using ONLY this data. "
        "Do not add any weather values that are not listed here."
    )