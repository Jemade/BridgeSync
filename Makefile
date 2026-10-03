.PHONY: test build lint

test:
	cd backend && ../.venv/bin/pytest -q

lint:
	cd backend && ../.venv/bin/ruff check app tests migrations

build:
	cd frontend && npm ci && npm run build
