# Cloud Roadmap

siamang Cloud was built as a sequence of **vertical slices** — each stage delivers
a working end-to-end capability rather than a horizontal layer. This page
summarizes that staged delivery plan (Stages 0–6), the feature-pass that polished
the product to a commercial shape, and the Beta-2 hardening pass. It is a
high-level roadmap; the canonical detail lives in `DEVELOPMENT_PLAN.md`,
`FEATURE_PASS.md`, and `BETA2_ROADMAP.md`.

---

## Planning principles

- **Defer external-service integration to the end.** First build and fully
  unit-test all the "pure" logic that needs no live services or keys (Postgres,
  Gitea, Redis, Docker, MinIO, Stripe, cloud infra). Anything needing a live
  connection is hidden behind a thin seam (a function/interface) and wired in a
  final **Service Integration** stage, so the pure side stays testable with mocks.
- **Vertical slices, not horizontal layers.** Each stage is a working slice from
  API to result, so value can be checked at every step.
- **Security from day one.** The sandbox for untrusted code and RLS isolation are
  laid down in Stage 1, not bolted on later — reworking them later is more
  expensive and dangerous.
- **Tenant-aware from the start.** `org_id` on every table and RLS enabled
  immediately, even with a single first customer — the on/off switch for SaaS vs.
  self-hosted.
- **MVP = end of Stage 2.** Everything up to the UI is verifiable with
  `httpie`/`curl`; the UI (Stage 3) is a wrapper over an already-working API.
- Each stage has a checkable **Definition of Done**, not "looks done".

---

## Stages 0–6

| Stage | Name | Result | Demonstrated value |
| :--- | :--- | :--- | :--- |
| 0 | **Foundation** | Repo, infra, CI, service skeletons | `docker compose up` brings up an empty stack |
| 1 | **Core API + Git + Validation** | A project = a Git repo + a DB schema; push → auto-validation | "survey code is versioned and checked" |
| 2 | **Deploy + Ingest (MVP)** | A survey deploys to our domain and collects responses | "the survey works, data accumulates" |
| 3 | **Web UI** | All of stages 1–2 through the browser | "the product can be shown to a non-developer" |
| 4 | **SDK + Analysis + Reports** | Analysis scripts over the data → report artifacts | "the researcher gets a finished report" |
| 5 | **SaaS hardening + Self-hosted** | Billing, limits, audit; a self-hosted build | "it can be sold" |
| 6 | **Scaling** | Survey hosting to R2, managed services | "it withstands growth" |

### Stage 0 — Foundation

Monorepo structure (`api/`, `worker/`, `siamang_cloud_engine/`, `sdk/`, `sandbox/`,
`survey_host/`, `web/`, `db/migrations/`); `docker-compose.yml` with every service
(stubbed); baseline CI (ruff/mypy/pytest/image builds); server provisioning
(Coolify on a VPS, Cloudflare DNS); a complete `.env.example`. **DoD:**
`docker compose up` brings everything up green, `git push` autodeploys via Coolify,
`/health` returns 200, CI is green.

### Stage 1 — Core API + Git + Validation

Migration `001_initial` (all `public.*` tables + RLS); auth (`/auth/register`,
`/auth/token`, `/auth/me` — JWT, bcrypt, Gitea-mirrored user with a Fernet-encrypted
token); `git_service` (Gitea REST wrapper); `database_service`
(`create_project_schema`); orgs/projects CRUD with `require_role` and the RLS
context; project provisioning (Gitea repo → DB schema → skeleton commit → webhook);
the git webhook → validate enqueue; the **sandbox** validate worker (ephemeral,
no secrets, no network). **DoD includes** a security test (sandboxed code can't
read the platform DSN/secrets and has no network) and an RLS test (a second user
from another org gets 403 / empty results).

### Stage 2 — Deploy + Ingest (MVP)

The `siamang_cloud_engine` plugin (`PlatformBackend` + client template); the deploy
worker (compile-in-sandbox → provision → build-in-sandbox → write the bundle to the
surveys volume → update the deployment row); the deploy API
(`POST/GET /deployments`, SSE logs, stop); the public **Ingest API**
(`POST /ingest/{survey_id}/responses` + quota check, open CORS, rate limit,
`max_responses`) backed by `survey_registry`; the survey-host nginx; the database
read API. **DoD:** a survey reaches `live`, the bundle is served, responses ingest
and are visible, quotas are respected, and tenant isolation holds.

### Stage 3 — Web UI

Next.js shell (auth via httpOnly cookie, org switcher, sidebar); the org dashboard;
Repository (file tree + type-aware editor + commit-status badge + commits);
Database (tables, schema, preview, export); Deployments (status/URL/logs via SSE,
Deploy/Stop); Team/Settings. Project navigation is consolidated to **Repository ·
Database · Deployments · Analysis · Files · Settings** (Reports open in Repository
by file type; Scripts+Runs merged into Analysis). **DoD:** the whole MVP flow runs
by mouse, deploy logs stream live, validation badges update after a push.

### Stage 4 — SDK + Analysis + Reports

