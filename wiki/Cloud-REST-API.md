# Cloud REST API

The complete endpoint reference for the siamang Cloud platform API (FastAPI),
grouped by router. Every path and method below was verified against the router
source in `api/app/routers/`. Responses are JSON.

## Base URL and authentication

- **Base URL** (local): `http://localhost:8000`.
- **Authentication**: a bearer token in the `Authorization` header —
  `Authorization: Bearer <token>` — on every endpoint **except** Health, the
  public parts of Auth, the public Ingest API, and the Gitea push webhook.
- A bearer may be a platform-issued JWT (or Supabase JWT) **or** a personal API
  key (`sck_…`). The operator admin API uses an `X-Admin-Token` header instead.

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/orgs
```

Endpoints below are marked **public** (no auth), **user** (any authenticated
user), **org/project** (requires membership in the resource's org), or with a
minimum **role** when `require_role(...)` applies (see
[[Cloud Authentication|Cloud-Authentication]] for the role model).

## Contents

- [Meta](#meta)
- [Health](#health)
- [Auth](#auth)
- [Organizations](#organizations)
- [Projects](#projects) (incl. Repository)
- [Deployments](#deployments)
- [Ingest (public)](#ingest-public)
- [Analysis](#analysis)
- [Database / Export](#database--export)
- [Dashboard](#dashboard)
- [Monitoring](#monitoring)
- [Files](#files)
- [Reports](#reports)
- [Schedules](#schedules)
- [Webhooks](#webhooks)
- [Secrets](#secrets)
- [Mirrors](#mirrors)
- [Connectors](#connectors)
- [Billing](#billing)
- [Assistant](#assistant)
- [SSO](#sso)
- [Admin](#admin)

---

## Meta

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /` | public | Service banner `{"service": ..., "version": ...}` |

