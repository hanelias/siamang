# Cloud Domain Model

The platform's data model lives in a single PostgreSQL `public` schema (the
control plane), while each project's collected data lives in its own isolated
`project_<id>` schema. This page describes the core entities, how they relate,
the roles/personas, and the per-project data tables.

## Core entities

These are the platform (control-plane) tables, defined as SQLAlchemy models in
`api/app/models.py`.

### Organization

The tenant — an agency or a personal workspace. Container for projects, team
membership, and billing.

| Field | Notes |
| :--- | :--- |
| `id`, `slug`, `name` | `slug` is unique |
| `plan` | Subscription tier (default `free`) |
| `type` | `personal` (solo) or `cooperative` (can invite a team) |
| `sso_config` | Per-org OIDC/SAML config (JSON, nullable) |
| `plan_expires_at` | Trial expiry; non-NULL only for invite-code trial orgs |

### User

A global account; org membership is expressed through `Membership`.

| Field | Notes |
| :--- | :--- |
| `id`, `email`, `name` | `email` is unique |
| `password_hash` | Nullable — OAuth-only accounts (Supabase) have no local password |
| `oauth_provider`, `oauth_sub` | Set for external-identity accounts |
| `gitea_user_id`, `gitea_token_enc` | The user's mirrored Gitea account and its encrypted access token |

### Membership

Join row linking a user to an org with a role. Primary key is `(user_id,
org_id)`; both cascade on delete.

| Field | Notes |
| :--- | :--- |
| `user_id`, `org_id` | Composite key |
| `role` | `owner` / `admin` / `member` (legacy fine-grained roles also accepted — see below) |

### Project

A research study: a Git repository plus a Postgres data schema. Unique per
`(org_id, slug)`.

| Field | Notes |
| :--- | :--- |
| `id`, `org_id`, `slug`, `name` | |
| `gitea_repo_id`, `gitea_full_name` | The backing Gitea repo (`<org_slug>/<project_slug>`) |
| `pg_schema` | The project's data schema, `project_<id>` |
| `default_branch` | Defaults to `main` |

### Deployment

A concrete publish of a survey, bound to a commit SHA and an environment. Unique
per `(project_id, environment, slug)`; a re-deploy reuses the row (and its
`survey_id`, so collected responses stay attached).

| Field | Notes |
| :--- | :--- |
| `commit_sha`, `environment`, `slug` | `environment` e.g. `pilot` / `main` |
| `status` | `queued` → `building` → `live` / `failed` / `stopped` |
| `survey_id` | Deployed-survey identifier (capability used by the Ingest API) |
| `url`, `logs` | Public URL and accumulated build log |

### Run

A single execution of an analysis script (or a run-all).

| Field | Notes |
| :--- | :--- |
| `type` | `analysis` (single script) or `analysis_all` (run all) |
| `path`, `commit_sha` | Script entry path; pinned commit |
| `status` | `queued` / `running` → `completed` / `failed` |
| `output_path`, `report_key` | Output location and the generated report's object key |
| `log` | Captured stdout |

### ProjectFile

Metadata for binary assets and run outputs; the bytes themselves live in MinIO.

| Field | Notes |
| :--- | :--- |
| `path` | e.g. `assets/logo.png` or `reports/...` |
| `minio_key`, `size`, `content_type` | Object-store location and metadata |

### SurveyRegistry

Routes an incoming `survey_id` to the project schema that should store its
responses; keyed by `survey_id`.

| Field | Notes |
| :--- | :--- |
| `survey_id` | Primary key |
| `project_id`, `org_id`, `pg_schema`, `environment` | Routing target |
| `max_responses`, `status` | Collection cap; `status` e.g. `live` / `stopped` |

### Audit

Every privileged action is recorded. (The model is the `audit_log` table; rows
carry `org_id`, `user_id`, `action` such as `project.create` / `deploy.create` /
`member.invite`, an optional `target`, and a JSON `meta`.)

