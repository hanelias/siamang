# Cloud Web App

The siamang Cloud web app is a **Next.js** single-page application (in `web/`) that
puts the whole platform behind a browser UI: organizations and projects, a Git
repository browser with a Monaco code editor, deployments with live logs, a
response database, dashboards with charts, analysis runs, files, team and settings.
It is the wrapper over the Stage 1–4 API and can run either against a live backend
or entirely on in-memory fixtures.

---

## Stack

| | |
| :--- | :--- |
| Framework | **Next.js 16** (App Router), **React 19**, TypeScript — `output: "standalone"` |
| Editor | **Monaco** (`@monaco-editor/react`), self-hosted from `/public/monaco` (no CDN) |
| Charts | **recharts** (themed wrappers in `components/charts.tsx`) |
| Fonts | `geist` |
| Tests | **Playwright** smoke spec (`npm run e2e`) |

`next.config.js` sets `output: "standalone"`, disables production browser source
maps, applies baseline security headers (incl. a conservative CSP that locks down
framing/object/base-uri but leaves script/style/connect permissive for Monaco and
the configurable API origin), and — when `API_PROXY_TARGET` is set — rewrites
`/auth,/orgs,/projects,/ingest,/webhooks,/health` to the backend server-side so the
browser never makes a cross-origin call.

A server-side `middleware.ts` gates navigation on a lightweight presence cookie
(`sc_auth`): unauthenticated users are redirected to `/login`, authenticated users
never see `/login`. The bearer token itself is verified by the API; the cookie only
controls routing.

---

## Mock vs. live mode

The app runs in one of two **data modes**, selected by `NEXT_PUBLIC_USE_MOCK`:

- **mock** (`NEXT_PUBLIC_USE_MOCK=true`, the default) — every screen runs on
  fixtures with no backend. Data lives in browser memory / `localStorage`; CRUD
  (create/revoke/delete) mutates in-memory copies so the demo behaves like the real
  thing. This is the frontend-only demo (Scenario A in
  [[Cloud Deployment|Cloud-Deployment]]).
- **live** (`NEXT_PUBLIC_USE_MOCK=false`) — calls the real API at
  `NEXT_PUBLIC_API_BASE_URL` (or relative paths through the Next proxy).

Screens never branch on mock-vs-live themselves. They go through one adapter,
`web/lib/platform.ts`, which exposes a single `platform` object whose every method
does `if (USE_MOCK) … else api.…`. The fixtures live in `web/lib/mock.ts`; the raw
HTTP client is `web/lib/api.ts`. Auth has its own seam, `web/lib/auth.ts`, with
three backends selected by `NEXT_PUBLIC_AUTH_MODE` (`mock` — any email signs in;
`dev` — `POST /auth/token` → JWT then `GET /auth/me`; `supabase` — OAuth redirect).

A separate **product stage** (`NEXT_PUBLIC_APP_STAGE` = `demo` | `beta` | `live`)
drives the stage badge and copy, decoupled from the data mode, so a live backend
can run as an invite-only beta or as GA (which hides the badge).

---

## The shell

After login, `components/app.tsx` renders the shell: a top bar (org chip with a
plan / "Pro trial · Nd" pill, theme toggle, user menu) and a sidebar that switches
between **organization** screens and **project** screens. Project navigation is
consolidated to **Repository · Database · Deployments · Analysis · Dashboard ·
Connectors · Files · Settings**; organization-level destinations are **Projects ·
Team · Organizations · Organization settings · Profile**. The document title
reflects the current screen and scope.

---

## Screens

### Organizations
The org workspace page. One organization per user: shows the org with its type
(`personal`/`cooperative`), the viewer's role, the current plan (and a trial pill),
and the "name / upgrade to cooperative" flow. Owners/admins manage it from here.

### Projects
The org's project list and project creation (with templates, e.g. the seeded
**example** study). Cards show status and response counts; the create action is
disabled with an upgrade prompt when the plan's project cap is reached
(`capOf` from `lib/plans.ts`). A brand-new live user with no org sees a clear empty
state rather than demo data.