## Health

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /health` | public | Liveness probe — `{"status": "ok"}` |
| `GET /health/ready` | public | Readiness probe — `200` only when Postgres and Redis are reachable, else `503` |

```json
{"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}
```

## Auth

Prefix `/auth`. The token/register/redeem endpoints are public; the rest require
a bearer.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /auth/register` | public | Create an account (mirrors the user into Gitea) |
| `POST /auth/check-email` | public | Whether an account exists for an email |
| `POST /auth/token` | public | Exchange email + password for an access token |
| `POST /auth/password` | user | Change the signed-in user's password |
| `POST /auth/logout` | public | Revoke the presented bearer token (adds its `jti` to a denylist) |
| `POST /auth/redeem` | public | Redeem an invite code into a fresh trial org and auto-login |
| `GET /auth/me` | user | The current user plus their org memberships |
| `POST /auth/api-keys` | user | Create a personal API key (returned once) |
| `GET /auth/api-keys` | user | List the caller's API keys |
| `DELETE /auth/api-keys/{key_id}` | user | Revoke an API key |

```bash
# Register, then get a token
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"pm@agency.com","name":"PM","password":"correct horse"}'

curl -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"pm@agency.com","password":"correct horse"}'
```

```json
{"access_token": "eyJhbGciOi...", "token_type": "bearer"}
```

`GET /auth/me`:

```json
{
  "user": {"id": 1, "email": "pm@agency.com", "name": "PM"},
  "memberships": [
    {"org_id": 1, "org_slug": "agency", "role": "owner",
     "org_type": "cooperative", "plan": "pro", "plan_expires_at": null, "days_left": null}
  ]
}
```

## Organizations

Prefix `/orgs`. Listing/creating orgs needs only a bearer; org-scoped routes
require membership, and several mutations require `admin`/`owner`.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /orgs` | user | Create an org (creator becomes `owner`) |
| `GET /orgs` | user | List the caller's organizations |
| `GET /orgs/{org}` | org member | Get one organization |
| `PATCH /orgs/{org}` | admin (rename) / owner (type) | Update name or `type` |
| `PATCH /orgs/{org}/plan` | owner | Set the plan tier |
| `GET /orgs/{org}/members` | org member | The org roster |
| `POST /orgs/{org}/members` | admin | Invite / set a member's role |
| `DELETE /orgs/{org}/members/{user_id}` | admin | Remove a member |
| `GET /orgs/{org}/audit` | admin | The org audit log |
| `GET /orgs/{org}/webhooks` | admin | List outgoing webhook endpoints |
| `GET /orgs/{org}/webhooks/deliveries` | admin | Recent webhook delivery journal (`?limit=`) |
| `POST /orgs/{org}/webhooks` | admin | Create a webhook endpoint (Plus+ feature) |
| `DELETE /orgs/{org}/webhooks/{webhook_id}` | admin | Delete a webhook endpoint |

```bash
curl -X POST http://localhost:8000/orgs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"slug":"agency","name":"Research Agency","type":"cooperative"}'
```

```json
{"id": 1, "slug": "agency", "name": "Research Agency", "plan": "free",
 "type": "cooperative", "plan_expires_at": null, "days_left": null, "warnings": []}
```

## Projects

A project provisions a Gitea repo, a Postgres schema, a skeleton commit, and a
push webhook. The Repository endpoints proxy Gitea. Editing the repo requires
the `developer` rank (member+); branch protection requires `manager` (admin+).

### Project CRUD

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /orgs/{org}/projects` | admin | Create a project (`template`: `default` or `example`) |
| `GET /orgs/{org}/projects` | org member | List projects (with response totals) |
| `GET /projects/{project_id}` | project member | Get one project |
| `PATCH /projects/{project_id}` | admin | Rename / change default branch |
| `DELETE /projects/{project_id}` | admin | Delete the project (repo + schema + rows) |

### Repository (Gitea-backed)

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/repository/tree` | project member | File tree (`?ref=`) |
| `GET /projects/{project_id}/repository/files/{path}` | project member | Read a file's text (`?ref=`) |
| `PUT /projects/{project_id}/repository/files/{path}` | developer | Create/update a file (commit) |
| `DELETE /projects/{project_id}/repository/files/{path}` | developer | Delete a file (`?branch=`, `?message=`) |
| `POST /projects/{project_id}/repository/move` | developer | Move/rename a file |
| `GET /projects/{project_id}/repository/branches` | project member | List branches |
| `POST /projects/{project_id}/repository/branches` | developer | Create a branch |
| `POST /projects/{project_id}/repository/protect` | manager | Protect a branch (optionally require validation status) |
| `GET /projects/{project_id}/repository/clone` | project member | Clone URL + the caller's personal Git token |
| `GET /projects/{project_id}/commits` | project member | List commits (`?branch=`) with validation status |
| `GET /projects/{project_id}/commits/{sha}/status` | project member | Validation status for a commit |
| `GET /projects/{project_id}/commits/{sha}/diff` | project member | Commit diff |
| `GET /projects/{project_id}/pulls` | project member | List pull requests (`?state=`) |
| `POST /projects/{project_id}/pulls` | developer | Open a pull request |
| `POST /projects/{project_id}/pulls/{number}/merge` | developer | Merge a pull request |
| `GET /me/ssh-keys` | user | List the caller's Git SSH keys |
| `POST /me/ssh-keys` | user | Add an SSH key |

```bash
curl -X PUT \
  "http://localhost:8000/projects/42/repository/files/survey/questionnaire.py" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"survey = Questionnaire(...)","message":"edit","branch":"main"}'
```

`GET /projects/{id}/commits/{sha}/status`:

```json
{"commit_sha": "9af1c2e", "branch": "main", "state": "valid",
 "report": [{"code": "...", "severity": "warning", "message": "...", "location": "..."}],
 "checked_at": "2026-06-10T12:00:00Z"}
```

## Deployments

Trigger a build/deploy of the survey and track its status. The build runs in the
deploy worker; logs stream over Server-Sent Events.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /projects/{project_id}/deployments` | developer | Build & deploy a survey (live, accepts responses) |
| `POST /projects/{project_id}/deployments/preview` | developer | Build a staging preview (no ingest) |
| `GET /projects/{project_id}/deployments` | project member | List deployments |
| `GET /projects/{project_id}/deployments/{deployment_id}` | project member | Get one deployment |
| `POST /projects/{project_id}/deployments/{deployment_id}/stop` | developer | Stop a deployment (stops accepting responses) |
| `GET /projects/{project_id}/deployments/{deployment_id}/logs` | project member | Live build log (SSE) |
| `GET /projects/{project_id}/deployments/{deployment_id}/logs/text` | project member | Accumulated log text (non-streaming) |

```bash
curl -X POST http://localhost:8000/projects/42/deployments \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"environment":"pilot","branch":"main"}'
```

```json
{"id": 7, "project_id": 42, "environment": "pilot", "slug": "pilot",
 "status": "queued", "commit_sha": "9af1c2e", "survey_id": "a1b2c3d4e5f6",
 "url": null, "created_at": "2026-06-10T12:00:00Z", "deployed_at": null}
```

## Ingest (public)

