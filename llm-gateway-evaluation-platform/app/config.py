from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LLM Gateway & Model Evaluation Platform"
    environment: str = "development"
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    site_url: str = "http://localhost:8000"
    site_name: str = "LLM Gateway"
    database_url: str = "postgresql+psycopg://llm:llm@localhost:5432/llm_gateway"
    default_model: str = "openrouter/free"
    evaluation_model: str = "openai/gpt-5.5"
    http_timeout_seconds: float = 90.0
    model_cache_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
