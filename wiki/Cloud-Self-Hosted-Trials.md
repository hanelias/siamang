# Cloud Self-Hosted Trials

The self-hosted demo can grant prospects a real, end-to-end trial of the product
through **invite codes**. An operator mints codes (or redeem links); redeeming one
creates a fresh **Pro** organization that lives for a fixed number of days
(default 14). When the trial lapses the org is downgraded to Free immediately, and
a cleanup worker **hard-deletes** the org and its data after a short grace period.

This is a fully working, real-backend system: the invite/redeem flow, the
time-limited Pro plan, expiry enforcement + cleanup, operator tooling (admin API +
CLI), and the live-mode redemption UX are all wired and tested. Payments/Stripe and
the cloud (Supabase/Fly) architecture are out of scope here.

See also: [[Cloud Deployment|Cloud-Deployment]] (Scenario C) ·
[[Cloud Subscription Tiers|Cloud-Subscription-Tiers]] ·
[[Cloud Configuration|Cloud-Configuration]] ·
[[Cloud Authentication|Cloud-Authentication]].

---

## How it works

- **Redemption = quick signup.** A link `…/login?code=…` (or a manual code field)
  → a short form (email + name + password) → a fresh Pro-trial organization. The
  user keeps these credentials and can sign back in throughout the trial.
- **At expiry = hard delete.** Once `plan_expires_at` passes, the org collapses to
  the Free plan for access purposes; after the grace period the cleanup cron
  removes the trial org, its projects/data, its Gitea repos, and the owner account.
- **Code generation = admin-token API + CLI.** `POST /admin/invites` (header
  `X-Admin-Token`) and `scripts/make_invite.py` for `docker compose exec`.

### Trial-plan math

`api/app/services/invites.py` is the single home for the (pure) trial math:

- `effective_plan(org)` → the plan actually in force: a lapsed trial collapses to
  `"free"`.
- `days_left(org)` → whole days remaining (ceil), or `None` for a non-trial org.
- `is_expired(org)` → whether `plan_expires_at` is in the past.

`/auth/me` and the billing endpoint surface `plan_expires_at` and `days_left` per
membership so the UI can show a **"Pro trial · N days left"** pill.

---

## Data model (migration 009)

```sql
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ NULL;   -- NULL = permanent

CREATE TABLE IF NOT EXISTS invite_codes (
  id          BIGSERIAL PRIMARY KEY,
  code        TEXT UNIQUE NOT NULL,
  plan        TEXT NOT NULL DEFAULT 'pro',
  trial_days  INTEGER NOT NULL DEFAULT 14,
  max_uses    INTEGER NOT NULL DEFAULT 1,
  used_count  INTEGER NOT NULL DEFAULT 0,
  label       TEXT,
  expires_at  TIMESTAMPTZ,        -- the code's own validity window (optional)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`invite_codes` is intentionally **not** under RLS: it is a global, admin-managed
registry with no `org_id` (like `survey_registry`); the unguessable code is the
capability. See [[Cloud Data Model and Migrations|Cloud-Data-Model-and-Migrations]].

---

## Minting codes (operator)

Both paths reuse the same `invites.create_codes` service, so codes minted over
HTTP and over the CLI are identical.

**Admin API** (requires a non-empty `ADMIN_TOKEN`):

```bash
curl -s -X POST https://<api>/admin/invites \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"trial_days":14,"count":5,"label":"Acme Corp"}' | jq
```

**CLI on the VPS** (no HTTP, no token needed — runs inside the API container):

```bash
docker compose exec api python -m scripts.make_invite --days 14 --count 5 --label "Acme Corp"
# prints lines like: https://<demo-host>/login?code=TRIAL-7Q3K-9F2A
```

`make_invite` flags: `--plan` (default `pro`), `--days` (default
`TRIAL_DEFAULT_DAYS`), `--count`, `--max-uses` (default 1), `--label`, and
`--code-expires-days` (the code's own validity window, independent of trial
length).

Codes use a readable, unambiguous alphabet (no I/L/O/0/1), formatted like
`TRIAL-7Q3K-9F2A`. Each `InviteOut` carries a `redeem_url` built from
`WEB_BASE_URL`.

---

## The admin API

`api/app/routers/admin.py` (prefix `/admin`) is gated by a `require_admin`
dependency that checks the `X-Admin-Token` header against `settings.admin_token`,
using a constant-time comparison to avoid leaking the token via response timing:

```python
def require_admin(x_admin_token=Header(default=None, alias="X-Admin-Token")):
    if not settings.admin_token or not secrets.compare_digest(x_admin_token or "", settings.admin_token):
        raise HTTPException(403, "admin access denied")
