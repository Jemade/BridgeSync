# Deployment and recovery

## Before exposing the application

Use an HTTPS reverse proxy, set SECURE_COOKIE=true, replace every sample secret, and keep database/Redis/connector ports private. Review the application's business scope and access rules. There are no preinstalled login credentials. The seed command is explicit. Administrator passwords are not part of image builds.

The Compose listener binds to 127.0.0.1. Put your reverse proxy on the host, or configure private container networking deliberately. Do not expose a demonstration workspace with administrator credentials. Public showcases should use a separately isolated, read-only dataset or a recording.

The API health endpoint checks the database only; it is not proof that the worker, broker and destination are healthy. Monitor pending-job age, failed deliveries, dispatch errors, worker liveness, database health and backup age.

## Backup PostgreSQL

From the root, with the Compose stack running:

```bash
mkdir -p backups
docker compose exec -T db pg_dump -U bridge -d bridgesync -Fc > backups/bridgesync.dump
```

Protect backups, encrypt them at rest and keep copies outside the application host. Never commit backup files.

## Practise a restore

Use a separate test database, not the active production database:

```bash
docker compose exec db createdb -U bridge bridgesync_restore
docker compose exec -T db pg_restore -U bridge -d bridgesync_restore < backups/bridgesync.dump
docker compose exec db psql -U bridge -d bridgesync_restore -c 'SELECT COUNT(*) FROM orders;'
```

Compare expected record counts, organisation boundaries and recent transactions. Start a separately configured application instance against the restored database to verify authenticated reads before declaring recovery successful.

## Queue or worker interruption

Pending jobs remain in PostgreSQL when Redis is unavailable. Restore Redis and the scheduler; eligible jobs are dispatched again. Interrupted worker claims become eligible after their lease expires. The destination's idempotency key handles repeated deliveries. Inspect audit and attempt history after recovery.

## Upgrade and rollback

Back up the database. Build and test a tagged source version. Review migrations before `alembic upgrade head`; do not blindly downgrade a populated database. Keep the previous image available. Application rollback is safe only when its schema expectations remain compatible. The initial migration's downgrade deletes tables and is intended for disposable development schemas only.

## Secrets and permissions

Revoke exposed integration keys in Settings. Disable member access to invalidate their sessions. Rotate the deployment connector credential on both sender and receiver. This version does not implement self-service password reset; account recovery needs an administrator-controlled procedure. Do not reuse public test credentials.
