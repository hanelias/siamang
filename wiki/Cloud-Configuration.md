# Cloud Configuration

This is the complete environment-variable reference for siamang Cloud. Every value
is read from the environment (in development from a `.env` file copied from
`.env.example`; in production from your orchestrator's secrets — e.g. Coolify or
`fly secrets set`). The authoritative sources are `.env.example`,
`api/app/config.py` (the API `Settings`, via `pydantic-settings`), and
`worker/app/config.py` (the worker `Config`).

Variables are grouped by category below. The **Default** column is the value
applied when the variable is unset. The **Change for prod?** column flags values
that *must* be changed away from their development defaults for a client-facing
deploy — three of them are enforced at startup (see [Secure config](#secure-config-must-change-for-production)).

---

## Database

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `PLATFORM_PG_DSN` | Postgres DSN the API and workers connect to. For real RLS isolation, run the app as a **non-superuser** role (RLS is forced in migration 010 but bypassed by superusers). | `postgresql://siamang:siamang@postgres:5432/siamang` | Yes |
| `POSTGRES_USER` | Postgres user the `postgres` container is created with. | `siamang` | Recommended |
| `POSTGRES_PASSWORD` | Postgres password for that user. | `siamang` | **Yes** (strong password) |
| `POSTGRES_DB` | Database name. | `siamang` | No |

---

## Queue & Storage

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `REDIS_DSN` | Redis DSN backing the ARQ task queue. | `redis://redis:6379/0` | If hosted elsewhere |
| `MINIO_ENDPOINT` | S3-compatible object store endpoint (run outputs, reports, uploaded assets). On the worker, an **empty** endpoint means artifacts stay local (`LocalArtifactSink`). | API: `http://minio:9000` · worker: *(empty)* | If hosted elsewhere |
| `MINIO_ACCESS_KEY` | Object-store access key. | `minioadmin` | **Yes** |
| `MINIO_SECRET_KEY` | Object-store secret key. | `minioadmin` | **Yes** (strong secret) |
| `MINIO_BUCKET` | Bucket name. On the worker, an empty bucket disables object storage. | API: `siamang` · worker: *(empty)* | If hosted elsewhere |

> The worker treats object storage as enabled only when **both** `MINIO_ENDPOINT`
> and `MINIO_BUCKET` are set (`Config.minio_enabled`).

---

## Git backend (Gitea)

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `GITEA_BASE_URL` | Base URL of the Gitea instance the API/worker call. | `http://gitea:3000` | If hosted elsewhere |
| `GITEA_ADMIN_TOKEN` | Gitea admin API token. `scripts/dev_up.sh` mints one automatically in dev. | *(empty)* in code; `changeme` in `.env.example` | **Yes** |

---

## Git webhook

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `GIT_WEBHOOK_SECRET` | HMAC secret validating Gitea → API push webhooks. | `dev-webhook-secret` | **Yes** (enforced) |
| `API_INTERNAL_URL` | URL Gitea uses to reach the API for push webhooks. Default is the in-compose service name; set a routable URL if Gitea runs on a separate host. | `http://api:8000` | If Gitea is remote |

---

## Auth & Crypto

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `JWT_SECRET` | Signing key for platform-issued HS256 access tokens. | `dev-insecure-change-me` | **Yes** (enforced, ≥32 chars) |
| `JWT_TTL_MINUTES` | Access-token lifetime in minutes. | `720` (12 h) | Optional |
| `FERNET_KEY` | Fernet key encrypting stored Gitea tokens and project secrets at rest. Required for register/secrets. | *(empty)* | **Yes** (enforced) |
| `AUTH_PROVIDER` | Identity backend behind the verifier seam: `dev` (platform HS256 JWT, email/password) or `supabase` (verify Supabase JWTs). | `dev` | For social login |
| `SUPABASE_URL` | Supabase project URL (only when `AUTH_PROVIDER=supabase`). | *(empty)* | If using Supabase |
| `SUPABASE_JWKS_URL` | JWKS endpoint for verifying Supabase JWTs. | *(empty)* | If using Supabase |
| `SUPABASE_JWT_SECRET` | Supabase JWT shared secret (alternative to JWKS). | *(empty)* | If using Supabase |
| `SUPABASE_JWT_AUD` | Expected `aud` claim on Supabase JWTs. | `authenticated` | Optional |

Generate the two required secrets:

```bash
# JWT_SECRET
openssl rand -hex 32
# FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Public URLs

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `INGEST_BASE_URL` | Absolute base URL of the Ingest API, baked into deployed survey bundles (`env.js`). | `http://localhost:8000` | **Yes** |
| `SURVEYS_DOMAIN` | Domain for the survey static host. | `surveys.localhost` | **Yes** |
| `SURVEYS_BASE_URL` | Public base URL of the survey static host (nginx); baked into deploy URLs. | `http://localhost:8080` | **Yes** |
| `CORS_ALLOW_ORIGINS` | Comma-separated browser CORS allow-list for the API. When empty it is derived from `WEB_BASE_URL` + `SURVEYS_BASE_URL`. | *(empty → derived)* | Set explicitly |

---

## Sandbox & Analysis

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `SANDBOX_IMAGE` | Image tag the validate/deploy/analysis workers run. | `siamang-cloud-sandbox:latest` | No |
| `SANDBOX_TIMEOUT` | Per-run sandbox timeout, in seconds. | `120` | Optional |
| `SANDBOX_NETWORK` | Docker network the analysis sandbox attaches to in order to reach Postgres. | `.env.example`: `siamang_cloud_default` · worker default: `bridge` | **Yes** |
| `SANDBOX_DB_SECRET` | Shared secret used to derive per-project Postgres role passwords for analysis sandboxes. Empty = no scoped role provisioned (analysis DB access disabled). | *(empty)* | **Yes** (required for analysis) |
| `SURVEYS_ROOT` | Where the deploy worker writes survey bundles (shared volume with nginx). | `/srv/surveys` | No |
| `DEPLOY_STUCK_MINUTES` | A deploy/preview left in `queued`/`building` beyond this many minutes is reaped to `failed`. Comfortably above `SANDBOX_TIMEOUT`. | `15` | Optional |
| `PREVIEW_TTL_DAYS` | Staging preview bundles (`preview/<project>/<sha>/`) are purged after this many days. | `7` | Optional |
| `OUTPUTS_MAX_FILES` | Max number of files collected from a sandbox `/out` run; the rest are skipped. | `50` | Optional |
| `OUTPUTS_MAX_TOTAL_MB` | Max total size (MB) of collected run outputs. | `200` | Optional |

Generate `SANDBOX_DB_SECRET` with `openssl rand -hex 32`.

---

## Billing

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `BILLING_PROVIDER` | `stub` applies the chosen plan immediately with no payment; real Stripe checkout/webhooks are wired behind the same interface in the Service Integration stage. | `stub` | For live billing |
| `STRIPE_SECRET_KEY` | Stripe API secret key (live billing). | *(empty)* | If using Stripe |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret. | *(empty)* | If using Stripe |

See [[Cloud Subscription Tiers|Cloud-Subscription-Tiers]] for the plan matrix.

---

## AI

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `AI_PROVIDER` | `stub` returns deterministic canned suggestions; a real model (default Claude) is wired in the Service Integration stage. | `stub` | If re-enabling AI |
| `AI_API_KEY` | API key for the real AI provider. | *(empty)* | If re-enabling AI |

> The AI assistant was removed from the product for beta-2. The endpoint remains
> behind the (off-by-default) `FEATURE_AI` flag and answers HTTP 402 on every
> plan, so old clients get a clean error rather than a 404.

---

## SSO

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `SSO_PROVIDER` | `""` disables SSO; `oidc` / `saml` are wired in the Service Integration stage. Kept here as the config seam. | *(empty)* | For enterprise SSO |
| `OIDC_ISSUER` | OIDC issuer URL. | *(empty)* | If using OIDC |
| `OIDC_CLIENT_ID` | OIDC client id. | *(empty)* | If using OIDC |
| `SAML_METADATA_URL` | SAML IdP metadata URL. | *(empty)* | If using SAML |

---

## Admin & Trials

| Variable | Purpose | Default | Change for prod? |
| :--- | :--- | :--- | :--- |
| `ADMIN_TOKEN` | Gates the `/admin` invite API via the `X-Admin-Token` header. **Empty disables the admin API entirely** (every call 403s), so the demo ships closed by default. | *(empty)* | For invite trials (enforced ≥32 chars when set) |
| `WEB_BASE_URL` | Public URL of the web app; used to build invite redeem links (`…/login?code=…`) and to derive CORS. | `http://localhost:3000` | **Yes** |
| `TRIAL_DEFAULT_DAYS` | Fallback trial length (days) when a minted invite code omits one. | `14` | Optional |
| `TRIAL_GRACE_DAYS` | Grace period (days) an expired trial org keeps its data before the cleanup cron hard-deletes it (on expiry the API immediately locks the org out — 403 on every org/project request; only `/auth/me` still answers, reporting the collapsed `free` plan). | `3` (worker) | Optional |

See [[Cloud Self-Hosted Trials|Cloud-Self-Hosted-Trials]] for the invite system.

---

## Rate Limiting

All limiters are Redis fixed-window and fail-open (see
[[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]]).

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `INGEST_RATE_LIMIT` | Max ingest requests per `survey_id` + client IP per window. | `60` |
| `INGEST_RATE_WINDOW` | Ingest window length (seconds). | `60` |
| `REDEEM_RATE_LIMIT` | Max `POST /auth/redeem` per client IP per window (deters invite-code brute-forcing). | `10` |
| `REDEEM_RATE_WINDOW` | Redeem window length (seconds). | `60` |
| `LOGIN_RATE_LIMIT` | Max `POST /auth/token` and `/auth/register` per client IP + email per window. | `10` |
| `LOGIN_RATE_WINDOW` | Login window length (seconds). | `60` |

---

## Web App

These are read by the Next.js frontend. `NEXT_PUBLIC_*` values are **inlined at
build time**, so a live demo image must be built with the live values baked in.

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | API origin the browser calls. Leave empty to use relative paths through the Next server proxy. | `http://localhost:8000` |
| `NEXT_PUBLIC_USE_MOCK` | `true` runs the UI on fixtures with no backend; `false` uses the live API. | `true` |
| `NEXT_PUBLIC_AUTH_MODE` | `mock` (any email signs in), `dev` (live `/auth/token`), or `supabase` (OAuth). Defaults from `NEXT_PUBLIC_USE_MOCK`. | derived |
| `NEXT_PUBLIC_APP_STAGE` | Product stage badge + copy, decoupled from the data mode: `demo` \| `beta` \| `live`. `live` hides the badge. | `demo` (mock) / `beta` (live) |
| `NEXT_PUBLIC_AUTH_PROVIDERS` | Comma-separated OAuth providers shown on the login card (`google,github,gitlab`). | `google,github,gitlab` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL for the OAuth redirect (when `AUTH_MODE=supabase`). | *(empty)* |
| `NEXT_PUBLIC_PROJECT_ID` | Default project id used by the analysis/dashboard adapters. | `1` |
| `API_PROXY_TARGET` | Server-side rewrite target so the browser calls the web origin and Next forwards `/auth,/orgs,/projects,/ingest,/webhooks,/health` to the API (no CORS). Unset in production builds. | *(empty)* |

A typical live web build:

```bash
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_AUTH_MODE=dev
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

---

## Secure config (must change for production)

`assert_secure_config()` runs in the API lifespan (`api/app/config.py`) and, for
the `dev` auth provider, **refuses to start** if any of these are left at their
dev defaults:

```text
JWT_SECRET          must be a strong value (>= 32 chars), not "dev-insecure-change-me"
FERNET_KEY          must be set (required to encrypt stored Git tokens/secrets)
GIT_WEBHOOK_SECRET  must be a non-default value (not "dev-webhook-secret")
ADMIN_TOKEN         when set, must be at least 32 chars
```

Beyond those, change `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`,
`GITEA_ADMIN_TOKEN`, and the public URLs (`INGEST_BASE_URL`, `SURVEYS_DOMAIN`,
`SURVEYS_BASE_URL`, `WEB_BASE_URL`) before exposing the stack. Set
`SANDBOX_DB_SECRET` and a real `SANDBOX_NETWORK` if you want live analysis DB
access.

## See also

[[Cloud Deployment|Cloud-Deployment]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Cloud Quick Start|Cloud-Quick-Start]]
