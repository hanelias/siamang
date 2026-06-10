# Cloud Data Model and Migrations

siamang Cloud stores everything in **PostgreSQL**, split into two layers:

1. A shared **platform schema** (`public.*`) holding orgs, users, projects, and
   all the operational tables — protected by Row-Level Security (RLS) for
   multi-tenant isolation.
2. One **per-project data schema** (`project_<id>`) per project, holding that
   project's collected survey responses, survey metadata, and quota counters —
   mirroring the engine's `SupabaseBackend` layout.

Schema changes to the platform layer are managed with **Alembic**; the per-project
schemas are created at runtime by the API, not by migrations. This page documents
both layers, how RLS is enforced, and what each migration (001–012) adds.

---

## Platform schema (`public.*`)

The initial migration creates the core tenant model. Tables carrying `org_id`
(below) are isolated by RLS; the others are global registries gated at the
application layer.

| Table | Purpose | RLS |
| :--- | :--- | :--- |
| `organizations` | Tenants. `slug`, `name`, `plan`, `type`, `plan_expires_at`, `sso_config`. | — (resolved via SECURITY DEFINER helpers) |
| `users` | Accounts. `email`, `name`, `password_hash` (nullable for OAuth), `gitea_user_id`, `gitea_token_enc`, `oauth_provider`/`oauth_sub`. | — |
| `memberships` | User ↔ org with `role` (owner/admin/member). | — |
| `projects` | A project = a Gitea repo + a `project_<id>` schema. `slug`, `name`, `gitea_repo_id`, `gitea_full_name`, `pg_schema`, `default_branch`. | **Yes** |
| `commit_status` | Per-commit validation result (`state`, `report_json`). | **Yes** |
| `deployments` | Published surveys (`environment`, `slug`, `status`, `survey_id`, `url`, `logs`). | **Yes** |
| `runs` | Analysis runs (`type`, `path`, `status`, `output_path`, `report_key`, `log`). | **Yes** |
| `project_files` | Uploaded assets + run outputs in object storage (`path`, `minio_key`, `size`). | **Yes** |
| `audit_log` | Append-only per-org activity (`action`, `target`, `meta_json`). | **Yes** |
| `survey_registry` | Maps a public `survey_id` → project schema for Ingest. | — (the `survey_id` is the capability) |
| `api_keys` | Personal `sck_…` tokens (`token_prefix`, `token_hash`, `revoked`, `expires_at`). | — |
| `schedules` | Cron-scheduled runs (`kind`, `script_name`, `cron`, `branch`, `enabled`). | — (app-gated; worker reads across orgs) |
| `webhook_endpoints` | Outgoing org webhooks (`url`, `secret`, `events`). | — |
| `plan_tiers` | Reference copy of plan caps/features for ops visibility. | — |
| `project_secrets` | Fernet-encrypted per-project credentials (`key`, `value_encrypted`). | **Yes** |
| `git_mirrors` | Push/pull mirror configs to GitHub/GitLab (`provider`, `direction`, `remote_path`, `secret_key`). | **Yes** |
| `invite_codes` | Operator-minted trial codes (`code`, `plan`, `trial_days`, `max_uses`, `used_count`). | — |
| `webhook_deliveries` | Per-attempt webhook delivery journal (`event`, `payload`, `status`, `attempts`, `next_attempt_at`). | — |

> `schedules` carries `org_id` but is created in migration 004, which documents
> these platform-feature tables (`api_keys`, `schedules`, `webhook_endpoints`) as
> intentionally **not** under RLS — access is gated by membership/role checks in
> the application, because the worker's scheduler/notifier reads them across orgs.

---

## Per-project schema (`project_<id>`)

When a project is created, `database_service.create_project_schema` runs
`project_schema_ddl` to provision a dedicated schema named `project_<id>`
(validated against `^project_\d+$` before being inlined). It contains three
tables:

```sql
CREATE TABLE project_<id>.responses (
    id            BIGSERIAL PRIMARY KEY,
    survey_id     TEXT NOT NULL,
    data          JSONB NOT NULL,
    respondent_id UUID DEFAULT gen_random_uuid(),
    partial       BOOLEAN NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE project_<id>.survey_meta (
    id             BIGSERIAL PRIMARY KEY,
    survey_id      TEXT UNIQUE NOT NULL,
    title          TEXT,
    schema_json    JSONB,
    variables_json JSONB,
    max_responses  INTEGER,
    schema_hash    TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE project_<id>.quota_counters (
    id        BIGSERIAL PRIMARY KEY,
    survey_id TEXT NOT NULL,
    variable  TEXT NOT NULL,
    value     TEXT NOT NULL,
    target    INTEGER NOT NULL,
    current   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (survey_id, variable, value)
);
```

Notable details:

- **Respondent resume / dedup:** a unique index on `(survey_id, respondent_id)`
  is the conflict target for the ingest upsert
  (`ON CONFLICT (survey_id, respondent_id)`), so re-submissions update the same
  row and partial responses can be resumed.
- **`survey_meta`** stores the compiled survey schema and variable dictionary,
  including custom page kinds (everything lands in `schema_json`), so no platform
  schema change was needed for them.
