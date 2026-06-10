# Cloud Sandbox and Security

siamang Cloud runs **untrusted user code** — every survey definition, deploy
build, and analysis script is authored by tenants and committed to a Git repo.
The platform never executes that code in-process. Instead it ships each operation
into an ephemeral, locked-down Docker container with no secrets, no network
egress (or a single DB-only network for analysis), a read-only filesystem, and an
unprivileged user. This page documents that sandbox plus the surrounding security
controls: scoped per-project database roles, Fernet-encrypted project secrets,
secure-config enforcement at startup, audit logging, and rate limiting.

---

## The sandbox container

The sandbox image (`sandbox/Dockerfile`) is built from the repo root so its build
context can bundle the engine archive, the engine plugin, and the SDK:

```bash
docker build -f sandbox/Dockerfile -t siamang-cloud-sandbox:latest .
```

What goes into the image:

- **Base:** `python:3.11-slim`.
- **Engine:** installed from the bundled `siamang-main.zip` archive (siamang is
  not published to a public index, so the archive itself is the version pin).
- **Plugin + SDK:** `siamang_cloud_engine` (the `PlatformBackend` / client
  template used by `build`) and the `siamang_cloud` SDK (used by analysis runs).
- **Curated analysis packages:** everything in `worker/app/allowed_packages.txt`
  (the single allowlist source — see below).
- **Entrypoint:** `sandbox/_entry.py`, baked in. The repo checkout is mounted
  read-only at `/work` at runtime.

Because the rootfs is read-only at runtime, caches are pointed at the writable
`/tmp` tmpfs so importing siamang (matplotlib) does not fail writing to `$HOME`:

```dockerfile
ENV MPLCONFIGDIR=/tmp/matplotlib \
    XDG_CACHE_HOME=/tmp/cache \
    HOME=/tmp
RUN useradd --create-home --uid 10001 sandbox
USER sandbox
WORKDIR /work
ENTRYPOINT ["python", "/opt/_entry.py"]
```

### The entrypoint and operations

`_entry.py` is invoked as `python /opt/_entry.py <operation> <args...>` and prints
its result as a single JSON line on stdout for the worker to parse. The operations:

| Operation | Purpose | Filesystem | Network |
| :--- | :--- | :--- | :--- |
| `validate` | `load_survey` → `validate(strict=False)` + `lint(level="basic")`; reports `valid` / `warnings` / `error` | `/work` read-only | none |
| `build` | Compile + bundle a survey into the worker-mounted `/out` volume (no DB; provisioning rows returned to the worker) | `/work` read-only, `/out` writable | none |
| `run_script` | Run a named analysis script; writes artifacts into `<work>/outputs`; returns stdout/stderr + output manifest | `/work` read-write | DB-only network |
| `analysis` | The `run_all` analysis step; runs a script in-place under `/work` | `/work` read-write | DB-only network |

The entry guards against path traversal: `_safe_work_path` resolves the entry
path and raises `ValueError` if it escapes `/work`.

### Hardening flags

`worker/app/sandbox.py` applies the same hardening to every run, with the network
chosen per operation. The base flags:

```python
_HARDENING_BASE = [
    "--rm",
    "--read-only",
    "--tmpfs", "/tmp",
    "--memory", "512m",
    "--cpus", "1",
    "--pids-limit", "128",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
]
_NET_NONE = ["--network", "none"]
```

- **`validate` / `build`** run fully offline (`--network none`) with the repo
  mounted read-only (`-v <repo>:/work:ro`).
- **`run_script` / `analysis`** attach to a DB-only Docker network
  (`--network <SANDBOX_NETWORK>`), mount the checkout read-write so the script can
  write into `<work>/outputs`, and receive **only** the scoped project DB
  environment (see below). No platform secrets are ever passed in.

Every operation is wrapped in a `subprocess.run(..., timeout=timeout)`; a timeout
returns a clean error such as `"validation timed out (120s)"`. The timeout comes
from `SANDBOX_TIMEOUT` (default **120 seconds**).

