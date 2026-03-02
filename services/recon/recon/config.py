import os


class Config:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    API_URL: str = os.getenv("API_URL", "http://localhost:8000/api/v1")
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "f1admin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "f1adminpass")
    OUTPUT_BUCKET: str = os.getenv("OUTPUT_BUCKET", "f1-reconstructions")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"


config = Config()
