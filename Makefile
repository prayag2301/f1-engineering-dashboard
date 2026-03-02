.PHONY: bootstrap test lint build backfill docker-up docker-down workers clean

# Local development
bootstrap:
	./scripts/bootstrap_local.sh

test: test-api

test-api:
	cd apps/api && python -m pytest -v

lint:
	npm -ws --if-present run lint

typecheck:
	npm -ws --if-present run typecheck

build:
	npm -w @f1/web run build

# Docker
docker-up:
	docker compose up -d

docker-down:
	docker compose down

workers:
	docker compose --profile workers up -d

# Pipeline
backfill:
	@if [ -z "$(SEASON)" ] || [ -z "$(RACE)" ]; then \
		echo "Usage: make backfill SEASON=2026 RACE=R05"; \
		exit 1; \
	fi
	./scripts/backfill_weekend.sh $(SEASON) $(RACE)

# Validation
validate-schemas:
	./scripts/validate_schemas.sh

# Cleanup
clean:
	docker compose down -v
	rm -rf apps/web/node_modules apps/web/.next
	rm -rf services/*/node_modules services/*/dist
	rm -rf packages/*/node_modules packages/*/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
