# API examples

API documentation: http://localhost:8000/docs. Protected workspace endpoints use the login cookie. Mutations require `X-BridgeSync-Request: browser`. The documented Swagger operations include this header. The Swagger UI loads its frontend assets from jsDelivr; the product workspace assets are served locally.

## Integration order submission

Create an integration key in Settings. Store it outside source control. In your shell, assign `BRIDGESYNC_API_KEY` without committing it, then:

```bash
curl http://localhost:8000/api/webhooks/orders \
  -H "Authorization: Bearer $BRIDGESYNC_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-1001","reference":"EXT-1001","customer":"Demo retailer","amount":"129.00","currency":"USD"}'
```

An accepted event returns HTTP 202 and `{ "id": "...", "duplicate": false }`. An identical repeat returns the same order ID with `duplicate: true`. A conflicting event or order reference returns HTTP 409. Revoked or missing keys return HTTP 401.

## Payment CSV

```csv
reference,order_reference,amount,currency
PAY-2001,ORD-1001,129.00,USD
PAY-2002,ORD-1002,300.00,USD
PAY-2003,ORD-9999,74.25,USD
```

The first row matches the seeded order. The second has an amount mismatch. The third references a nonexistent order. UTF-8 files up to 1 MB and 1000 rows are accepted. Empty files, malformed rows, invalid amounts, invalid headers and repeated references within one file are rejected with useful errors.

## Main routes

| Method | Route | Purpose |
| --- | --- | --- |
| POST | /api/auth/login | Create browser session |
| POST | /api/auth/logout | Revoke current session |
| GET | /api/me | Current member and organisation |
| GET | /api/overview | Actual counts and currency totals |
| GET / POST | /api/orders | Search or accept orders |
| POST | /api/webhooks/orders | API-key authenticated ingestion |
| GET | /api/jobs/{id} | Job state and attempt history |
| POST | /api/jobs/{id}/retry | Explicit failed-job recovery |
| GET | /api/payments | Imported payments |
| POST | /api/payments/import | CSV validation and reconciliation |
| POST | /api/payments/{id}/match | Exact manual order matching |
| GET / PUT | /api/connector | Test destination behaviour |
| GET | /api/audit | Tenant activity history |
| GET / POST / DELETE | /api/keys and /api/keys/{id} | Admin key management |
| GET / POST / DELETE | /api/members and /api/members/{id} | Admin access management |
| GET | /api/health | API/database liveness |