Prefix `/ingest`. **No auth** — the `survey_id` is the capability. Deployed survey
bundles POST answers here; rate-limited per `survey_id` + client IP.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /ingest/{survey_id}/responses` | public | Submit a survey response |
| `POST /ingest/{survey_id}/quota-check` | public | Check whether a quota cell still has room |

```bash
curl -X POST http://localhost:8000/ingest/a1b2c3d4e5f6/responses \
  -H 'Content-Type: application/json' \
  -d '{"responses": {"satisfaction": 4, "remote_freq": 2}, "partial": false}'
```

```json
{"status": "ok", "id": 1234}
```

Optional fields: `respondent_id` (enables resume/dedup) and `partial`.
`quota-check` returns `{"ok": true|false}`.

## Analysis

Analysis scripts are declared in the project's `siamang.yaml`. Runs execute in a
sandbox and write outputs/reports to object storage.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/scripts` | project member | List analysis scripts from `siamang.yaml` |
| `GET /projects/{project_id}/runtime` | project member | Read the project's runtime config (python + packages) |
| `POST /projects/{project_id}/scripts/{name}/run` | analyst | Enqueue a single analysis script |
| `POST /projects/{project_id}/scripts/run-all` | analyst | Enqueue all analysis scripts (combined report) |
| `GET /projects/{project_id}/runs` | project member | List runs (`?limit=`, `?offset=`) |
| `GET /projects/{project_id}/reports` | project member | List generated report files (`reports/…`) |

```json
{"id": 88, "project_id": 42, "type": "analysis", "path": "scripts/final_tables.py",
 "commit_sha": "9af1c2e", "status": "queued", "output_path": null,
 "report_key": null, "log": null, "created_by": 1,
 "started_at": "2026-06-10T12:00:00Z", "finished_at": null}
```

## Database / Export

Read access to a project's data schema (`project_<id>`). Browsing is open to any
project member; deleting a response requires `developer`.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/database/tables` | project member | List tables with row counts |
| `GET /projects/{project_id}/database/tables/{table}/schema` | project member | Column schema |
| `GET /projects/{project_id}/database/tables/{table}/preview` | project member | Preview rows (`?limit=`) |
| `GET /projects/{project_id}/database/tables/{table}/export` | project member | Download a full table (`?format=csv\|xlsx\|parquet\|sav\|sqlite`) |
| `DELETE /projects/{project_id}/database/responses/{response_id}` | developer | Delete a single response (GDPR erasure) |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/projects/42/database/tables/responses/export?format=xlsx" \
  -o responses.xlsx
```

## Dashboard

Server-side aggregation over a project's responses (correct at any data volume).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/dashboard/summary` | project member | Respondent summary + responses per day (`?days=`) |
| `GET /projects/{project_id}/dashboard/variables` | project member | Variables available for charting |
| `GET /projects/{project_id}/dashboard/frequencies` | project member | Frequency distribution for one variable (`?variable=`) |
| `GET /projects/{project_id}/dashboard/crosstab` | project member | Crosstab of two variables (`?rows=`, `?cols=`) |

```json
{"responses": 312, "respondents": 300, "duplicates": 12, "partial": 18,
 "partial_percent": 5.8, "last_response_at": "2026-06-10T11:59:00Z",
 "per_day": [{"day": "2026-06-09", "count": 41}]}
```

## Monitoring

Live fieldwork monitoring for a deployment's survey.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/deployments/{deployment_id}/stats` | project member | Response count, cap, percent, last response |
| `GET /projects/{project_id}/deployments/{deployment_id}/quotas` | project member | Quota cell progress |
| `GET /projects/{project_id}/deployments/{deployment_id}/codebook` | project member | The survey's variable dictionary |

## Files

Project assets and run outputs (`project_files` rows + MinIO objects).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/files` | project member | List files |
| `POST /projects/{project_id}/files` | developer | Upload an asset (multipart; 50 MB limit) |
| `GET /projects/{project_id}/files/{file_id}/download` | project member | Get a presigned download URL (expires in 300s) |
| `DELETE /projects/{project_id}/files/{file_id}` | developer | Delete a file |

```json
{"url": "http://minio:9000/siamang/...?X-Amz-...", "expires_in": 300}
```

## Reports

Report artifacts generated by analysis runs. Rendered reports are *stored* in
object storage (MinIO/S3) — the worker uploads them and records the object key on
`runs.report_key` — while the Reports endpoints are the *surfacing* layer
(`GET /projects/{id}/reports` lists them; the endpoints below address an artifact
by its repository path).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/reports/{path}` | project member | Report artifact metadata + inline text content |
| `GET /projects/{project_id}/reports/{path}/download` | project member | Resolve a downloadable artifact URL (`?format=`) |

