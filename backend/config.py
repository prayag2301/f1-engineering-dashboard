from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "F1 Engineering Dashboard"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql://f1user:f1pass@db:5432/f1dashboard"
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
