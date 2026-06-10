# Cloud Deployment

This page covers how to deploy siamang Cloud — from a zero-backend frontend demo
to a full self-hosted stack to a production SaaS topology. The first thing to
understand, before choosing a platform, is that the product has two halves with
very different hosting needs.

| Part | What it is | Where it deploys |
| :--- | :--- | :--- |
| **Frontend** (`web/`) | Next.js app; runs **on fixtures** with no backend (`NEXT_PUBLIC_USE_MOCK=true`) | Vercel / Netlify / Cloudflare Pages / any Node host |
| **Backend** (`api/`, `worker/`, Gitea, Postgres, Redis, MinIO, nginx) | Docker stack; the worker launches **sandbox containers via the host Docker socket** | A Docker host / VPS only (Coolify, Fly, your own server) — **not** Vercel/Netlify |

> **Vercel and Netlify host only the frontend.** The backend cannot run there: it
> needs a live Docker daemon (for the sandbox), persistent services
> (Postgres/Redis/Gitea/MinIO), and a long-running worker — none of which are
> serverless. For the backend, use a VPS.

---

## Scenario A — frontend-only demo (mock mode)

The simplest, most reliable "make the demo work" path. **No backend needed** — the
whole UI is clickable on fixtures (projects, repository with Git features,
database, deployments, analysis, dashboard, connectors, settings, plan gating).
Data lives in the browser's `localStorage`.

- **Login:** at `/login`, any email (any password) → a demo workspace.
- **App root is the `web/` directory.** You need a host that supports Next.js
  middleware (Vercel/Netlify/Cloudflare/Node); a pure static export (GitHub Pages)
  will not work.

### Vercel

1. Import Project → select the repository.
2. **Root Directory: `web`** (required).
3. Framework preset auto-detects as **Next.js**.
4. Set `NEXT_PUBLIC_USE_MOCK = true` (already the default; pin it explicitly).
5. Deploy → open the URL → `/login` → any email.

```bash
cd web
npx vercel        # preview
npx vercel --prod
```

### Netlify

New site from Git → **Base directory: `web`**, build command `npm run build` (the
official `@netlify/plugin-nextjs` attaches itself for Next.js). Set
`NEXT_PUBLIC_USE_MOCK = true`.

### Cloudflare Pages

Framework preset Next.js; root/build directory `web`; built via
`@cloudflare/next-on-pages`. Set `NEXT_PUBLIC_USE_MOCK = true`.

### Docker (Railway / Render / Fly / any) — frontend container

The repo ships `web/Dockerfile` (standalone, listens on port 3000):

```bash
cd web
docker build -t siamang-demo .
docker run -p 3000:3000 -e NEXT_PUBLIC_USE_MOCK=true siamang-demo
# http://localhost:3000
```

Railway works for the mock demo (it injects `$PORT`, which Next standalone reads):
set Root Directory `web` and `NEXT_PUBLIC_USE_MOCK = true`. It is **not** suitable
for the live backend (no host Docker socket for the sandbox, no shared surveys
volume) — see Scenario B.

**Demo environment variables:**