## Schedules

Cron-scheduled analysis runs. A Plus+ feature (`FEATURE_SCHEDULES`).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/schedules` | project member | List schedules |
| `POST /projects/{project_id}/schedules` | analyst | Create a schedule (`kind`: `run_script`/`run_all`, `cron`) |
| `DELETE /projects/{project_id}/schedules/{schedule_id}` | analyst | Delete a schedule |

```bash
curl -X POST http://localhost:8000/projects/42/schedules \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"kind":"run_all","cron":"0 6 * * *","branch":"main","enabled":true}'
```

## Webhooks

The inbound Gitea push webhook. **Not bearer-authenticated** — validated by an
HMAC signature (`X-Gitea-Signature`) against `GIT_WEBHOOK_SECRET`. (Outgoing
webhook *endpoints* are managed under [Organizations](#organizations).)

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /webhooks/git` | HMAC signature | Gitea push event → enqueue validation |

## Secrets

Per-project encrypted secrets (Fernet). Values are **write-only**: list/read
return only key names, never plaintext.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/secrets` | project member | List secret key names |
| `POST /projects/{project_id}/secrets` | developer | Set/replace a secret value |
| `DELETE /projects/{project_id}/secrets/{key}` | developer | Delete a secret |

## Mirrors

Push this project's repo to GitHub/GitLab, or pull from them (performed by Gitea).
A Pro/Corporate feature (`FEATURE_CONNECTORS`).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/mirrors` | project member | List mirrors |
| `POST /projects/{project_id}/mirrors` | developer | Create a mirror (`provider`, `direction`, `remote_path`, optional `secret_key`) |
| `POST /projects/{project_id}/mirrors/{mirror_id}/sync` | developer | Trigger a mirror sync |
| `DELETE /projects/{project_id}/mirrors/{mirror_id}` | developer | Delete a mirror |

## Connectors

Connector tasks declared in `siamang.yaml`. Connectors are *available to
configure* (a Pro/Corporate feature); running transfers is deferred.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /projects/{project_id}/connectors` | project member | List connector tasks from `siamang.yaml` |

## Billing

Prefix `/orgs`. In the default `stub` provider a checkout applies the chosen plan
immediately (no payment), so the tier system is fully exercisable without Stripe.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /orgs/{org}/billing` | org member | Current plan + plan catalogue + trial state |
| `POST /orgs/{org}/billing/checkout` | owner | Start checkout / apply a plan |
| `POST /orgs/{org}/billing/cancel` | owner | Cancel back to the `free` plan |

```json
{"plan": "pro", "status": "active", "provider": "stub",
 "available": [{"plan": "plus", "price_cents": 0, "features": ["..."]}],
 "plan_expires_at": null, "days_left": null}
```

## Assistant

AI assistant endpoint (parked). The route and the `FEATURE_AI` flag exist, but the
feature was removed from the product for beta-2 and **no plan includes it**, so the
endpoint currently answers `402 Payment Required` on every plan. The `stub` provider
behind it returns deterministic canned suggestions and is kept for the future
service-integration stage.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /projects/{project_id}/assistant` | analyst | Ask the assistant (`usecase`: `authoring`/`nl_query`/`script`/`report`) — currently `402` on all plans |

## SSO

Prefix `/orgs`. Stores a per-org OIDC/SAML configuration (a Pro/Corporate feature,
`FEATURE_SSO`). The actual login/verification flow is deferred; this manages the
config only.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /orgs/{org}/sso` | admin | Read the org's SSO config + feature availability |
| `PUT /orgs/{org}/sso` | owner | Set the SSO config (`provider`: `oidc`/`saml`) |

## Admin

Prefix `/admin`. Operator API for minting invite codes. Gated by an
`X-Admin-Token` header matched against `ADMIN_TOKEN`; an empty `ADMIN_TOKEN`
disables the whole router (every call returns `403`).

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /admin/invites` | `X-Admin-Token` | Mint one or more invite codes |
| `GET /admin/invites` | `X-Admin-Token` | List invite codes |

```bash
curl -X POST http://localhost:8000/admin/invites \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"plan":"pro","trial_days":14,"max_uses":1,"count":5}'
```

## See also

[[Cloud Authentication|Cloud-Authentication]] · [[Cloud Domain Model|Cloud-Domain-Model]] · [[Cloud Architecture|Cloud-Architecture]] · [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]] · [[Cloud Quick Start|Cloud-Quick-Start]]
