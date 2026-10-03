# BridgeSync

[![Verify BridgeSync](https://github.com/Jemade/BridgeSync/actions/workflows/ci.yml/badge.svg)](https://github.com/Jemade/BridgeSync/actions/workflows/ci.yml)

Order delivery and payment reconciliation for business operations teams.

BridgeSync accepts an order, saves its durable delivery job in the same transaction, delivers it to a business-system connector, and makes failures inspectable. Payment CSVs are compared against order references, amounts and currencies. The dashboard displays current order, delivery, and reconciliation records.

![BridgeSync workspace](docs/screenshots/overview.png)

## Why this project exists

An order should not disappear because a message broker is unavailable. Repeated events should not create repeated business actions. A failed delivery should leave enough history for an operator to understand and recover it. BridgeSync makes those behaviours visible and testable.

## Features

- Python/FastAPI backend and React/TypeScript frontend.
- Organisation-scoped workspaces with administrator, operator and viewer roles.
- Password hashing, expiring server-side sessions, sign-in throttling and revocable integration keys.
- Transactional order acceptance and a durable job outbox.
- Database-enforced event and order uniqueness; conflicting duplicates return HTTP 409.
- Atomic worker leases, bounded retries, terminal failures, manual recovery and delivery-attempt history.
- A persistent HTTP test receiver with idempotency keys and deliberate outage/rejection modes.
- CSV payment import with exact integer-cent accounting, duplicate detection and explicit exceptions.
- Controlled manual matching, tenant-scoped audit records, search and pagination.
- Docker Compose configuration for PostgreSQL, Redis, API, worker, scheduler and connector.
- Database migrations, API documentation, automated backend and browser tests.

## Integration scope

The included connector is a test receiver with a documented HTTP contract, idempotency support, and controllable failure modes. Commercial platform adapters are separate extensions. Payment matching currently handles independent full-amount settlements.

Screenshots show actual local execution with seeded demonstration data. The failure controls are available only for the test connector. See [validation](docs/VALIDATION.md) for what was actually verified and what remains to be verified.

## Deploy to Render

[Deploy to Render](https://render.com/deploy?repo=https://github.com/Jemade/BridgeSync)

The Blueprint starts the interface, API, and demonstration worker. Supply a dedicated PostgreSQL database URL and initial account credentials. See [Render deployment](docs/RENDER.md) for startup, persistence, service-plan limits, and verification.

## Run with Docker Compose

Requirements: Git, Docker Engine/Desktop and Docker Compose v2. From the repository root:

```bash
cp .env.example .env
```

Edit `.env` first. Replace both service secrets and the administrator credentials. Use a URL-safe PostgreSQL password (for example, a random hexadecimal string) because it forms part of the database URL.

For Bash, load only your own trusted environment file, then start and seed the workspace:

```bash
set -a
. ./.env
set +a
docker compose up --build -d
docker compose exec -e ADMIN_EMAIL -e ADMIN_PASSWORD api python -m app.seed --demo
```

Open **http://localhost:8000** and sign in using the administrator credentials you set. The API reference is at `/docs`. The application only binds to localhost by default. Seeding is explicit and never overwrites existing accounts. Omit `--demo` for an empty workspace.

Useful commands:

```bash
docker compose logs -f api worker scheduler
docker compose ps
docker compose down
```

`docker compose down` preserves database volumes. Do not use `down -v` unless you deliberately intend to delete stored data.

## Local development without Docker

Requirements: Python 3.12 and Node.js 24. SQLite is the local-development default; Compose uses PostgreSQL.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd frontend
npm ci
npm run build
cd ../backend
alembic upgrade head
```

Set `ADMIN_EMAIL` and a unique `ADMIN_PASSWORD` of at least 12 characters, then:

```bash
python -m app.seed --demo
```

In three terminals, activate the environment, enter `backend`, and set the **same** `CONNECTOR_TOKEN` value in each terminal:

```bash
uvicorn app.main:app --port 8000
```

```bash
uvicorn app.mock_connector:app --port 8001
```

```bash
python -m app.worker
```

The local polling worker uses the same claim and delivery code as Celery. For frontend development, run `npm run dev` from `frontend`; Vite proxies API requests to port 8000. Rebuild the frontend after UI edits when using the Python-served interface.

## Test

From `backend`, with the environment active:

```bash
pytest -q
ruff check app tests migrations
```

The tests create and clear an isolated test schema. **Never point TEST_DATABASE_URL at a production database.** For PostgreSQL:

```bash
TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/bridgesync_test pytest -q
```

From `frontend`:

```bash
npm ci
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests require the running API, connector and local worker. Set the test administrator's `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the test shell. The workflow under `.github/workflows` starts these services in CI and runs both SQLite and PostgreSQL test jobs.

## Documentation

- [Architecture and delivery guarantees](docs/ARCHITECTURE.md)
- [Three-minute demonstration](docs/DEMO.md)
- [API examples](docs/API.md)
- [Deployment and recovery](docs/OPERATIONS.md)
- [Verified results and limits](docs/VALIDATION.md)
- [Resume and interview evidence](docs/RESUME.md)
- [Interface decisions](docs/DESIGN.md)

## Repository layout

```text
backend/
  app/          API, security, schema, services, worker and test connector
  migrations/   Versioned schema changes
  tests/        Business correctness and security tests
frontend/
  src/          React/TypeScript interface and API client
  public/       SVG identity and example payment CSV
  tests/        Browser workflows
  package-lock.json
.github/workflows/ci.yml
docs/
Dockerfile
compose.yaml
```

## Next practical extensions

A commercial-system adapter; password reset and self-service credential rotation; email invitations; queue/worker readiness monitoring; accounting for partial and multi-payment settlements; timestamp-signed webhook support where required; and production load testing. These are tracked product extensions, not features represented as already implemented.

## License

MIT. See [LICENSE](LICENSE).
