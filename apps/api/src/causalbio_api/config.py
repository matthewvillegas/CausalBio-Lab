"""Environment-backed API configuration without embedded secrets."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAUSALBIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="ENV")
    web_origin: str = "http://localhost:3000"
    artifact_dir: Path = Path("artifacts")
    no_llm: bool = True
    no_telemetry: bool = True
    live_research_enabled: bool = True
    source_cache_dir: Path = Path(__file__).resolve().parents[4] / "data/cache/sources"
    research_database: Path = Path(__file__).resolve().parents[4] / "data/research.sqlite3"
    max_request_bytes: int = 1_000_000
    local_rate_limit_per_minute: int = 180


@lru_cache
def get_settings() -> Settings:
    return Settings()
