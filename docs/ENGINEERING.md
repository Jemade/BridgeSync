# Engineering notes: BridgeSync

## Purpose and scope

Order delivery and payment reconciliation. This repository is an independently inspectable project; customer adoption, production scale and commercial readiness are not claimed without evidence.

## Request and data flow

Order/webhook input → validated organization-scoped order and outbox → worker delivery → reconciliation and audit.

## Implementation map

Primary implementation and review locations: `backend/app/main.py`, `backend/app/services.py`, `backend/app/worker.py`. Dependency manifests and `.github/workflows/` specify installation and automated checks. Read the source for exact contracts and data models.

## Local verification

From `backend` in a configured virtual environment:

```sh
pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

From the repository root, run `python scripts/repository_check.py` for documentation and tracked-file checks. CI evidence is available in [GitHub Actions](https://github.com/Jemade/BridgeSync/actions). Green hygiene checks alone do not mean application tests passed.

## Decisions and boundaries

Free hosted SQLite storage is temporary. A commercial-system adapter, persistent production database and load testing require separate deployment work.

Use the README's current run instructions and configuration examples. Keep provider credentials outside Git. Test changes against controlled fixtures before enabling external services. Health checks indicate process/service state, not end-to-end correctness.

## Review and operational evidence

[Review checklist](REVIEW_CHECKLIST.md) distinguishes repository evidence from outstanding human and deployment validation. Report measured workload, environment and method with any performance claim. Document incident fixes through reproducible issues and regression tests; do not invent user counts or peer reviews.

## Reuse and licensing

The root LICENSE describes the repository license. Third-party dependencies and assets retain their respective licenses.
