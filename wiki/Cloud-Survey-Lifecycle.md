# Cloud Survey Lifecycle

This page traces how a survey goes from a commit in Git to a **live** survey
collecting responses on the public Ingest API. Three worker tasks do the work —
`validate`, `deploy` (and its sibling `preview`) — and a public Ingest endpoint
accepts answers from the deployed bundle. Each stage runs untrusted user code
inside a [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] container; the
trusted worker performs the database and filesystem writes.

The endpoints that trigger these tasks are documented in the
[[Cloud REST API|Cloud-REST-API]].

## Overview

```text
git push ──► POST /webhooks/git ──► enqueue "validate"
                                        │
                                        ▼
   ┌──────────────────────── validate task ───────────────────────────┐
   │ download archive @sha → sandbox `validate` → commit_status        │
   │                                            → Gitea commit status   │
   └────────────────────────────────────────────────────────────────────┘

POST /projects/{id}/deployments ──► enqueue "deploy" (or "preview")
                                        │
                                        ▼
   ┌──────────────────────── deploy task ─────────────────────────────┐
   │ download archive @sha                                             │
   │   → sandbox `build`  (compile + bundle, no DB, no network)        │
   │   → provision_survey (survey_meta + quota_counters + registry)    │
   │   → publish bundle   (copy /out → nginx surveys volume)           │
   │   → deployments.status = live, url, notify "deploy.live"          │
   └────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
respondent's browser ──► POST /ingest/{survey_id}/responses   (answers)
                    └──► POST /ingest/{survey_id}/quota-check  (cell capacity)
```

## Stage 1 — Validate

### Trigger

A `git push` makes Gitea fire a `push` webhook at `POST /webhooks/git`, signed
with an HMAC secret. The API verifies the signature, resolves the project by
`gitea_repo_id`, upserts a `commit_status` row in the `pending` state, and
enqueues the `validate` job with the commit SHA, branch, repo full name, and a
default entry path. (See [[Cloud Scheduling and Webhooks|Cloud-Scheduling-and-Webhooks]]
for the incoming-webhook details.)

### The `validate` worker task

`worker/app/tasks/validate.py`:

1. Downloads the commit's source tree as a `tar.gz` from the Gitea archive API
   (`download_archive`) and extracts it to a temp directory.
2. Reads `siamang.yaml` and resolves the survey entry path via `survey_entry()`
   (falling back to `survey/questionnaire.py`).
3. Runs the sandbox in **validate** mode (`run_validate`) — fully offline
   (`--network none`), repo mounted read-only. Inside, the sandbox loads the
   questionnaire, calls `validate()` and `lint()`, and prints a JSON result.
4. Applies a **package policy check**: every `runtime.packages` entry must be in
   the curated sandbox allowlist (`disallowed_packages`); anything else turns
   the result into an `error`.
5. Writes the outcome to `public.commit_status` (`update_commit_status`) and
   mirrors it onto the Gitea commit (`set_commit_status`) so checks appear on
   commits and pull requests.

### States

| `state`    | Meaning                                  | Gitea status |
| :--------- | :--------------------------------------- | :----------- |
| `pending`  | queued / running                         | pending      |
| `valid`    | no errors and no warnings                | success      |
| `warnings` | lint warnings (listed in the report)     | warning      |
| `error`    | `validate()` raised, or a bad package    | failure      |

## Stage 2 — Deploy

### Trigger

`POST /projects/{id}/deployments` (role `developer`+) with an `environment`, an
optional `slug`, and a `branch` (default `main`). The API resolves the branch
HEAD and pins that commit SHA itself, creates a `deployments` row
(`status=queued`), and enqueues the `deploy` job. Deploy splits cleanly between
the sandbox (which only sees the code and absolute Ingest URLs) and the trusted
worker (which holds the database connection) — see
[[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]].

### The `deploy` worker task

`worker/app/tasks/deploy.py` (`_build_and_provision`):

1. **Checkout** the commit archive into a temp directory; create a separate,
   world-writable `/out` directory (the sandbox runs as uid 10001 and writes the
   bundle there).
2. **Build in the sandbox** (`run_build`, offline): compile the questionnaire and
   write the static frontend bundle into `/out`. The build also returns the rows
   the worker must persist — `survey_meta` and `quotas`. (This is the
   [[Cloud Engine Plugin|Cloud-Engine-Plugin]]'s `build_bundle()`.) A non-`built`
   result fails the deployment.
3. **Provision the database** (`provision_survey`, trusted worker): INSERT the
   `survey_meta` row and `quota_counters` rows into the project's schema
   (`project_<id>`), and a `survey_registry` row so Ingest can route by
   `survey_id`. The environment's `max_responses` from `siamang.yaml` overrides
   the questionnaire's own. All three are idempotent on `survey_id`, so
   re-deploying an environment updates rows in place.
4. **Publish the bundle** (`_publish_bundle`): replace
   `<surveys_root>/<org>/<project>/<slug>` with the freshly built bundle. nginx
   serves that directory as static files.

On success the worker sets the `deployments` row to `live` with its public URL
(`https://surveys.<domain>/<org>/<project>/<slug>/`), records an audit entry, and
emits a `deploy.live` notification. Any handled failure marks the row `failed`
and emits `deploy.failed`.

### Environments

Each environment (e.g. `pilot`, `main`, or a custom name) is a separate
deployment with its **own `survey_id`** and its own URL sub-path, so pilot and
main-fieldwork data stay separated in the `responses` table by `survey_id`.

### Preview (staging)

The `preview` task takes the **same sandboxed build + publish path** as `deploy`
but **skips DB provisioning and the registry entry**. The bundle is published
under a dedicated `preview/<project_id>/<sha>/` prefix and is **never wired to
Ingest** — a preview can be clicked through for review but accepts no responses.
Preview bundles are immutable per commit and are swept nightly once older than
their TTL (`purge_stale_previews`).

## Stage 3 — Public ingest

The deployed bundle posts answers to the public Ingest API (`api/app/routers/ingest.py`).
There is **no auth** — the `survey_id` is the capability — and CORS is open
because the bundle is plain static files with no backend of its own.

```bash
# Submit a completed response
curl -X POST https://api.example.com/ingest/<survey_id>/responses \
  -H 'Content-Type: application/json' \
  -d '{"survey_id": "<survey_id>", "responses": {"satisfaction": 4}}'
# → 201 {"status": "ok", "id": 1234}

# Ask whether a quota cell still has capacity (before showing the question)
curl -X POST https://api.example.com/ingest/<survey_id>/quota-check \
  -H 'Content-Type: application/json' \
  -d '{"survey_id": "<survey_id>", "variable": "gender", "value": 1}'
# → {"ok": true}
```

Both endpoints first resolve the survey via the registry and require its status
to be `live`. Notable guards:

- **Rate limiting** — per `survey_id` + client IP (`X-Forwarded-For` aware);
  exceeding the window returns `429`.
- **Quota / response cap** — `store_response` raises `QuotaFull` once the survey
  reaches its limit, which the endpoint returns as `409`.
- **Resume / dedup** — an optional `respondent_id` (and `partial` flag) lets a
  resumed session upsert onto the same row rather than duplicate it.

The matching client transport (the `submit` / `checkQuota` functions baked into
the bundle's `env.js`) is rendered by `PlatformClientTemplate` — see
[[Cloud Engine Plugin|Cloud-Engine-Plugin]].

## See also

[[Cloud REST API|Cloud-REST-API]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Cloud Engine Plugin|Cloud-Engine-Plugin]] · [[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]]
