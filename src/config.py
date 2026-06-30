"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    # LLM (Google Gemini)
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"

    # Database (admin / migrasi / load_data)
    POSTGRES_USER: str = "textsql"
    POSTGRES_PASSWORD: str = "textsql_secret"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "olist"

    # Database (read-only role khusus LLM agent)
    DB_READONLY_USER: str = "llm_readonly"
    DB_READONLY_PASSWORD: str = "change_me_readonly"

    @property
    def database_url(self) -> str:
        """Koneksi admin. Dipakai migrasi, load_data, dan /health."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def agent_database_url(self) -> str:
        """Koneksi read-only yang dipakai LLM agent. Tidak punya grant tulis."""
        return (
            f"postgresql://{self.DB_READONLY_USER}:{self.DB_READONLY_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # App
    APP_PORT: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()