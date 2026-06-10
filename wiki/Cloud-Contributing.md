# Cloud Contributing

This page covers the branching workflow, local development setup, and the code
style / tooling used for `siamang_cloud`.

---

## Branching workflow

The rules (from `BRANCHES.md`) exist to keep branches from sprawling:

- **`main` is the single source of truth** — the consolidated snapshot of all work
  plus the latest fixes. Develop against it and merge back into it.
- **`claude/*` branches are ephemeral session branches** (one per Claude Code on
  the web session). Delete them once their PR merges.
- **Never force-push or rewrite `main`'s history.** A past reset/force-push to a
  fresh, flattened history orphaned every open branch from `main` (no common
  ancestor), which is the root cause of the historical "many disconnected
  branches" mess. Land changes as ordinary commits/merges so branches keep a
  common ancestor.

### Going forward

1. `main` is protected and canonical; all work merges into it, nothing else is
   long-lived.
2. Do not rewrite `main`'s history (no force-push, no reset-to-new-root).
3. Branch off `main` for every change. Claude Code on the web does this
   automatically (`claude/<name>`); for manual work use `feature/<short-topic>` or
   `fix/<short-topic>`.
4. Keep branches short-lived and single-purpose — don't stack a new session on top
   of an unmerged branch; start from `main`.
5. Delete the branch once its PR merges.

### Recommended GitHub settings

- **Settings → General → Automatically delete head branches → ON** (prunes merged
  PR branches; prevents most sprawl on its own).
- **Settings → Branches → branch protection for `main`:** require a pull request
  before merging (no direct pushes), require status checks to pass (the CI in
  `.github/workflows/`), and do not allow force pushes.

> Branch deletion is blocked from the web execution sandbox, so retire stale
> `claude/*` branches locally (`git push origin --delete <branch> …`) or via the
> GitHub branches UI.

---

## Local development setup

The full stack runs locally with Docker Compose. The fastest path is the bootstrap
script, which is idempotent:

```bash
git clone <repo> && cd siamang_cloud
cp .env.example .env
# fill in the secrets (generate keys — see Cloud Configuration), then:
bash scripts/dev_up.sh
```

`dev_up.sh` generates secrets into `.env`, starts postgres/redis/gitea/minio, runs
the migrations, mints a Gitea admin token, creates the MinIO bucket, builds the
sandbox image, and starts api + worker + nginx. For Codespaces/local dev, layer the
overlay so Gitea initializes non-interactively and can deliver webhooks to the
private `api` host:

```bash
docker compose -f docker-compose.yml -f docker-compose.codespaces.yml up -d
```

For frontend-only work you don't need the backend at all — run the web app on
fixtures:

```bash
cd web
npm install
npm run dev        # http://localhost:3000, NEXT_PUBLIC_USE_MOCK defaults to true
```

See [[Cloud Quick Start|Cloud-Quick-Start]] for the full local run and
[[Cloud Configuration|Cloud-Configuration]] for the environment variables.

---

## Code style & tooling

The repo is split into independently tooled components: `api/`, `worker/`,
`siamang_cloud_engine/`, `sdk/`, and `web/`.

**Python** (`api`, `worker`, plugin, SDK):

- **ruff** for linting and formatting — `ruff check .` and `ruff format --check .`.
- **mypy** for type checking — `mypy api/app` and `mypy worker/app`.
- **pytest** for tests, run from the component directory with `PYTHONPATH=.`
  (e.g. `PYTHONPATH=api pytest api/tests`).
- New code is fully type-annotated (`from __future__ import annotations`), and
  service modules favor pure, dependency-free logic behind thin seams so the
  service-dependent side can be mocked (see the development philosophy in
  [[Cloud Roadmap|Cloud-Roadmap]]).

**Web** (`web/`):

- TypeScript + Next.js; `npm run lint` and `npm run build` (the build also
  type-checks). `npm run e2e` runs the Playwright smoke spec.

**The full local gate** before opening a PR (mirrors CI):

```bash
ruff check . && ruff format --check . && mypy api/app && mypy worker/app && \
  PYTHONPATH=api pytest api/tests && PYTHONPATH=worker pytest worker/tests && \
  (cd siamang_cloud_engine && pytest tests) && (cd sdk && pytest) && \
  (cd web && npm run lint && npm run build)
```

Then bring up the stack and run `scripts/e2e_smoke.sh` for the live end-to-end
check. CI runs all of this plus the migrations apply/rollback and image builds —
see [[Cloud CI CD and Testing|Cloud-CI-CD-and-Testing]].

---

## Commits & pull requests

- Keep each branch single-purpose and open a PR into `main`.
- CI must be green: lint, types, all test suites, migrations, the web build, both
  smoke jobs, and the image builds.
- Delete the branch after the PR merges.

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Cloud CI CD and Testing|Cloud-CI-CD-and-Testing]] · [[Cloud Architecture|Cloud-Architecture]]
