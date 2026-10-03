# Validation record

Checked on 3 October 2026. Results below describe the actual initial implementation, not assumed production behaviour.

| Check | Result |
| --- | --- |
| Python backend suite | 20 tests passed on SQLite |
| Browser workflow: sign-in, order, delivery, CSV import, sign-out | Passed against the running API, worker and HTTP receiver |
| Browser workflow: mobile width, navigation and Escape | Passed at 390 x 844 |
| Browser workflow: rejection and manual recovery | Passed against the live test connector |
| Browser runtime errors during screenshot capture | None observed |
| TypeScript checks and production frontend build | Passed |
| Ruff checks | Passed |
| Initial Alembic migration against a clean SQLite database | Passed; no pending schema changes detected |
| Compose YAML | Parsed; six services configured |

## Important test coverage

Concurrent identical submissions create one order and one job. Reused identifiers with conflicting data fail. Acceptance rolls back its order and job together. Concurrent duplicate worker tasks result in one claimed delivery. Temporary failures retry with a delay; permanent failures and exhausted attempts require manual recovery. Expired leases can recover. Broker failure does not remove durable work.

Tests also exercise tenant isolation, viewer restrictions, disabled-session revocation, integration-key scope/revocation, browser mutation guards, sign-in throttling, CSV validation, conflicting-payment rollback, exact currency matching, pagination and large monetary values. The persistent test receiver deduplicates repeated delivery and rejects changed content under the same key.

## Regression caught during implementation

SQLite's legacy transaction behaviour allowed a released savepoint to persist an earlier payment row despite a later import conflict. Explicit transaction management fixed the issue. The regression test verifies that the entire conflicting import rolls back.

## Not yet verified in this environment

- Docker image build and the full PostgreSQL/Redis/Celery Compose stack: Docker was unavailable.
- PostgreSQL runtime test results: a PostgreSQL process could not be started under the available process permissions. The committed GitHub Actions workflow includes PostgreSQL tests and migration verification, but has not run on GitHub yet.
- Real commercial business-system connectors, third-party API credentials, production load, email delivery or public deployment.
- Independent security audit, full accessibility audit and broader browser/device coverage.

The browser tests used the local SQLite polling worker, which calls the same claim/delivery function used by Celery. Mock-transport unit tests supplement the live HTTP receiver tests. None of these results imply a production SLA or exactly-once delivery to arbitrary systems.