| Variable | Value | Why |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_USE_MOCK` | `true` | run on fixtures, no backend |
| `NEXT_PUBLIC_AUTH_MODE` | *(unset)* | mock mode auto-logs in any email |
| `NEXT_PUBLIC_API_BASE_URL` | *(unset)* | only used in live mode |

---

## Scenario B — full stack on a VPS (Docker Compose)

Here real Gitea/Postgres/Redis/MinIO, the sandbox, and response collection all
work. The backend runs on a **VPS with Docker**; the frontend runs there too (as a
container) or on Vercel/Netlify pointed at the API.

### The compose services

`docker-compose.yml` defines the full stack (base images pinned; restart policies,
resource limits, and capped logs on every long-running service):

| Service | Image / build | Role |
| :--- | :--- | :--- |
| `postgres` | `postgres:15.8` | Platform DB + per-project schemas; volume `pgdata` |
| `redis` | `redis:7.4.1` | ARQ task queue |
| `gitea` | `gitea/gitea:1.21` | Git hosting; volume `gitea` |
| `minio` | `minio/minio` | Object storage (outputs, reports, assets); volume `minio` |
| `api` | built from repo root, `api/Dockerfile` | FastAPI app; runs migrations on start |
| `worker` | `./worker` | ARQ worker; mounts `/var/run/docker.sock` + the `surveys` volume |
| `nginx` | `nginx:1.27.2` | Serves built survey bundles read-only from the `surveys` volume |
| `web` | `./web` | Next.js app (proxies to `api` via `API_PROXY_TARGET`) |

The same compose file is deployed in production by Coolify; Coolify/Cloudflare
terminate TLS in front. Ports are bound to `127.0.0.1` so a reverse proxy fronts
them: API `:8000`, Web `:3001`→3000, Gitea `:3000`, MinIO `:9000`/console `:9001`,
surveys (nginx) `:8080`.

### Server requirements

- A VPS with Docker + docker compose (e.g. Hetzner CX22+; for the sandbox and
  builds, **≥ 2 vCPU / 4–8 GB**).
- DNS pointing at the server, with subdomains for app / api / gitea / surveys.

> **Why not Railway / serverless / Cloud Run for the backend:** two stack
> requirements break on platforms without host Docker and shared volumes:
> 1. the `worker` runs untrusted code in **sandbox containers via
>    `/var/run/docker.sock`** — absent there, so validate/deploy/run_script don't
>    work;
> 2. `worker` → `nginx` share the **`surveys` volume** for published bundles —
>    no shared cross-service volume on those platforms.

### B-1 (recommended) — Coolify on a VPS

The "standard" production path from the design: Coolify deploys the same
`docker-compose.yml`, and `git push` triggers a rebuild.

1. Install Coolify on the VPS, connect the repository.
2. New Resource → **Docker Compose** → point at `docker-compose.yml`.
3. Fill the secrets as **Environment** (Coolify stores them instead of `.env`).
4. Bind domains to `web` (3000), `api` (8000), `gitea` (3000),
   `nginx`/surveys (80), `minio` (9001). Cloudflare provides TLS.
5. Deploy. Coolify builds the `api`/`worker`/`web` images and brings the stack up.

### B-2 — manual on a VPS

```bash
git clone <repo> && cd siamang_cloud
cp .env.example .env
# fill in the secrets. Generate keys:
#   FERNET_KEY:        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   JWT_SECRET:        openssl rand -hex 32
#   SANDBOX_DB_SECRET: openssl rand -hex 32
docker compose up -d --build
# first-time init (migrations + Gitea admin + token + bucket) is easiest via:
bash scripts/dev_up.sh          # idempotent; fix domains/TLS for prod afterward
```

> **Critical for the sandbox:** `worker` mounts `/var/run/docker.sock` and runs
> sandbox containers on the **host** Docker daemon (validating/building/analyzing
> untrusted code). The backend must live on a machine with a reachable Docker
> daemon — this is precisely why serverless platforms don't work.

### Wiring the frontend to a live API

Two options:

**(a) Single origin via Next's server-side proxy (no CORS, recommended).** Build
`web` with:

```bash
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=          # empty → relative paths
API_PROXY_TARGET=http://api:8000   # server-side rewrite to the API
```

The browser hits the web origin and Next forwards `/auth,/orgs,/projects,/ingest,/webhooks,/health`
to the API. Ideal when web and api share a network (Coolify/compose).

**(b) Direct API calls (needs CORS + a public API).**

```bash
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

Then configure CORS on the API for the frontend's origin. On Vercel/Netlify only
option (b) applies (frontend there, API on the VPS).

### First login (live)

There are no default users. Register one, then sign in at `/login`:

```bash
curl -s -X POST https://api.your-domain.com/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@org.com","name":"you","password":"<strong>"}'
```

Registration creates a mirrored Gitea user and encrypts its token (requires valid
`FERNET_KEY` and `GITEA_ADMIN_TOKEN`).

> For invite-code Pro trials on top of this scenario, see
> [[Cloud Self-Hosted Trials|Cloud-Self-Hosted-Trials]].

### Codespaces / local-dev overlay

`docker-compose.codespaces.yml` overlays the base file for Codespaces and local
dev: it initializes Gitea non-interactively (no web installer), allows Gitea to
deliver webhooks to the private `api` host (`GITEA__webhook__ALLOWED_HOST_LIST: "*"`),
and sets a shared `TMPDIR` (`/tmp/sandbox-work`) bind-mounted identically on host
and worker so the Docker-out-of-Docker bind mounts resolve correctly.

```bash
docker compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d
```

---

## Scenario C — production SaaS (Supabase + Vercel + Fly.io)

