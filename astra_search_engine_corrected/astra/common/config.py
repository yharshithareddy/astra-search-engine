from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASTRA_", case_sensitive=False)

    db_path: str = "./data/astra.db"

    user_agent: str = "AstraSearchBot/1.0"
    crawl_delay_seconds: float = 1.0
    http_timeout_seconds: float = 10.0
    max_response_bytes: int = 2_000_000  # 2MB safety cap

    # ranking
    title_boost: float = 2.0
    k1: float = 1.2
    b: float = 0.75

    # tokenization
    min_token_len: int = 2


settings = Settings()