> The worker launches these containers via **Docker-out-of-Docker** — it mounts
> the host `/var/run/docker.sock` and runs sandbox containers on the host daemon.
> This is why the backend must run on a host with a reachable Docker daemon (see
> [[Cloud Deployment|Cloud-Deployment]]); the production SaaS blueprint swaps this
> for Fly Machines micro-VMs.

---

## The allowed-packages allowlist

`worker/app/allowed_packages.txt` is the single source of truth for which Python
packages analysis code may use:

- The **sandbox image** `pip install`s the list, so those packages are importable
  at runtime.
- The **validate task** rejects any `runtime.packages` entry in a project's
  `siamang.yaml` that is not on the list, so a commit cannot silently depend on a
  missing library.

`worker/app/packages.py` implements this. It normalizes requirement specs to their
canonical distribution name (`_norm`), always treats the platform packages
(`siamang`, `siamang-cloud`, `siamang-cloud-engine`) as available because they are
baked into the image, and exposes `disallowed_packages(config_text)` which returns
the requested specs whose name is not in the allowlist.

---

## Scoped per-project database roles

Analysis runs need to read their own collected responses, but untrusted code must
never reach another tenant's data or the platform tables. The platform provisions
a **dedicated Postgres login role per project**, scoped to only that project's
schema.

`api/app/services/database_service.py` creates the role alongside the
`project_<id>` schema (`_scoped_role_ddl`):

- Role name mirrors the schema: `project_<id>`.
- Privileges are granted **only** on `project_<id>` (USAGE/CREATE on the schema;
  SELECT/INSERT/UPDATE/DELETE on its tables and sequences, including default
  privileges for future tables).
- `search_path` is pinned to the project schema, and `REVOKE ALL ON SCHEMA public`
  removes any access to the shared schema.

The role password is **derived deterministically** with a keyed HMAC of a shared
secret and the project id, so the worker can rebuild the exact DSN without storing
any password:

```python
def role_password(secret: str, project_id: int) -> str:
    return hmac.new(secret.encode(),
                    f"project:{project_id}".encode(),
                    hashlib.sha256).hexdigest()
```

`worker/app/sandbox_db.py` mirrors this and rewrites the platform DSN into the
narrow per-project DSN, which is passed into the sandbox via
`SIAMANG_CLOUD_PG_DSN` / `SIAMANG_CLOUD_PROJECT_SCHEMA` / `SIAMANG_CLOUD_PROJECT_ID`.
The shared secret is `SANDBOX_DB_SECRET`; when it is empty **no scoped role is
provisioned** and analysis DB access is disabled.

---

## Encrypted project secrets

Tenant credentials — connector tokens, BYO-DB DSNs, Git-mirror PATs — are stored
encrypted at rest in `public.project_secrets` (migration 006), under RLS by
`org_id`. Encryption uses **Fernet** (`api/app/crypto.py`) with the key from
`FERNET_KEY`:

```python
def _fernet() -> Fernet:
    if not settings.fernet_key:
        raise RuntimeError("FERNET_KEY is not configured; cannot encrypt/decrypt secrets.")
    return Fernet(settings.fernet_key.encode())
```

The same key encrypts each user's mirrored Gitea token (`users.gitea_token_enc`).
Secret values are **write-only** over the API: the list endpoint returns keys
only, never the plaintext. Generate a key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Authentication and access tokens

The dev/localhost identity backend issues its own JWTs (`api/app/security.py`):

- Passwords are hashed with **bcrypt** (`passlib`).
- Access tokens are **HS256 JWTs** signed with `JWT_SECRET`, carrying `sub`
  (user id), a unique `jti` (so a token can be revoked on sign-out), `iat`, and
  `exp` (TTL from `JWT_TTL_MINUTES`, default 720 minutes / 12 hours).

The verifier is behind a seam (`auth_provider`): `dev` for the platform-issued
JWT, `supabase` for verifying Supabase-issued JWTs (Google/GitHub/GitLab) when the
live identity integration is enabled. Personal **API keys** (`sck_…` bearer
tokens) are stored only as SHA-256 hashes and shown once. See
[[Cloud Authentication|Cloud-Authentication]] for the full flow.

