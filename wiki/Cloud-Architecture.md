# Cloud Architecture

siamang Cloud is a monorepo of small services that wrap the `siamang` engine: a
FastAPI control plane, ARQ background workers, a Git server, object storage, a
static survey host, and a Next.js web app. This page covers the repository
layout, the layered model, the end-to-end data flow, multi-tenant isolation, and
the design principles behind it all.

## Monorepo layout

```
api/                  FastAPI platform API (auth, orgs/projects, deploy,
                      database, ingest, monitoring, billing, assistant, sso,
                      connectors, mirrors, secrets, schedules, webhooks)
worker/               ARQ background workers (validate, deploy, preview,
                      run_script, run_all, scheduler) + connector definitions
siamang_cloud_engine/ Engine plugin: PlatformBackend + PlatformClientTemplate
sdk/                  siamang_cloud SDK for analysis scripts (db, analysis,
                      respondents)
sandbox/              Ephemeral image for running untrusted user code
survey_host/          nginx config serving deployed survey bundles
web/                  Next.js frontend (runs on fixtures by default)
db/                   Alembic migrations
.github/workflows/    CI
docker-compose.yml    Full local stack (also deployed in production by Coolify)
```

The engine itself is vendored (as a pinned dependency in the sandbox image) and
consumed through its public extension points. The only sanctioned extension of
the engine is the `siamang.reporting.Report` document submodule.

## Components

```
                          ┌───────────────────────────┐
                          │       Web UI (Next.js)     │
                          │  Repository · Database ·   │
                          │  Deployments · Analysis ·  │
                          │  Files · Settings          │
                          └─────────────┬──────────────┘
                                        │ HTTPS (Bearer JWT)
                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          API (FastAPI)                                 │
│  auth · orgs · projects · repository · database · deployments · runs · │
│  files · ingest · webhooks · monitoring · billing · sso · ...          │
│  ── per-request tenant context (SET LOCAL app.current_org) ──          │
└───┬───────────┬───────────┬───────────┬───────────┬───────────┬───────┘
    │           │           │           │           │           │
    ▼           ▼           ▼           ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│Postgres│  │ Gitea  │  │ Redis  │  │ MinIO  │  │ nginx  │  │  ARQ     │
│platform│  │ (git)  │  │(queue) │  │ (S3)   │  │(surveys│  │ workers  │
│  + RLS │  │        │  │        │  │        │  │ static)│  │          │
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘  └────┬─────┘
                                                                 │ launches
                                                                 ▼
                                                  ┌───────────────────────────┐
                                                  │  Sandbox (ephemeral        │
                                                  │  docker container):        │
                                                  │  siamang + plugin,          │
                                                  │  no secrets, no egress      │
                                                  │  (analysis: DB-only net),   │
                                                  │  validate / deploy / run    │
                                                  └───────────────────────────┘
```

## The layered model

The product is organized as four user-facing layers, each backed by one or more
services:

| Layer | What it does | Backed by |
| :--- | :--- | :--- |
| **Repository** | Questionnaire and logic as versioned code; validation on push | Gitea + API (`projects`, `webhooks`) |
| **Deployments** | Build and publish a survey to a public URL | API (`deployments`) + deploy worker + sandbox + nginx |
| **Database** | Managed response storage, browsing, export, dashboards | Postgres (per-project schema) + API (`database`, `dashboard`, `monitoring`) |
| **Analysis** | Python analysis scripts, run history, schedules, reports | API (`analysis`, `schedules`) + run workers + sandbox + MinIO |

## End-to-end data flow

The whole loop is **Git push → validate → deploy → ingest → analyze → report**:

| Flow | Route |
| :--- | :--- |
| **Create project** | UI → API → Gitea (repo) + Postgres (`CREATE SCHEMA`) + Gitea (skeleton commit) + push webhook |
| **Push code (validate)** | Git client → Gitea → push webhook → API → ARQ enqueue → `validate` worker → sandbox → Postgres (`commit_status`) |
| **Deploy** | UI → API → ARQ enqueue → `deploy` worker → sandbox (build bundle) → nginx volume + Postgres (provision survey) |
| **Take survey (ingest)** | Respondent browser → nginx (static bundle) → public Ingest API → Postgres (`project_<id>.responses`) |
| **Analyze** | `run_script`/`run_all` → sandbox → SDK `db` → Postgres (`project_<id>.*`) → outputs/report → MinIO |