```

> An **empty `ADMIN_TOKEN` disables the whole router** — every call 403s. The demo
> therefore ships closed by default until the operator sets a strong token (≥32
> chars; enforced by [secure-config](Cloud-Sandbox-and-Security#secure-config-enforcement-at-startup)).

Endpoints:

- `POST /admin/invites` → mint codes (`invites.create_codes`), returns
  `list[InviteOut]` with redeem links.
- `GET /admin/invites` → list codes with usage.

---

## Redemption flow

`POST /auth/redeem` (public, rate-limited) calls `invites.redeem`, which:

1. Fetches the code with a row lock; rejects with the right HTTP status if it is
   missing (404), past its `expires_at` (400), or already at `max_uses` (400).
2. Rejects a duplicate email with **409** (sign in instead — no account takeover).
3. Creates the `User` (Gitea-mirrored, password hashed) under a sanitized, unique
   handle, mirroring `/auth/register`.
4. Creates the org — `plan = code.plan`, `type = "cooperative"`,
   `plan_expires_at = now + trial_days` — with the user as `owner`, then creates
   the Gitea org. Platform rows are written first so a Gitea hiccup rolls the
   request back cleanly.
5. Consumes one use (`used_count += 1`) and returns a JWT (auto-login).

The prospect's experience: the link `…/login?code=…` opens a "Redeem your Pro
trial" step (code prefilled), they enter email + name + password, land in a fresh
Pro workspace with a **"Pro trial · Nd"** pill, and can sign out and back in until
expiry. After expiry, an access attempt returns **403** and the UI shows
"Trial ended — request a new code."

`POST /auth/redeem` is rate-limited per client IP (`REDEEM_RATE_LIMIT` /
`REDEEM_RATE_WINDOW`, default 10 / 60s) to deter code brute-forcing.

---

## Expiry & cleanup

A worker cron job, `cleanup_expired_trials` (`worker/app/tasks/cleanup.py`), runs
**every 30 minutes** (registered in `worker/app/settings.py` as
`cron(cleanup_expired_trials, minute={0, 30})`). For each org whose
`plan_expires_at` is past (beyond the `TRIAL_GRACE_DAYS` grace period, default 3):

1. **Gitea first:** delete the org's repos (an org can't be deleted while it owns
   repos), then the Gitea org, then the owner's Gitea user — but only if that owner
   has **no other org** (otherwise their Git access elsewhere would be revoked).
2. **Platform DB:** hard-delete the `organizations` row (FK cascade removes
   projects → deployments/runs/files/secrets and memberships), org-scoped rows
   without a cascading FK (webhooks, audit), and the owner `users` row.

All Gitea calls are best-effort, so a Gitea outage never wedges the cron; the DB
delete is the source of truth. Hard delete is irreversible — intended for demo
trials only.

---

## Enabling trials on a deploy

On top of a live backend (Scenario B in [[Cloud Deployment|Cloud-Deployment]]):

1. Set **`ADMIN_TOKEN`** (`openssl rand -hex 32`), **`WEB_BASE_URL`** (the public
   frontend URL), and optionally `TRIAL_DEFAULT_DAYS`. An empty `ADMIN_TOKEN`
   disables the admin API entirely.
2. Apply migration **009** (with the rest: `alembic upgrade head`).
3. The worker already runs the `cleanup_expired_trials` cron — no extra config.
4. Build the `web` image in **live mode** (`NEXT_PUBLIC_*` are inlined at build
   time): `NEXT_PUBLIC_USE_MOCK=false`, `NEXT_PUBLIC_AUTH_MODE=dev`,
   `NEXT_PUBLIC_API_BASE_URL=https://<api>`. The default stage is **beta**
   (Beta badge); set `NEXT_PUBLIC_APP_STAGE=live` for GA (badge hidden).
