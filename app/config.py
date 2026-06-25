"""Centralised application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    app_name: str = Field(default="Health Campaign AI", alias="APP_NAME")
    app_env: str = Field(default="production", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_port: int = Field(default=8001, alias="API_PORT")

    # --- Database ---
    db_url: str = Field(
        default="mysql+pymysql://health_user:health_pass@health_campaign_db:3306/health_campaign_manager",
        alias="DB_URL",
    )
    db_max_rows: int = Field(default=1000, alias="DB_MAX_ROWS")
    db_query_timeout: int = Field(default=15, alias="DB_QUERY_TIMEOUT")

    # --- LLM (Groq - free online AI) ---
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_timeout: int = Field(default=60, alias="LLM_TIMEOUT")

    # --- Security ---
    jwt_secret: str = Field(default="change-me-please", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=120, alias="JWT_EXPIRE_MINUTES")
    api_keys: str = Field(default="demo-api-key-change-me", alias="API_KEYS")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")

    # --- Rate limiting ---
    rate_limit: str = Field(default="30/minute", alias="RATE_LIMIT")

    # --- CORS ---
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # --- Redis ---
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    cache_ttl: int = Field(default=300, alias="CACHE_TTL")

    @property
    def api_key_list(self) -> List[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
