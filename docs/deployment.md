# Deployment and operations

The starting point is FastAPI with Neon PostgreSQL and persistent image storage. PostgreSQL stores accounts, sessions, JSONB detections, inspection metadata and audit events; image files remain in the configured data directory. The compiled React UI can be served by FastAPI. Python/PyTorch inference needs a conventional server or container; a static frontend host cannot run it.

## Configuration

Use `.env` locally and environment variables in a container.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Server-only Neon PostgreSQL pooled connection string with TLS; required. |
| `PCB_DATA_DIR` | Persistent image directory; default `./data`. |
| `PCB_MODEL_PATH` | Trusted `best.pt`; default `./models/best.pt`. |
| `PCB_MODEL_MANIFEST` | Matching manifest; default `./models/model-manifest.json`. |
| `PCB_IMAGE_SIZE` | Input resolution; default 1024, matching the notebook. |
| `PCB_DEVICE` | `cpu`, `mps`, or CUDA device `0`; install the host's matching PyTorch build. |
| `PCB_SECURE_COOKIES` | Set `true` behind production HTTPS. |
| `PCB_ALLOWED_ORIGINS` | Comma-separated exact browser origins permitted to write; set the HTTPS domain. |

Keep frontend and API on the same HTTPS origin. Mutations require `X-PCB-Request: 1`; do not enable permissive CORS. Configure proxy upload limits around 21 MB and inference-appropriate timeouts. Configure trusted proxies deliberately so login throttling sees the correct client identity; do not trust arbitrary forwarded-IP headers.

## Containers

Set the actual Neon `DATABASE_URL` in `.env` before running Compose. The application container requires that variable and does not start a separate application database.

```bash
docker compose up --build
docker compose exec app /app/.venv/bin/python -m backend.manage create-admin --email you@example.com
```

Open http://localhost:8000. The default image starts without heavy inference dependencies. To enable CPU inference:

```bash
docker compose build --build-arg INSTALL_INFERENCE=true
docker compose up -d
```

Place trained artifacts in `models/`. Compose mounts that directory read-only and persists application data in a named volume. The image runs as an unprivileged user. Container builds and GPU inference require verification on the deployment host.

For public hosting, add an HTTPS reverse proxy and set `PCB_SECURE_COOKIES=true` and `PCB_ALLOWED_ORIGINS=https://your-domain.example`. The local HTTP configuration is not a public deployment configuration.

## Storage and backups

Never expose `data/` as static files. Image routes verify active sessions and ownership or administrator access. The upload UI discloses admin visibility. Password/session hashes never appear in admin responses.

Use Neon backups/restore facilities and take periodic PostgreSQL logical backups with `pg_dump`. Back up the image directory and trusted model artifacts separately. Coordinate snapshots of records and images, verify restores, and restrict access to service and backup accounts. Do not store the database URL in logs or frontend build variables.

The weights checksum detects accidental mismatches; it does not authenticate a publisher if both manifest and weights were replaced. Install only trusted training exports and restrict artifact write access.

## Before public production use

- Add verified email, password recovery and any required MFA using an explicitly selected provider.
- Decide retention, deletion/export and storage quotas.
- Add monitoring, capacity controls and external rate limiting. The current audit log covers successful sign-ins, registration, access changes and saved inspections, not every security event.
- Move inference to a bounded job queue when usage exceeds a small single-instance workload. Model calls are serialized per process; additional workers duplicate model memory.
- PostgreSQL migrations in `backend/migrations/` are versioned and checksummed. Add a new migration for schema changes; never edit a migration already applied. Startup and `backend.manage migrate` apply pending files under a transaction-level advisory lock.
- Move images to authenticated shared object storage before deploying multiple instances. Local image storage is suitable for a persistent single-host deployment.
- Validate the model on actual boards, camera conditions and confirmed healthy images before quality decisions.

Email recovery, email verification, MFA, organization tenancy, background jobs and automatic model uploads are not included.

## Neon connection behavior

Use the pooled URL from Neon, preserve TLS parameters and percent-encode special characters in credentials if constructing a URL manually. Psycopg uses a bounded application connection pool, checks connections before reuse, and disables protocol-level prepared statements for compatibility with transaction pooling. Schema selection and migration locks are transaction-local. No session-wide database settings are assumed.

Use `uv run python -m backend.manage check-db` to verify connectivity and `uv run python -m backend.manage migrate` to apply migrations. Missing `DATABASE_URL` stops startup with a configuration error. No live Neon connection is claimed until verified against the supplied URL.

## Test isolation

`TEST_DATABASE_URL` is separate from application credentials. `compose.test.yaml` provides PostgreSQL 17 for local tests; `.env.test.example` supplies its disposable credentials. Each API test and browser-server run creates its own random PostgreSQL schema and drops that schema afterward. Never point the test variable at production. Browser fixture endpoints exist only in `tests/browser_server.py`.
