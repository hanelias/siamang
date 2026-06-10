# Cloud Subscription Tiers

The siamang **engine is open source**; siamang **Cloud** is the managed, hosted
product that monetizes the infrastructure and a set of premium capabilities on top
of the open engine. Subscriptions therefore cover the *Cloud* — hosting, resource
limits, and gated features. There are four tiers: **Free**, **Plus**, **Pro**, and
**Corporate**.

> **Single source of truth.** The plan matrix is defined in the backend and
> mirrored by the UI:
> - Caps & feature flags: `api/app/services/limits.py`
> - Prices & catalogue: `api/app/services/billing.py`
> - UI mirror used for client-side gating: `web/lib/plans.ts`
>
> The values below are taken from `limits.py` (the authoritative source). Where
> the prose docs differ, see the [note on the AI feature](#a-note-on-the-ai-assistant).

---

## Plans at a glance

| | **Free** | **Plus** | **Pro** | **Corporate** |
| :--- | :--- | :--- | :--- | :--- |
| **Price / month** | $0 | $49 | $299 | Custom — contact sales |
| **Checkout** | Self-serve | Self-serve | Self-serve | Sales-assisted |
| **Projects (repositories)** | 2 | 10 | Unlimited | Unlimited |
| **Team members** | 2 | 15 | Unlimited | Unlimited |
| **Responses per project** | 500 | Unlimited | Unlimited | Unlimited |
| **Webhooks** | — | ✓ | ✓ | ✓ |
| **Schedules (cron runs)** | — | ✓ | ✓ | ✓ |
| **Connectors & Git mirrors** | — | — | ✓ | ✓ |
| **SSO (SAML / OIDC)** | — | — | ✓ | ✓ |
| **Self-hosted deployment** | — | — | — | ✓ |
| **Core platform** (repos, deploys, database, analysis, reports, API keys) | ✓ | ✓ | ✓ | ✓ |

`Unlimited` is represented in code as "no cap" (`None`). Prices come from
`PLAN_PRICE_CENTS` in `billing.py` (`free=0`, `plus=4900`, `pro=29900`,
`corporate=None`).

---

## What every plan includes (core platform)

All tiers — including **Free** — get the complete research-as-code product; Free
is a genuinely useful, capped funnel rather than a crippled trial. Core
capabilities on every plan:

- **Git-backed repositories** — author surveys as code; commit, branch, open and
  merge pull requests; every commit runs validation and reports a status.
- **Repository dashboard** — per-repo overview (README, status, recent commits,
  latest deployment).
- **Deployments** — publish a survey to an environment, get a hosted survey URL,
  collect responses.
- **Response database** — browse responses, view table schemas, export to
  CSV/XLSX/SAV/Parquet/SQLite.
- **Analysis & reports** — run analysis scripts and generate reports (Markdown /
  HTML; PDF planned).
- **Files** — repository outputs plus uploaded assets and exports.
- **Team** — invite members and assign roles (`owner` / `admin` / `member`).
- **Developer access** — personal API keys (`sck_…` bearer tokens) and SSH keys.
- **Project settings** — runtime (`siamang.yaml`), project secrets, branch
  protection.

The premium features below are additions on top of this core.

---

## Premium features (gated by plan)

Each feature is a flag in `limits.py`. Using a gated feature on a plan that lacks
it returns **HTTP 402 (upgrade required)** via `require_feature` →
`FeatureRequired`, and the UI surfaces an upgrade prompt instead of a dead end.

| Feature flag | Tiers | What it unlocks |
| :--- | :--- | :--- |
| `FEATURE_WEBHOOKS` | Plus, Pro, Corporate | Outgoing, HMAC-signed `POST` notifications on terminal events (`deploy.live`/`deploy.failed`, `run.completed`/`run.failed`). A Slack incoming-webhook URL works directly. |
| `FEATURE_SCHEDULES` | Plus, Pro, Corporate | Cron-scheduled automation: run an analysis script or a full "run-all" on a schedule. |
| `FEATURE_CONNECTORS` | Pro, Corporate | Data connectors (S3, GCS, Azure, BigQuery, Snowflake, Sheets, BYO-DB) **and** Git mirrors (push/pull to GitHub/GitLab). See [[Cloud Connectors\|Cloud-Connectors]]. |
| `FEATURE_SSO` | Pro, Corporate | Enterprise SAML / OIDC configuration for the org. The config surface is available on Pro+; enforced sign-in lands with the live identity integration. |
| `FEATURE_SELF_HOSTED` | Corporate only | Entitlement to run siamang Cloud on your own infrastructure (data-residency / control). |

The exact `PLAN_TIERS` definition (from `limits.py`):

```python
PLAN_TIERS = {
    "free":      PlanLimits(max_projects=2,    max_members=2,    max_responses_per_project=500,  features=frozenset()),
    "plus":      PlanLimits(max_projects=10,   max_members=15,   max_responses_per_project=None, features={WEBHOOKS, SCHEDULES}),
    "pro":       PlanLimits(max_projects=None, max_members=None, max_responses_per_project=None, features={WEBHOOKS, SCHEDULES, CONNECTORS, SSO}),
    "corporate": PlanLimits(max_projects=None, max_members=None, max_responses_per_project=None, features={WEBHOOKS, SCHEDULES, CONNECTORS, SSO, SELF_HOSTED}),
}
```

### A note on the AI assistant

The `FEATURE_AI` flag still exists, but **AI was removed from the product for
beta-2**. It is *not* included in any plan's `features` set in `limits.py` (or in
the UI mirror `plans.ts`), so the assistant endpoint answers **HTTP 402 on every
plan** rather than 404-ing old clients. The `docs/SUBSCRIPTION_TIERS.md` prose and
the reference `plan_tiers` table (migration 005) still list `ai` as a Plus+
feature, but those are stale relative to the authoritative `limits.py`.