- **Dashboard aggregation** runs server-side SQL (frequencies, crosstabs,
  per-day series, respondent summary) directly over the full `responses` table —
  variable names are bound parameters inside `data->>…`, so arbitrary names are
  safe.

Project teardown (`drop_project_schema`) runs `DROP SCHEMA … CASCADE` and
`DROP ROLE` for the scoped login role.

---

## Row-Level Security

Tenant isolation rests on PostgreSQL RLS. For every `org_id`-bearing table, the
initial migration enables RLS and attaches an `org_isolation` policy:

```sql
CREATE POLICY org_isolation ON <table>
    USING (org_id = current_setting('app.current_org', true)::bigint)
    WITH CHECK (org_id = current_setting('app.current_org', true)::bigint);
```

The API sets `SET LOCAL app.current_org` once per request transaction. The
`true` argument to `current_setting` means an **unset** context returns `NULL` and
matches zero rows — the system fails **closed**. To establish org context for an
endpoint addressed by `project_id`, a SECURITY DEFINER helper
`app_resolve_project_org(project_id)` maps project → org while bypassing RLS;
`app_org_plan(org_id)` similarly lets the public Ingest path read a plan without
an org context.

Migration **010** adds `FORCE ROW LEVEL SECURITY`: plain `ENABLE` does not apply
to the table owner and never to a superuser, so if the app connects as the DB
owner/superuser the policies are silently bypassed. `FORCE` makes them apply to
the owner too. It is a no-op while the app still connects as a superuser, so full
defense-in-depth requires deploying under a dedicated **non-superuser** role.
Cross-tenant maintenance that legitimately spans orgs (trial cleanup, the deploy
reaper) must run via a superuser/owner connection or a SECURITY DEFINER helper.

---

## Migrations (Alembic)

Migrations live in `db/migrations/versions/`. The DSN comes from
`PLATFORM_PG_DSN` (rewritten to the psycopg3 sync driver in `db/migrations/env.py`).
Apply them with:

```bash
cd db
alembic upgrade head      # apply all
alembic downgrade base    # roll everything back (CI verifies both directions)
```

| # | Revision | Adds |
| :--- | :--- | :--- |
| 001 | `001_initial` | The full platform schema (`organizations`, `users`, `memberships`, `projects`, `commit_status`, `deployments`, `runs`, `project_files`, `audit_log`) + indexes; enables RLS and the `org_isolation` policy on the tenant tables; the `app_resolve_project_org` SECURITY DEFINER resolver. |
| 002 | `002_survey_registry` | `survey_registry` — routes a public `survey_id` to its project schema for the open Ingest API. Intentionally **not** under RLS (the unguessable `survey_id` is the capability). |
| 003 | `003_auth_providers` | OAuth identity columns on `users` (`oauth_provider`, `oauth_sub` + a partial unique index); makes `password_hash` nullable so OAuth-only accounts need no local password. |
| 004 | `004_platform_features` | `api_keys`, `schedules`, and `webhook_endpoints`. Not under RLS — `api_keys` are read during authentication before any org context exists, and the worker's scheduler/notifier read across orgs; access is gated in the application. |
| 005 | `005_plan_limits` | `app_org_plan(org_id)` (SECURITY DEFINER, so the public Ingest path can read a plan past RLS) + a reference `plan_tiers` table documenting the default caps/features per plan. |
| 006 | `006_secrets_and_mirrors` | `project_secrets` (Fernet-encrypted per-project credentials) and `git_mirrors` (push/pull mirror configs). Both under RLS by `org_id`. |
| 007 | `007_org_sso_config` | `organizations.sso_config` (JSONB) — stored OIDC/SAML config for orgs on an SSO-capable plan. The login flow itself is deferred to Service Integration. |
| 008 | `008_org_type_and_roles` | `organizations.type` (`personal` \| `cooperative`) and normalizes legacy membership roles onto `owner`/`admin`/`member` (manager → admin; developer/analyst/viewer → member). |
| 009 | `009_trials_and_invites` | `organizations.plan_expires_at` (NULL = permanent) and the `invite_codes` table backing the operator invite/redeem system. `invite_codes` is global (not under RLS). |
| 010 | `010_force_rls` | `FORCE ROW LEVEL SECURITY` on all tenant tables so the policies apply to the table owner, not just non-owners — the schema half of running the app as a non-superuser. |
| 011 | `011_registry_status_check` | A `CHECK` constraint pinning `survey_registry.status` to `('live', 'stopped')`, so a typo can't make a survey silently unroutable. |
| 012 | `012_webhook_deliveries` | `webhook_deliveries` — a per-attempt journal (`status` `pending`/`ok`/`failed`, `attempts`, `next_attempt_at`) powering webhook retries with backoff; partial index on due pending rows. Not under RLS. |

CI runs migration apply/rollback against a real Postgres in the `migrations` job —
see [[Cloud CI CD and Testing|Cloud-CI-CD-and-Testing]].

## See also

[[Cloud Domain Model|Cloud-Domain-Model]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Cloud Configuration|Cloud-Configuration]]