The `siamang_cloud` SDK (`db.table().to_pandas()`, `db.write_table()`,
`db.as_survey_data()` — narrow per-schema DSN); the engine `Report` document
submodule (fluent API + `Report.combine`); run workers (`run_script` / `run_all`
in the sandbox → `runs` + logs + outputs/reports in MinIO; MD/HTML render, PDF on
request); the analysis API; the **Analysis** UI + report rendering in Repository.
**DoD:** `cleaning.py` writes `clean_responses`; a `Report(...).save()` renders on
opening a `.md`; "Run all" assembles a combined `reports/report.md`; a security
test confirms a script sees only its own `project_<id>` schema.

### Stage 5 — SaaS hardening + Self-hosted

Stripe billing + plan limits; cap/quota enforcement at the API; audit log + rate
limiting + RLS review; a self-hosted build (single-tenant, RLS retained, license
key); observability (structured logs, Prometheus metrics, alerts).

### Stage 6 — Scaling

Survey hosting → Cloudflare R2 (decouples worker from nginx → horizontal scaling);
managed Postgres / object storage; sandbox → gVisor/Firecracker or Modal; multiple
worker nodes; data sharding by org if growth demands it.

### Dependencies

```text
Stage 0 ─┬─► Stage 1 ──► Stage 2 (MVP) ──► Stage 3 (UI)
         │                    │                 │
         │                    └─────────────────┴──► Stage 4 (SDK+Reports)
         │                                                  │
         └──────────────────────────────────────────► Stage 5 ──► Stage 6
```

What cannot be deferred (laid down early): the **sandbox** (Stage 1, or untrusted
code is a hole), **RLS + `org_id`** (Stage 1, retrofitting multi-tenancy is very
costly), and the shared `BackendConfig`/`survey_registry` contract (Stage 2, all of
ingest and deploy depend on it).

---

## Feature pass (commercial / UX polish)

An iteration over the working MVP (Stages 1–4) brought the GUI to a product shape
and closed functional gaps for two personas — the sociologist-analyst and the
programmer-researcher. Highlights, all implemented and tested:

- **Prototype completion on mocks** — every previously live-only feature (audit,
  API keys, webhooks, schedules, deploy monitoring, export, response deletion)
  routed through one adapter (`web/lib/platform.ts`) with fixtures, so the whole
  product is clickable with `NEXT_PUBLIC_USE_MOCK=true`.
- **SaaS tiering (W1+W2)** — the plan/limits engine (`limits.py`), Free caps, and a
  portable per-project SQLite snapshot export; migration `005_plan_limits`.
- **W3 + Git mirrors** — encrypted `project_secrets` and push/pull mirrors to
  GitHub/GitLab via Gitea; migration `006`.
- **Premium stubs (W7 billing · W5 AI · W6 SSO)** — all wired as stubs behind their
  feature gates (no real keys/services).
- **W4 connectors** — the catalog + declarative config + API + UI, *availability
  only* (no live transfer).
- **Analyst features** — curated package allowlist; data export (CSV/XLSX/SAV/
  Parquet); deploy monitoring (stats/quotas/codebook); audit log + GDPR delete.
- **Platform/dev** — personal API keys (`sck_…`); ingest rate-limiting; cron
  schedules; outgoing HMAC-signed webhooks. Migration `004_platform_features`.
- **Survey preview** before deploy; SDK `analysis`/`respondents` helpers;
  client-side **dashboards**.

---

## Beta-2 ("honest interface" + hardening)

Beta-2 closed most remaining bugs, stubs, and dead ends so every visible UI element
either works or is honestly labelled "Coming soon". Security was out of scope for
this pass (handled separately before beta-1). Status: **implemented**
(`v0.2.0-beta2`). Key decisions and themes:

- **AI assistant removed from the product** (panel gone from the UI; the backend
  router remains behind the off-by-default `FEATURE_AI`).
- **Billing / Connectors / SSO kept but honestly marked "Coming soon."**
- **Email not implemented** (invite codes remain; trial-expiry warning shows as a
  UI banner).
- **Dashboard moved to server-side aggregation + charts** (recharts).
- **Example Project** — a full demo study ("Work & Wellbeing") seeded to each user,
  exercising most of `siamang.core` and the whole SDK, with ~300 synthetic
  responses, deployable and analyzable.

The pass was organized in stages: (0) honest interface — remove stubs/dead ends;
(1) backend reliability — webhook delivery journal + retries (migration `012`), ARQ
timeouts/watchdog, deploy-failure handling, scheduler resilience, sandbox-timeout
messages, output caps, artifact TTL/cleanup, plan-downgrade reconciliation, trial
grace period; (2) server-side dashboard + charts; (3) frontend UX polish (unified
data hook, SSE polling fallback, skeleton/empty/error states, accessibility,
Repository/Database/Analysis refinements); (4) the Example Project + onboarding;
(5) quality (Playwright smoke in CI, observability, backup/restore, docs,
CHANGELOG + tag).

**Consciously out of beta-2:** Stripe live payments; the SSO login flow; connector
execution (S3/BQ/Sheets…); the AI assistant (removed); email/SMTP; i18n; PDF report
rendering; the self-hosted build.

## See also

[[Cloud Architecture|Cloud-Architecture]] · [[Cloud Subscription Tiers|Cloud-Subscription-Tiers]] · [[Cloud CI CD and Testing|Cloud-CI-CD-and-Testing]]
