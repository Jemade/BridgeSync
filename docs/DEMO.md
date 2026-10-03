# Recruiter walkthrough

Use an explicitly seeded local workspace. Never publish real customer data or reusable private credentials in a recording.

## 0:00 - 0:30: business problem

Show Overview. Explain that lost delivery jobs, duplicate orders and unmatched payments are the problems. Metrics are generated from records in the current workspace.

## 0:30 - 1:10: successful order delivery

Open Orders, create a unique order reference and inspect its delivery. Show the pending state becoming Synced. Explain the database transaction and durable job row. Open the API reference to show the integration endpoint.

## 1:10 - 2:00: failure and recovery

Open Integrations and choose Permanent rejection. Create another order, inspect its failed attempt, then change the connector to Available. Retry from the order dialog and watch it become Synced. For automatic backoff, repeat using Temporary outage instead.

## 2:00 - 2:30: reconciliation

Import frontend/public/sample-payments.csv after demo seeding. Show the matched, amount-mismatch and unmatched rows. Repeat the same import to demonstrate duplicate skipping. Try an invalid row and show that nothing was imported.

## 2:30 - 3:00: engineering evidence

Show the architecture, tests and Git history. Explain tenant isolation, duplicate constraints, worker leases and at-least-once delivery. State that the destination is a test connector and mention the implementation limits honestly.

## Extra interview demonstration

Create a scoped integration key. Submit the same event twice; both responses refer to one order. Modify its amount and submit again; the API rejects it with HTTP 409. Revoke the key and demonstrate HTTP 401.
