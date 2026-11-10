from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local AI Chatbot"
    ollama_url: str = "http://localhost:11434"
    default_model: str = "qwen2.5:3b"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    request_timeout: int = 180
    max_history_messages: int = 20
    system_prompt: str = "You are a helpful assistant."
    database_path: str = "chatbot.db"
    openweather_api_key: str = ""
    openweather_api_url: str = ""
    api_key: str = ""
    weather_timeout: int = 10
    memory_enabled: bool 
    chroma_path: str 
    embed_model: str 
    memory_top_k: int 
    memory_max_distance: float 
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_window: int = 60
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()