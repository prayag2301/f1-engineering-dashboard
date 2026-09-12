.PHONY: bootstrap test test-api typecheck build docker-up docker-down collect jobs
bootstrap:
	./scripts/bootstrap_local.sh
test: test-api typecheck
test-api:
	cd backend && .venv/bin/python -m pytest
typecheck:
	npm --prefix frontend run typecheck
build:
	docker compose build
docker-up:
	docker compose up -d --build
docker-down:
	docker compose down
collect:
	docker compose exec -T api python -m app.cli collect
jobs:
	docker compose exec -T api python -m app.cli jobs
