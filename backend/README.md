# Canonical API and workers

This directory contains the only backend implementation. See [the root README](../README.md) for the Docker workflow, migration and publication rules.

Install development dependencies with `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'`. Run `.venv/bin/python -m pytest` here. Unit tests use isolated SQLite state; Docker smoke tests exercise PostgreSQL migrations and native Blender.

`app.bootstrap` is the one-shot migration service. API startup does not mutate the database. `app.tasks` owns durable jobs; the scheduler consumes its own queue so rendering cannot block recovery. Legacy records and endpoints remain maintainer-only.
