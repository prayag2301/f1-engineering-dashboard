import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make the backend package importable (adds /app/ or apps/api/ to sys.path)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from app.database import Base  # local dev (package name: app)
    import app.models.models  # noqa: F401
except ModuleNotFoundError:
    from backend.database import Base  # Docker (package name: backend)
    import backend.models.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """
    Resolve DATABASE_URL in priority order:
      1. DATABASE_URL env var
      2. app/backend Settings default
    For local dev outside Docker, export:
      DATABASE_URL=postgresql://f1user:f1pass@localhost:5432/f1dashboard
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        from app.config import get_settings
        return get_settings().DATABASE_URL
    except Exception:
        pass
    try:
        from backend.config import get_settings
        return get_settings().DATABASE_URL
    except Exception:
        pass
    return "postgresql://f1user:f1pass@localhost:5432/f1dashboard"


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
