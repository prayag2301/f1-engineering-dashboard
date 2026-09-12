from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent if APP_ROOT.name == "backend" else APP_ROOT


class Settings(BaseSettings):
    APP_NAME: str = "F1 Engineering Dashboard"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://f1user:f1pass@db:5432/f1dashboard"
    API_V1_PREFIX: str = "/api/v1"
    REDIS_URL: str = "redis://localhost:6379/0"
    RELEASE_ROOT: Path = PROJECT_ROOT / "data" / "releases"
    REFERENCE_ROOT: Path = PROJECT_ROOT / "data" / "references"
    MODELING_ROOT: Path = PROJECT_ROOT / "modeling"
    ADMIN_TOKEN: str = ""
    SESSION_SECRET: str = ""
    COOKIE_SECURE: bool = False
    ENABLE_DEMO_DATA: bool = False
    BLENDER_BINARY: str = "blender"
    BUILD_TIMEOUT_SECONDS: int = 7200
    RENDER_SAMPLES: int = 128
    SOURCE_MAX_BYTES: int = 15_000_000
    SOURCE_TIMEOUT_SECONDS: int = 30
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
