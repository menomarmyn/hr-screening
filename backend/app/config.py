from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "KOZ HR Screener"
    api_key: str = "dev-key"  # простой ключ для доступа к API (заголовок X-API-Key)

    database_url: str = "postgresql+psycopg://hr:hr@localhost:5432/hr"
    redis_url: str = "redis://localhost:6379/0"
    celery_eager: bool = False  # True — задачи выполняются синхронно (dev/тесты)

    # LLM: mock | anthropic | openai | gemini | ollama
    llm_provider: str = "mock"
    llm_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"

    # Embeddings: hash (без внешних вызовов) | openai | ollama
    embedding_provider: str = "hash"
    embedding_model: str = ""
    embedding_dim: int = 384

    # Безопасность: маскировать ПДн (телефоны, email, ИИН) перед отправкой в LLM
    mask_pii: bool = True
    max_upload_mb: int = 5

    # Интеграции. dry_run=True — запросы пишутся в журнал, но не отправляются
    integrations_dry_run: bool = True
    bitrix24_webhook_url: str = ""
    onec_base_url: str = ""
    onec_user: str = ""
    onec_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