The multi-tenant production blueprint maps the stack onto three platforms and
resolves the two things that block a non-VPS deploy (the sandbox over `docker.sock`
and the shared `surveys` volume).

**Three platforms:**

1. **Supabase** — Postgres (with RLS), object storage (S3-compatible), optionally
   Auth.
2. **Vercel** — the `web` frontend.
3. **Fly.io** — `api`, `gitea`, `redis`, `survey-host` as long-running apps, and a
   `worker` that launches **Fly Machines** (Firecracker micro-VMs) per job instead
   of using the host Docker socket.

Pin all Fly apps to one region near your Supabase project (the edit→commit→validate
loop and the DB are chatty).

### The two structural changes vs. compose

1. **Sandbox: `docker.sock` → Fly Machines API.** Introduce a `SandboxDriver` seam
   with two implementations — `DockerDriver` (local/VPS) and `FlyMachinesDriver`
   (prod, `create → start → wait → destroy` a micro-VM from the same
   `SANDBOX_IMAGE` per task). The job contract is unchanged; sandbox Machines get
   no platform secrets, restricted egress (`SANDBOX_NETWORK`), and a hard timeout.
   Firecracker gives VM-level isolation — stronger than the shared-kernel
   Docker-socket model.
2. **Surveys: shared volume → object storage.** Fly volumes are per-Machine, so the
   worker **uploads** the built bundle to object storage (Supabase Storage / R2)
   and `survey-host` (a Fly app or a CDN) **serves** bundles from it. Put
   Cloudflare in front (`SURVEYS_DOMAIN` / `SURVEYS_BASE_URL`) so respondent
   traffic is CDN-cached.

Everything else (Postgres, Redis, Gitea, CORS, env) is configuration — reuse the
[[Cloud Configuration|Cloud-Configuration]] reference, pointing each value at its
production target (e.g. `MINIO_*` → the Supabase Storage S3 endpoint and keys).

### Fly.io specifics

- **Apps:** `api`, `gitea`, `redis`, `survey-host`, `worker` — each its own
  `fly launch`.
- **Private networking (6PN):** apps reach each other at `‹app›.internal`; use
  **Flycast** (`‹app›.flycast`) for private load-balanced access to
  `api`/`gitea`/`redis` so they need no public IP.
- **Public ingress:** only `api` (HTTPS), `survey-host` (HTTPS), and `gitea` SSH.
- **Volumes:** `gitea` and `redis` are each a single Machine + a Fly volume.
- **Secrets:** `fly secrets set …` per app (DSNs, tokens, `FERNET_KEY`,
  `JWT_SECRET`, S3 keys, and `FLY_API_TOKEN` for the worker to drive Machines).

### Auth options

- **Minimal (recommended to start):** Supabase = Postgres + Storage only; keep the
  API's built-in auth (`/auth/register`, `/auth/token`, `JWT_SECRET`), with
  frontend `AUTH_MODE=dev`. No code change.
- **Full social login:** Supabase Auth (`NEXT_PUBLIC_AUTH_MODE=supabase`); the
  API's verifier seam (`api/app/auth/verifier.py`) must verify Supabase JWTs.

### RLS + pooling (important)

The API sets per-request tenant context for RLS (`SET LOCAL app.current_org`
inside the transaction). Use Supabase's **session pooler or a direct connection**
for the API; the transaction pooler is only safe because the org context is set
*locally inside the transaction* — verify before switching to it.

### Scaling shape

Respondents (filling surveys) are CDN-served and cheap. Authors drive cost: each
deploy/analysis is one sandbox Machine billed per-second while running — ideal for
bursty per-tenant load. Always-on small Machines: `api`, `gitea`, `redis`,
`survey-host`.

---

## The survey static host (nginx)

Deployed survey bundles are written by the worker to the shared `surveys` volume at
`/srv/surveys/<org>/<project>/<slug>/` and served read-only by nginx
(`survey_host/nginx.conf`). TLS and the `surveys.<domain>` host are terminated by
Coolify (Traefik) / Cloudflare in front; nginx still sends baseline security
headers (`X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`,
`Referrer-Policy`, `Strict-Transport-Security`). Routing serves each bundle's
`index.html` as the SPA fallback, long-caches fingerprinted assets (`max-age=31536000, immutable`),
leaves the HTML entry uncached, and exposes `/healthz`.

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Cloud Configuration|Cloud-Configuration]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Cloud Self-Hosted Trials|Cloud-Self-Hosted-Trials]]