### Supporting entities

| Entity | Purpose |
| :--- | :--- |
| `ApiKey` | Personal API keys (`sck_…`), stored as a SHA-256 hash with prefix, expiry, and revoked flag |
| `Schedule` | Cron-scheduled analysis runs (`run_script` / `run_all`) per project |
| `WebhookEndpoint` | Outgoing webhook endpoints per org (URL, secret, event list) |
| `WebhookDelivery` | Delivery journal for outgoing webhooks (status, attempts, retry/backoff) |
| `ProjectSecret` | Per-project encrypted secrets (Fernet), write-only; unique per `(project_id, key)` |
| `GitMirror` | Push/pull mirror config to GitHub/GitLab |
| `InviteCode` | Operator-minted code that redeems into a trial org |
| `CommitStatus` | Validation result per `(project_id, commit_sha)`: `pending` / valid / warnings / error + report JSON |

## Relationships

```
organizations 1───∞ memberships ∞───1 users
      │
      1
      │
      ∞
   projects 1───∞ commit_status
      │      1───∞ deployments 1───∞ (survey_registry by survey_id)
      │      1───∞ runs
      │      1───∞ project_files
      │      1───∞ schedules · project_secrets · git_mirrors
      │
      └── pg_schema → "project_<id>"  (separate Postgres schema; see below)

organizations 1───∞ webhook_endpoints 1───∞ webhook_deliveries
organizations 1───∞ audit_log
users         1───∞ api_keys
```

Most child tables also carry a denormalized `org_id` so Row-Level Security can
isolate them per tenant. See [[Cloud Authentication|Cloud-Authentication]].

## Roles and personas

### Personas

| Persona | What they do |
| :--- | :--- |
| **Project Manager** | Creates projects, deploys surveys, manages the team and access |
| **Methodologist / Survey programmer** | Writes `questionnaire.py`, `variables.py`, and the config; commits; fixes after validation |
| **Analyst** | Reads data, writes cleaning scripts, builds tables/charts, exports results |
| **Org Owner / Admin** | Billing, organization settings, member management |
| **Respondent** | External user; takes the survey via its public URL (no account) |

### Role ranks

The canonical product roles are **`owner` > `admin` > `member`**. Older
fine-grained roles are mapped onto the same rank scale so existing memberships
and `require_role(...)` call sites keep working:

| Role | Rank |
| :--- | :--- |
| `owner` | 4 |
| `admin`, `manager` | 3 |
| `member`, `developer` | 2 |
| `analyst` | 1 |
| `viewer` | 0 |

Roughly: viewers read; analysts also run analysis and write to data tables;
members/developers also push code and create/stop deployments; admins/managers
also invite members and create projects; the owner also controls billing and
org type. Ownership is never granted through an invite.

## Per-project data tables

When a project is created, the platform creates a dedicated schema `project_<id>`
whose table structure mirrors the engine's Supabase backend (so data formats stay
compatible). The three managed tables are:

| Table | Purpose |
| :--- | :--- |
| `responses` | One row per submission: `survey_id`, `data` JSONB (`{var: value}`), `respondent_id`, timestamps |
| `survey_meta` | Per-survey metadata: `title`, `schema_json` (compiled `SurveySchema`), `variables_json`, `max_responses`, `schema_hash` |
| `quota_counters` | Quota tracking: `(survey_id, variable, value)` with `target` and `current` |

`variables_json` is critical: the analysis SDK reconstructs the variable map from
it so engine reporting produces labeled tables (labels, scale, missing values)
without loading `questionnaire.py`. Analysts create further tables (e.g.
`clean_responses`, `aggregates`) in the same schema via the SDK. For the full
schema and migrations, see
[[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]].

## See also

[[Cloud Architecture|Cloud-Architecture]] · [[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]] · [[Cloud Authentication|Cloud-Authentication]] · [[Cloud REST API|Cloud-REST-API]]
