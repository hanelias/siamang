# Cloud CI/CD and Testing

siamang Cloud is tested by a GitHub Actions workflow (`.github/workflows/ci.yml`)
that lints, type-checks, and unit-tests every component, applies and rolls back
the database migrations, type-checks and builds the web app, runs a Playwright
smoke test in mock mode, brings up the full stack and runs a strict end-to-end
smoke against it, and builds the Docker images. This page lists the CI jobs and
shows how to run each check locally.

---

## CI jobs

CI runs on every push (`branches: ["**"]`) and on pull requests.

| Job | What it does |
| :--- | :--- |
| **python** | Installs `api`/`worker` dev deps + the engine (from `siamang-main.zip`); runs `ruff check`, `ruff format --check`, `mypy api/app`, `mypy worker/app`, `pytest` for `api` and `worker` (each with `PYTHONPATH=.`); plus a non-blocking `pip-audit`. |
| **migrations** | Spins up a `postgres:15.8` service and runs `alembic upgrade head` then `alembic downgrade base`, proving migrations apply and roll back cleanly. |
| **engine** | Installs the engine + the `siamang_cloud_engine` plugin; runs `mypy` and `pytest` on the plugin (no live services). |
| **sdk** | Installs the engine + SDK deps; runs `pytest` on the `sdk` package (no live services). |
| **web** | `npm ci`, a non-blocking `npm audit --omit=dev`, then `npm run build` (Next.js build also type-checks and lints). |
| **web-e2e** | `npm ci`, installs the Playwright Chromium browser, runs `npm run e2e` (the mock-mode smoke spec); uploads traces on failure. |
| **live-e2e** | Brings up the full stack with `scripts/dev_up.sh`, then runs `scripts/e2e_smoke.sh` (strict); dumps `api`/`worker`/`gitea` logs on failure. 25-minute timeout. |
| **docker** | Copies `.env.example` → `.env`, validates `docker compose config`, and builds the `api` and `worker` images. |

The engine and the api suite are installed from the bundled `siamang-main.zip`
archive (siamang is not published to a public index), mirroring the sandbox image.

---

## Running checks locally

### Python (lint, types, tests)

The api and worker test suites need `PYTHONPATH` pointed at the component root
(matching CI, which sets `working-directory` + `PYTHONPATH: .`):

```bash
# from the repo root
pip install -r api/requirements-dev.txt -r worker/requirements-dev.txt

ruff check .
ruff format --check .
mypy api/app
mypy worker/app

PYTHONPATH=api    pytest api/tests
PYTHONPATH=worker pytest worker/tests
```

The engine plugin and the SDK are tested from their own directories:

```bash
cd siamang_cloud_engine && pytest tests
cd sdk && pytest
```

The consolidated gate used during development is:

```bash
ruff check . && ruff format --check . && mypy api/app && \
  PYTHONPATH=api pytest api/tests && PYTHONPATH=worker pytest worker/tests
```

### Migrations

```bash
cd db
PLATFORM_PG_DSN=postgresql://siamang:siamang@localhost:5432/siamang alembic upgrade head
PLATFORM_PG_DSN=postgresql://siamang:siamang@localhost:5432/siamang alembic downgrade base
```

### Web

```bash
cd web
npm ci
npm run lint
npm run build      # type-checks + lints + builds
npm run e2e        # Playwright smoke (mock mode); needs: npx playwright install chromium
```

---

## The end-to-end smoke script

`scripts/e2e_smoke.sh` is the strict, live-stack gate (run **after**
`scripts/dev_up.sh`, which generates secrets, starts
postgres/redis/gitea/minio, runs migrations, mints a Gitea admin token, creates
the MinIO bucket, builds the sandbox image, and starts api + worker + nginx).

It exercises the whole critical path against the running API and asserts each
expectation via a `check()` helper, exiting non-zero if any fails (so it doubles
as the `live-e2e` CI gate). It deliberately does **not** `set -e`, so a failing
step still prints diagnostics. The flow:

- register → token → create org → upgrade plan to `pro`;
- create a project (Gitea repo + skeleton + `project_<id>` schema + webhook);
- commit to `survey/questionnaire.py` → poll `commit_status` until validation
  settles (`valid`/`warnings`);
- deploy the survey → poll until `live`, confirm nginx serves the bundle
  (HTTP 200);
- ingest responses → confirm rows are visible in the project schema;
- run the `cleaning` script and `run-all` → poll runs to `completed`, list reports;
- data export (CSV + a real SQLite snapshot), deployment monitoring
  (stats/quotas/codebook), an API key authenticating `/auth/me`, GDPR response
  delete → audit, schedule creation, project secret + Git mirror, connectors
  listing, survey preview, the ingest rate-limit (expect a 429 under a burst);
- negative paths (unknown `survey_id` → 404; broken `siamang.yaml` → 422) and the
  seeded **example** template (creates a working study with sample data,
  dashboard aggregates, and `cleaning,tables,weights` scripts);
- webhook delivery journal.

It prints `SMOKE: OK` and exits 0 when every `check()` passed, otherwise
`SMOKE: N FAILURE(S)` and exits 1.

## See also

[[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]] · [[Cloud Web App|Cloud-Web-App]] · [[Cloud Contributing|Cloud-Contributing]]