---

## Limits & enforcement

| Limit | Free | Plus | Pro | Corporate | Where enforced |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Projects** | 2 | 10 | ∞ | ∞ | `check_projects` → project creation (`projects.py`) |
| **Team members** | 2 | 15 | ∞ | ∞ | `check_members` → member invite (`orgs.py`) |
| **Responses / project** | 500 | ∞ | ∞ | ∞ | `response_cap` → response ingest (`ingest_service.py`) |

- **Projects / members:** exceeding the cap returns **HTTP 402**; the UI disables
  the action and links to Billing.
- **Responses:** the effective per-survey cap is the **tighter** of the plan cap
  and the survey's own `max_responses` (set in `siamang.yaml`). `response_cap`
  returns `min(plan_cap, survey_max)`, or `None` (unlimited) if neither applies.
  On Free a survey stops accepting responses at 500.

`limits.py` is intentionally pure (no DB, no services), so it can be unit-tested
and called from any router. The `plan_tiers` table (migration 005) mirrors these
defaults for ops visibility / future per-org overrides (wired later).

---

## Billing: stub vs live

Billing is a pure, dependency-free seam (`api/app/services/billing.py`) selected
by the `BILLING_PROVIDER` setting:

- **`stub`** (default) — a checkout applies the chosen plan **immediately, with no
  payment**. `checkout_url` returns a placeholder
  (`https://billing.stub.local/checkout?...`). This is what the beta and demo run
  on; the UI shows honest "in the beta, the plan switches without payment" copy
  and a "Coming soon" badge on checkout.
- **live (Stripe)** — real hosted Checkout sessions + webhooks are wired behind
  the same interface in the Service Integration stage, using `STRIPE_SECRET_KEY`
  and `STRIPE_WEBHOOK_SECRET`.

`available_plans()` returns the catalogue (plan, price, sorted features) for the
billing UI. `SELF_SERVE_PLANS = ("free", "plus", "pro")` — only those can be
selected from **Organization settings → Billing**; `corporate` is sales-assisted
("Contact sales").

---

## Subscription vs. team roles vs. org type

Three independent dimensions control access — don't conflate them:

1. **Subscription tier** (this page) — *what the organization can do* (caps +
   premium features). Bought by the owner; applies org-wide. Only the **owner**
   can purchase, change, or cancel it. Cancelling returns the org to **Free**.
2. **Team role** — *who within the org can do what*: **owner** (full control incl.
   billing, org type, SSO), **admin** (manage profile/members, create projects,
   branch protection, integrations), **member** (contribute: edit code, run
   analysis, deploy, manage secrets).
3. **Organization type** — **personal** (solo workspace, no team invitations) or
   **cooperative** (can invite teammates and manage roles). Independent of the
   tier; switching a cooperative back to personal removes all members except the
   owner.

## See also

[[Cloud Self-Hosted Trials|Cloud-Self-Hosted-Trials]] · [[Cloud Connectors|Cloud-Connectors]] · [[Cloud Configuration|Cloud-Configuration]]