Two architectural decisions shape this flow:

- **Deployment is driven manually, not via `survey.deploy()`.** The engine's
  deploy pipeline uses a hard-coded client registry, so the platform replicates
  the pipeline in its deploy worker, substituting its own `PlatformBackend` and
  `PlatformClientTemplate`.
- **`PlatformClientTemplate` posts answers to the Ingest API.** A deployed survey
  is just static files on nginx with no backend of its own, so its `env.js` is
  rendered with an absolute CORS URL pointing at `/ingest/{survey_id}/responses`.

## Multi-tenant isolation

Isolation is enforced at two independent levels:

1. **Per-project Postgres schema.** Every project gets its own schema
   `project_<id>` holding `responses`, `survey_meta`, and `quota_counters` (plus
   any tables analysts create). Tenants never share response tables.
2. **Row-Level Security (RLS) on platform tables.** Every platform table with an
   `org_id` column has RLS enabled. The API runs each request inside one
   transaction and issues `SET LOCAL app.current_org = <org_id>` after resolving
   the caller's org context, so Postgres will not return another tenant's rows
   even if an application-level check is missed. `require_role(...)` is
   authorization *by action*; RLS is isolation *by data* — two separate lines of
   defense. See [[Cloud Authentication|Cloud-Authentication]] for the full model.

For a self-hosted single-tenant install, the same policies stay in place but
`app.current_org` always points at the one organization, making isolation
trivial.

The analysis sandbox connects to Postgres with a **narrow role scoped to a single
schema** (`search_path` + a GRANT on `project_<id>` only), so a leaked token
still cannot read another project's data.

## Design principles

- **"Service Integration last."** The platform was built so that all the *pure*
  domain logic lives behind thin boundaries and stubs, with real service wiring
  (Postgres, Gitea, Redis, Docker, MinIO/S3, Stripe, LLM, SSO IdP, hosting) done
  as a single final stage. The web app even ships clickable on fixtures
  (`NEXT_PUBLIC_USE_MOCK=true`) with no services running at all.
- **Pure-logic modules + pluggable seams.** Provider-selectable pieces sit behind
  small interfaces chosen by config:
  - the **auth verifier** (`auth_provider` = `dev` JWT vs `supabase`),
  - **billing** (`billing_provider` = `stub` vs Stripe),
  - the **AI assistant** (`ai_provider` = `stub` vs a real model),
  - **SSO** (`sso_provider` = OIDC/SAML config behind the verifier seam).

  Each deferred piece is isolated behind its seam, so it is enabled by config /
  a provider implementation without rewriting the product.
- **Sandboxed untrusted code.** `load_survey` executes arbitrary user Python, so
  both validation and deploy run user code only inside an ephemeral container
  with no platform secrets and no network egress — a SaaS requirement from day
  one, not an afterthought.

## Technology stack

| Layer | Technology |
| :--- | :--- |
| API | FastAPI + uvicorn (async) |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 15 (schemas, JSONB, RLS) |
| Git hosting | Gitea |
| Queue / workers | ARQ + Redis |
| Object storage | MinIO (S3-compatible) |
| Survey host | nginx (static bundle serving) |
| Sandbox | Docker (Docker-out-of-Docker) |
| Frontend | Next.js (App Router) |
| Auth | PyJWT + passlib[bcrypt] |

Production runs the same `docker-compose.yml` on a single VPS managed by Coolify,
with Cloudflare for DNS/CDN/TLS; a `git push` triggers an automatic rebuild.

## See also

[[Cloud Overview|Cloud-Overview]] · [[Cloud Domain Model|Cloud-Domain-Model]] · [[Cloud Authentication|Cloud-Authentication]] · [[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]] · [[Cloud Quick Start|Cloud-Quick-Start]]
