# Cloud Overview

**siamang Cloud** is a managed (and self-hostable) *research-as-code* platform
built on top of the open-source [[Core Concepts|Core-Concepts]] engine. A survey
is a Git-backed project: you version the questionnaire and analysis as code,
deploy it as a live survey, collect responses into managed storage, and run
scheduled analysis with reproducible reports — all in one place.

## What it is

Sociological and marketing research is usually fragmented: the questionnaire is
built in one tool, data lives in another, cleaning and analysis happen in
Excel/SPSS/R on someone's laptop, and reports end up somewhere else. Six months
later it is nearly impossible to reconstruct *how* a study was built, what data
was collected, how it was cleaned, and which tables were produced.

siamang Cloud unifies the whole research lifecycle behind a model best described
as **"a specialized GitLab + survey deployment + managed data storage"**:

- **Repository** — the questionnaire and its logic as code, versioned through
  Git. Every push is validated automatically.
- **Deployments** — one-click publish of a survey to a public URL.
- **Database** — managed PostgreSQL storage for responses, readable by analysts.
- **Analysis** — data analysis through Python scripts with a full run history and
  their outputs.
- **Files & Reports** — survey assets and generated report artifacts (Markdown /
  HTML), downloadable from object storage.

Under the hood, all the domain functionality (questionnaire model, validation,
compilation to a web bundle, reporting, SPSS/Excel/Stata I/O) already lives in
the `siamang` engine. **siamang Cloud is the platform shell around the engine**:
multi-user, multi-tenant, with Git hosting, deployment orchestration, and data
storage. The engine is consumed through its public extension points so it can be
upgraded as a normal pip dependency.

## How it relates to the Library

The `siamang` Python package (the **Library** side of this wiki) is the engine:
you can use it entirely on your own laptop — define a survey, validate, simulate,
deploy to SQLite/Supabase, and analyze. siamang Cloud takes that same engine and
adds the surrounding platform:

| Concern | Library (`siamang`) | Cloud (`siamang_cloud`) |
| :--- | :--- | :--- |
| Survey definition | Python module | The same Python module, in a Git repo |
| Validation | `siamang validate` locally | Automatic on every `git push` (sandboxed) |
| Deployment | `siamang deploy` to your own backend | One-click managed deploy + hosted survey |
| Data storage | Local SQLite / your Supabase | Managed, multi-tenant PostgreSQL |
| Analysis | Run scripts locally | Hosted runs, schedules, run history, reports |
| Collaboration | Git / files you manage | Organizations, roles, audit, team access |

If you are new, read [[Core Concepts|Core-Concepts]] first to understand the
research-as-code model, then come back here.

## Who it is for

- **Research / marketing agencies** running repeated studies that need
  versioning, reproducibility, and a single source of truth.
- **Project managers** who create projects, deploy surveys, and manage the team.
- **Methodologists / survey programmers** who author the questionnaire, variables,
  and project config as code.
- **Analysts** who read collected data, write cleaning scripts, and build tables,
  charts, and reports.
- **Respondents** — external users who take a survey via its public URL with no
  account required.

## The value

- **Reproducible** — the questionnaire, the deployed version, the collected data,
  the analysis scripts, and every run output all live together and are versioned.
- **Managed** — no servers to wire up for collection: deploy, get a URL, and
  responses flow into isolated per-project storage.
- **Multi-tenant and secure** — each tenant is isolated by a per-project Postgres
  schema plus Row-Level Security; user code only ever runs in an ephemeral,
  network-isolated sandbox.
- **Open core** — the engine is open-source; the Cloud platform is what adds
  managed infrastructure, team collaboration, and premium features. It can also
  be self-hosted from a single `docker-compose.yml`.

## Where to go next

- [[Cloud Architecture|Cloud-Architecture]] — the monorepo, the layers, and the
  end-to-end data flow.
- [[Cloud Quick Start|Cloud-Quick-Start]] — run the whole stack locally with
  Docker.
- [[Cloud Domain Model|Cloud-Domain-Model]] — organizations, projects, runs, and
  how they relate.
- [[Cloud REST API|Cloud-REST-API]] — every endpoint, grouped by router.

## See also

[[Core Concepts|Core-Concepts]] · [[Cloud Architecture|Cloud-Architecture]] · [[Cloud Quick Start|Cloud-Quick-Start]] · [[Home]]
