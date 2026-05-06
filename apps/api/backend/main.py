from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.database import engine
from backend.api.routes import router as api_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="The most technically insightful open-source F1 engineering platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.on_event("startup")
    async def on_startup():
        from pathlib import Path
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import inspect, text

        backend_dir = Path(__file__).resolve().parent
        alembic_cfg = Config(str(backend_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        # If tables already exist (from old create_all) but no alembic_version row,
        # stamp to head so Alembic skips the initial migration instead of failing.
        with engine.connect() as conn:
            table_names = inspect(conn).get_table_names()
            has_tables = "teams" in table_names
            has_version = "alembic_version" in table_names
            if has_tables and not has_version:
                command.stamp(alembic_cfg, "head")
                return

        command.upgrade(alembic_cfg, "head")

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_app()