---

## Secure-config enforcement at startup

The API refuses to start client-facing with forgeable or weak secrets.
`assert_secure_config()` runs in the app lifespan (`api/app/main.py`); for the
`dev` auth provider it raises and aborts startup if any of these fail:

| Check | Requirement |
| :--- | :--- |
| `JWT_SECRET` | not a dev default, and at least 32 characters |
| `FERNET_KEY` | must be set (required to encrypt stored Git tokens / secrets) |
| `GIT_WEBHOOK_SECRET` | must be a non-default value |
| `ADMIN_TOKEN` (when set) | at least 32 characters |

The insecure defaults it rejects are `JWT_SECRET ∈ {"", "dev-insecure-change-me"}`
and `GIT_WEBHOOK_SECRET ∈ {"", "dev-webhook-secret"}`. See
[[Cloud Configuration|Cloud-Configuration]] for the full variable reference and
which values must change for production.

The API also sets baseline security headers on every response
(`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
`Strict-Transport-Security`) and scopes **CORS** to the web app and the deployed
survey host instead of `*` (bearer tokens travel in the `Authorization` header,
so cookies/credentials are not enabled).

---

## Tenant isolation (RLS)

Every table carrying `org_id` is protected by PostgreSQL **Row-Level Security**.
The API sets `SET LOCAL app.current_org` per transaction and the `org_isolation`
policy filters every row to the current org; an unset context yields zero rows
(fail-closed). Migration 010 adds `FORCE ROW LEVEL SECURITY` so the policy applies
even to the table owner — full isolation requires running the app as a
**non-superuser** role (superusers always bypass RLS). The detail, including the
per-project schema layout, is in
[[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]].

---

## Audit logging

`public.audit_log` is an append-only, per-organization activity log
(`api/app/services/audit.py`). `audit.record(...)` inserts one entry inside the
request's transaction (RLS context already set), so an audit row commits
atomically with the action it describes. Writes are **best-effort** — auditing
never raises into the primary action:

```python
except Exception:  # auditing must not break the primary action
    pass
```

Instrumented actions include `project.create`, `deploy.create` / `deploy.stop`,
`member.invite`, `response.delete`, `schedule.create`, and (from the worker)
`deploy.live` / `deploy.failed` and `run.*`. Reads power the **Activity** feed in
the web app and outgoing notifications. `list_for_org` returns the newest entries
(capped at 500).

---

## Rate limiting

A small Redis fixed-window limiter (`api/app/services/ratelimit.py`) protects
public and brute-forceable endpoints. It is **fail-open**: if Redis is
unavailable the request is allowed rather than dropping survey responses, and the
window key expires automatically.

```python
async def allow(redis, key, limit, window) -> bool:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    return count <= limit
```

Configured limiters (all fixed-window; see [[Cloud Configuration|Cloud-Configuration]]):

| Endpoint | Key | Default limit / window |
| :--- | :--- | :--- |
| Public `POST /ingest/{survey_id}/responses` | `survey_id` + client IP | `INGEST_RATE_LIMIT` = 60 / `INGEST_RATE_WINDOW` = 60s |
| `POST /auth/redeem` (invite codes) | client IP | `REDEEM_RATE_LIMIT` = 10 / `REDEEM_RATE_WINDOW` = 60s |
| `POST /auth/token`, `POST /auth/register` | client IP + email | `LOGIN_RATE_LIMIT` = 10 / `LOGIN_RATE_WINDOW` = 60s |

---

## Output caps

To stop one analysis script from filling the disk or object storage, the worker
caps the artifacts it collects from a sandbox run after it finishes (worker
`config.py`): `OUTPUTS_MAX_FILES` (default **50**) and `OUTPUTS_MAX_TOTAL_MB`
(default **200**). Files beyond these limits are skipped.

## See also

[[Cloud Architecture|Cloud-Architecture]] · [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]] · [[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]] · [[Cloud Configuration|Cloud-Configuration]]
