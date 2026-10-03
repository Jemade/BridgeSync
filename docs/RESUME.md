# Resume and interview evidence

## Project entry

Repository: [github.com/Jemade/BridgeSync](https://github.com/Jemade/BridgeSync)

**BridgeSync | Python, FastAPI, PostgreSQL, React/TypeScript, Celery, Redis, Docker**

- Built an organisation-scoped order integration and payment reconciliation application with role-based access and an operational dashboard.
- Implemented transactional order/job persistence, database-enforced duplicate protection, worker leases, bounded retries and an idempotent HTTP test destination.
- Added exact payment matching, atomic CSV validation, revocable integration keys, audit history and automated correctness/security tests.

## Interview topics this repository supports

Explain why the outbox is durable, why dispatch may repeat, how concurrent claims are controlled, and why the destination must deduplicate requests. Discuss transactions, security boundaries, authentication versus authorisation, decimal accounting, failed-job recovery, CSV validation and the limits of independent payment matching.

Show a test rather than only stating a claim. Explain a failed test you investigated, the cause, the implementation fix and the regression check. State which parts are framework behaviour and which business rules were implemented here.
