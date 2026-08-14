# Data privacy (production guidance)

This demo uses anonymised Telco benchmark data. In a real deployment:

## Customer identifiers

- **Hash or tokenise** customer IDs at ingestion (e.g., HMAC with rotating salt); never store raw IDs in model features or application logs.
- Separate **identity vault** from analytics warehouse; join only via ephemeral tokens for authorised workflows.

## PII in logs

- Structured logs record **request metadata only** (endpoint, latency, row counts) — not billing amounts, names, or full payloads.
- Batch upload filenames are logged; file contents are processed in memory and not persisted by default.

## Data at rest & in transit

- TLS for all API and UI traffic.
- Encrypt model artifacts and training snapshots at rest (S3 SSE-KMS or equivalent).

## Retention & deletion

- Prediction audit logs: 90-day retention default; cascade delete on GDPR erasure requests.
- Feature store rows keyed by tokenised ID with deletion hooks.

## Access control

- Role-based access (Clerk / SSO) for UI; scoped API keys for batch integrations.
- Admin routes (`/retrain`, `/logs`) protected with separate credentials.

## Model outputs

- SHAP and natural-language explanations describe **model attribution**, not causal effects — do not use as sole basis for regulated decisions without human review.
