# Deploy BridgeSync to Render

The repository includes a Docker web-service Blueprint in `render.yaml`.

[Deploy to Render](https://render.com/deploy?repo=https://github.com/Jemade/BridgeSync)

## Deployment inputs

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URL for a dedicated BridgeSync database |
| `ADMIN_EMAIL` | Initial administrator email |
| `ADMIN_PASSWORD` | Unique password of at least 12 characters |

The Blueprint generates `CONNECTOR_TOKEN`, enables secure cookies, and starts `python -m app.hosted`. PostgreSQL URLs from Render are normalized to the installed psycopg driver. Do not share a database with AgentBench; their table names overlap.

The startup command runs migrations, creates the administrator and sample orders on the first start, then supervises the API, polling delivery worker, and loopback test receiver. Existing accounts are not overwritten. The API binds Render's `PORT`. A component exit stops the service so the platform can restart it.

## Storage and service plan

The Blueprint selects a free web service and prompts for an external database URL. It does not create a paid database or other paid resources automatically.

Use PostgreSQL for durable application records. Render free web services sleep after inactivity and have an ephemeral filesystem. The local test receiver stores deduplication records in `/data/connector.db`, which resets on redeploy or instance replacement without a persistent disk. This is appropriate for the demonstration connector; a commercial receiver must retain its own idempotency records.

For an always-on deployment, choose an appropriate paid web plan and database after reviewing Render's current pricing. A persistent disk mounted at `/data` can retain test-receiver records. The default Blueprint has no disk.

## Verify after deployment

1. Open `/api/health`, then sign in at the service URL.
2. Submit an order and confirm it changes from queued to delivered.
3. Switch the test connector to outage mode and inspect retry history.
4. Import the example payment CSV and inspect matches and exceptions.
5. Redeploy and confirm PostgreSQL retains application records.

The public service is an authenticated demo. Keep administrator credentials out of the repository. Use separate viewer accounts when sharing access.

## Reference

- [Render Docker services](https://render.com/docs/docker)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render free-service limits](https://render.com/docs/free)
- [Operations](OPERATIONS.md)

## Current hosted demo

Created on 3 October 2026 in My Workspace: https://bridgesync.onrender.com. The live service uses Render's native Python runtime; its build installs backend requirements and builds the React frontend. Its start command is `cd backend && python -m app.hosted`.

Both the interface and `/api/health` returned HTTP 200. PostgreSQL connection wiring is pending, so this deployment currently uses temporary SQLite storage. Stored application data can reset on instance replacement or redeployment. Administrator credentials are secret environment variables in the service settings, not repository files. Automatic deploys are disabled while database configuration is being completed.