### Repository
The Git repository browser: a file tree, a **Monaco** editor keyed by file type
(`.py` → Python, `.yaml` → YAML, `.md` → Markdown) with a commit-status badge and
**Save & commit** (Ctrl/Cmd+S), a branch switcher, clickable breadcrumbs, the
commits list for the branch, commit **diffs** (Monaco diff), **Pull requests**
(create/merge), and **Connect locally** (clone over HTTP/SSH). Markdown/`.md`
reports render in place (Preview/Source) with MD/HTML download.

### Deployments
The deployments list (status / URL / commit / environment) with **Deploy** and
**Stop**, live deploy logs streamed over **SSE** (with a polling fallback), and the
fieldwork **monitor** on each card: collection **stats** (collected N / max + %,
last response), **quota** progress bars, and the variable **codebook**.

### Analysis
The analysis workspace: the list of scripts declared in `siamang.yaml` with
**Run ▶** / **Run all ▶**, and run history with per-run **Logs** and **Outputs**
tabs. **Schedules** (cron runs) live here behind the `schedules` plan gate.

### Database
Browse a project's tables. A **Data** tab (paginated, sortable preview rows) and a
**Schema** tab (column metadata), plus **export** to CSV/XLSX/SAV/Parquet/SQLite and
single-response **delete** (GDPR erasure).

### Dashboard
Server-side **data insights** over the full responses table (in mock mode the same
shapes are computed client-side via `lib/aggregate.ts`): a respondent **summary**
(responses, respondents, duplicates, partials), a **responses-per-day** area chart,
**frequency** bars for a chosen variable, and a two-way **crosstab**. Also shows a
deployment summary and an "Edit README" shortcut into Repository.

### Files
Project files in two groups: **repository outputs** (reports / generated tables
tracked in the repo tree) and **assets** (uploads/exports that don't live in Git),
with upload and download.

### Team
The org's members and their roles, with an empty state and a clear CTA to manage
membership in Organization settings.

### Settings (project)
Per-repository **Project settings** with tabs: **General**, **Runtime** (the
`siamang.yaml` Python version + curated packages), **Secrets** (write-only
per-project secrets), **Git** (SSH keys, branch protection), **Git mirrors**
(push/pull to GitHub/GitLab — a Pro feature), and **Danger Zone**.

### Organization settings
Org-level tabs: **General**, **Members**, **Billing** (plan catalogue + checkout;
in the beta the plan switches without payment, with a "Coming soon" badge on
checkout), **Integrations** (Webhooks + the webhook delivery journal; **SSO** with
a "Coming soon · Corporate" badge), and **Activity** (the audit feed).

### Connectors
A catalog of available connector targets (S3, GCS, Azure, BigQuery, Snowflake,
Sheets, BYO-DB) plus the connectors declared in the project. Gated by the
`connectors` plan feature and marked **"Coming soon"** — live transfer is deferred.
See [[Cloud Connectors|Cloud-Connectors]].

### Profile
Per-user account settings with tabs: **Account**, **Security** (password change),
**Appearance** (theme), **API keys** (`sck_…` personal tokens — shown once), and
**SSH keys**.

---

## The Monaco editor

`components/monaco-editor.tsx` wraps Monaco, loaded client-only (it needs `window`)
and **self-hosted from `/public/monaco`** so the editor works with no CDN access —
no webpack/Turbopack plugin to configure. A `monacoLang` helper maps a file's
stored language or extension to a Monaco language id (`python`, `yaml`, `markdown`,
`json`, else `plaintext`). The editor is configured for code (4-space tabs, no
minimap, line numbers, column selection, themed via the app's CSS variables and the
dark/light theme).

---

## Charts

`components/charts.tsx` holds thin recharts wrappers themed via the app's CSS
variables, so screens never import recharts directly and the chart style stays
uniform: `FreqBars` (horizontal frequency bars with count + percent) and
`ResponsesArea` (a responses-per-day area chart). Both are used by the Dashboard.

---

## Running it

In mock mode (no backend):

```bash
cd web
npm install
npm run dev        # http://localhost:3000 ; log in at /login with any email
```

For a live backend, set `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_BASE_URL`
(or use the Next proxy via `API_PROXY_TARGET`). The full local run is in
[[Cloud Quick Start|Cloud-Quick-Start]]; deployment options are in
[[Cloud Deployment|Cloud-Deployment]].

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] (how to run it) · [[Cloud REST API|Cloud-REST-API]] · [[Cloud Configuration|Cloud-Configuration]] · [[Cloud Deployment|Cloud-Deployment]]
