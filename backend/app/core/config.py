from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI ClinicOS"
    environment: str = "development"
    secret_key: str = Field(min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    database_url: str
    # Ollama is the only AI engine used by AI ClinicOS. Every AI feature
    # (AI Assistant, symptom analysis, medicine recommendations, patient
    # summaries, chat) flows Browser -> FastAPI -> Ollama -> Response.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout_seconds: int = 120
    backend_cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000"
    upload_dir: str = "app/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
