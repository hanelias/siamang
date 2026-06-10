# Cloud Quick Start

Run the full siamang Cloud stack locally with Docker: Postgres, Redis, Gitea,
MinIO, the API, a worker, the nginx survey host, and the Next.js web app. There
is also a zero-services "mock mode" if you only want to click through the web UI.

## Prerequisites

- Docker with Compose v2 (`docker compose`).
- The `siamang_cloud` repository checked out locally.
- For mock mode only: Node.js (to run the web dev server).

## Run the full stack

```bash
cp .env.example .env
docker compose up --build
```

The first build provisions Postgres, runs migrations, brings up Gitea and MinIO,
and starts the API, worker, nginx, and web containers.

### Service URLs

All ports are bound to `127.0.0.1` by the local compose file:

| Service | URL | Notes |
| :--- | :--- | :--- |
| API | http://localhost:8000 | FastAPI platform API |
| Web | http://localhost:3001 | Next.js product UI |
| Gitea | http://localhost:3000 | Git hosting (repos, push webhooks) |
| MinIO console | http://localhost:9001 | Object-storage console (S3 API on :9000) |
| Surveys | http://localhost:8080 | nginx static host for deployed surveys |

### Health check

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

`GET /health` is a liveness probe (200 when the API process is up). For a
readiness probe that also checks Postgres and Redis, use `GET /health/ready`,
which returns `200` with `{"status": "ok", "checks": {...}}` only when both
dependencies are reachable, and `503` (`"degraded"`) otherwise.

## Configure secrets before going client-facing

The API **refuses to start** (its `assert_secure_config` check) if the dev `auth`
provider is selected and the security-critical values are left at their defaults.
Every value marked `CHANGE ME` in `.env.example` must be replaced for a
client-facing deploy. The most important ones:

| Variable | Why | How to generate |
| :--- | :--- | :--- |
| `JWT_SECRET` | Signs platform JWTs (must be >= 32 chars and not the dev default) | `openssl rand -hex 32` |
| `FERNET_KEY` | Encrypts stored Git tokens and project secrets | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GIT_WEBHOOK_SECRET` | Validates Gitea push webhooks (must be non-default) | `openssl rand -hex 32` |
| `SANDBOX_DB_SECRET` | Derives per-project Postgres role passwords for analysis | `openssl rand -hex 32` |
| `GITEA_ADMIN_TOKEN` | Lets the API drive Gitea | minted automatically by `scripts/dev_up.sh` |

Other notable settings include `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY` /
`MINIO_SECRET_KEY`, and the public URLs (`INGEST_BASE_URL`, `SURVEYS_BASE_URL`,
`WEB_BASE_URL`). See [[Cloud Configuration|Cloud-Configuration]] for the complete
list.

## One-shot dev bring-up

For local development or GitHub Codespaces there is a re-runnable bootstrap
script that brings up infra, runs migrations, mints a Gitea admin token, creates
the MinIO bucket, builds the sandbox image, and starts the API, worker, and
nginx:

```bash
bash scripts/dev_up.sh
```

It fills in any still-default secrets in `.env`, sets `NEXT_PUBLIC_USE_MOCK=false`
so the web UI talks to the live API, and waits for `GET /health` to go green
before finishing (printing the container status and next-step hints).

## Web mock mode (no services)

The entire product is clickable on fixtures — no Postgres, Gitea, Redis, Docker,
or MinIO required. This is the fastest way to explore the UI:

```bash
cd web
npm install
NEXT_PUBLIC_USE_MOCK=true npm run dev    # http://localhost:3000 (next dev default)
```

Every screen works against `web/lib/mock.ts` fixtures (Repository, Database,
Deployments, Analysis, Dashboard, Files, Team, Settings). All screens go through
the `web/lib/platform.ts` adapter, which switches to the live API when
`NEXT_PUBLIC_USE_MOCK=false`. Point the live build at the API with
`NEXT_PUBLIC_API_BASE_URL` (and `NEXT_PUBLIC_AUTH_MODE=dev` for the dev JWT auth
flow). Note that `NEXT_PUBLIC_*` values are inlined at build time.

## First steps after it is up

1. Register a user and obtain a token — see [[Cloud Authentication|Cloud-Authentication]].
2. Create an organization and a project (which provisions a Git repo + a Postgres
   schema + a skeleton commit + a push webhook).
3. Edit the questionnaire, push, and watch validation; then deploy and collect
   responses. See [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]].

## See also

[[Cloud Overview|Cloud-Overview]] · [[Cloud Architecture|Cloud-Architecture]] · [[Cloud Configuration|Cloud-Configuration]] · [[Cloud Authentication|Cloud-Authentication]] · [[Cloud REST API|Cloud-REST-API]]
