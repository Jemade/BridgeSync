# Validation record

Checked on 3 October 2026. Results below describe the actual initial implementation, not assumed production behaviour.

| Check | Result |
| --- | --- |
| Python backend suite | 20 tests passed on SQLite locally and in GitHub Actions; 20 tests passed on PostgreSQL 17 in GitHub Actions |
| Browser workflow: sign-in, order, delivery, CSV import, sign-out | Passed locally and in GitHub Actions against the running API, worker and HTTP receiver |
| Browser workflow: mobile width, navigation and Escape | Passed locally and in GitHub Actions at 390 x 844 |
| Browser workflow: rejection and manual recovery | Passed locally and in GitHub Actions against the live test connector |
| Browser runtime errors during screenshot capture | None observed |
| TypeScript checks and production frontend build | Passed |
| Ruff checks | Passed |
| Initial Alembic migration against a clean SQLite database | Passed; no pending schema changes detected |
| PostgreSQL initial migration | Passed in GitHub Actions; no pending schema changes detected |
| Compose YAML | Parsed; six services configured |

Published source verification: all 61 initial repository files matched the tested local Git blob hashes. [Initial GitHub Actions run](https://github.com/Jemade/BridgeSync/actions/runs/37148637727).

## Important test coverage

Concurrent identical submissions create one order and one job. Reused identifiers with conflicting data fail. Acceptance rolls back its order and job together. Concurrent duplicate worker tasks result in one claimed delivery. Temporary failures retry with a delay; permanent failures and exhausted attempts require manual recovery. Expired leases can recover. Broker failure does not remove durable work.

Tests also exercise tenant isolation, viewer restrictions, disabled-session revocation, integration-key scope/revocation, browser mutation guards, sign-in throttling, CSV validation, conflicting-payment rollback, exact currency matching, pagination and large monetary values. The persistent test receiver deduplicates repeated delivery and rejects changed content under the same key.

## Regression caught during implementation

SQLite's legacy transaction behaviour allowed a released savepoint to persist an earlier payment row despite a later import conflict. Explicit transaction management fixed the issue. The regression test verifies that the entire conflicting import rolls back.

## Not yet verified in this environment

- Docker image build and the full PostgreSQL/Redis/Celery Compose stack: Docker was unavailable.
- Real commercial business-system connectors, third-party API credentials, production load, email delivery or public deployment.
- Independent security audit, full accessibility audit and broader browser/device coverage.

The browser tests used the local SQLite polling worker, which calls the same claim/delivery function used by Celery. Mock-transport unit tests supplement the live HTTP receiver tests. None of these results imply a production SLA or exactly-once delivery to arbitrary systems.

## Render startup verification

Checked on 3 October 2026: 25 backend tests passed locally on SQLite, including PostgreSQL URL normalization, provider port binding, child-process cleanup after component failure, and graceful platform shutdown. Ruff checks passed. All three browser workflows passed using `python -m app.hosted`; restarting the service retained the account without duplicate seeding.

The hosted startup was checked locally. A live Render deployment is not claimed by these results. The Blueprint requires a dedicated PostgreSQL connection and initial account credentials.
