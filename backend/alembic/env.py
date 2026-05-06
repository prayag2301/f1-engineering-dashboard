import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make backend/app importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base  # noqa: E402

# Import all models so Alembic can see them in Base.metadata
import app.models.models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """
    Resolve DATABASE_URL in priority order:
      1. DATABASE_URL env var (set explicitly or via .env)
      2. app Settings default (points to Docker host 'db')
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
