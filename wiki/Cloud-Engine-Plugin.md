# Cloud Engine Plugin

`siamang_cloud_engine` is the thin plugin that adapts the open-source
[`siamang`](https://github.com/hanelias/siamang) engine to the platform. It does
**not** fork the engine: it plugs into the engine's published extension seams and
adds the few platform-specific pieces — a Postgres-backed storage backend, a
frontend client that posts to the absolute Ingest API, a composable `Report`
builder, the sandbox-side `build_bundle()` helper, and the `siamang.yaml` parser.

```python
from siamang_cloud_engine import (
    PlatformBackend,        # targets the siamang.deploy.base.BackendAdapter seam (plain class until Service Integration)
    PlatformClientTemplate, # implements siamang.frontend.client.base.BackendClientTemplate
    Report,                 # composable report document (re-exported by the SDK)
    ProjectConfig, load_config, parse_config,   # siamang.yaml parsing
)
```

The package is installed into the sandbox image and the worker; user survey code
never imports it directly.

## How it plugs into the engine's seams

The engine defines two abstract seams that a deployment target implements:

- `BackendAdapter` (`siamang.deploy.base`) — provisions storage, accepts
  responses, enforces quotas, returns collected data.
- `BackendClientTemplate` (`siamang.frontend.client.base`) — renders the
  `env.js` snippet that wires the static bundle to its transport.

`PlatformBackend` and `PlatformClientTemplate` are the platform's
implementations of those seams.

### `PlatformBackend`

`PlatformBackend` (`backend.py`) maps a compiled survey to **per-project
Postgres** storage. It holds the pure parts — the survey id, a schema hash, a
frontend-safe `BackendConfig` with absolute Ingest URLs, and the `survey_meta` /
quota rows to persist:

```python
from siamang_cloud_engine import PlatformBackend

backend = PlatformBackend(
    project_id=42,
    pg_schema="project_42",
    ingest_base_url="https://api.example.com",
)

cfg = backend.build_config(schema, survey_id="sid123")
cfg.settings["endpoint"]        # "https://api.example.com/ingest/sid123/responses"
cfg.settings["quota_endpoint"]  # "https://api.example.com/ingest/sid123/quota-check"
cfg.internal                    # {"pg_schema": "project_42", "project_id": 42} — never sent to the bundle

backend.survey_meta_row(schema, "sid123")  # row for <schema>.survey_meta
backend.quota_rows(schema, "sid123")       # rows for <schema>.quota_counters
PlatformBackend.new_survey_id()            # 12-hex survey id
```

The actual reads/writes (`store_response`, `check_quota`, `get_responses`,
`provision`) are intentionally **deferred** placeholders that raise
`NotImplementedError`. The live path does not run inside the engine: ingest and
provisioning writes happen in the trusted worker (`worker/app/dbio.py`), and
analysis reads use the [[Cloud Analysis SDK|Cloud-Analysis-SDK]] `db` module.
Keeping these methods as documented placeholders lets the class be constructed
and unit-tested without a database.

### `PlatformClientTemplate`

`PlatformClientTemplate` (`client.py`) renders `env.js` so the static bundle
posts answers to the **absolute** Ingest URL (the bundle is served by nginx with
no backend of its own, so endpoints are absolute and CORS applies):

```python
from siamang.frontend.client.base import ClientEnv
from siamang_cloud_engine import PlatformClientTemplate

env = ClientEnv(survey_id="sid123", backend="platform", settings=cfg.settings)
js = PlatformClientTemplate().render_env_js(env)
# Registers window.SIAMANG_TRANSPORTS.platform with async submit()/checkQuota()
# that fetch() the absolute /ingest/<id>/responses and /quota-check endpoints.
```

## `build_bundle()` — the sandbox-side build

`deploy.build_bundle()` is the service-free half of deployment: it loads and
compiles the survey and writes its static bundle, returning both the file list
and the rows the trusted worker later persists. In production this runs **inside
the sandbox** (it executes user code), with no DB and no network.

```python
from siamang_cloud_engine.deploy import build_bundle

result = build_bundle(
    survey_path="survey/questionnaire.py",
    survey_id="sid123",
    ingest_base_url="https://api.example.com",
    project_id=42,
    pg_schema="project_42",
    out_dir="/out",
)

result["files"]        # sorted bundle filenames (index.html, env*.js, manifest.json, …)
result["survey_meta"]  # row the worker INSERTs into survey_meta
result["quotas"]       # quota_counters rows
```

It loads the module-level `survey` object and an optional `options` dict
(compiler settings such as `completion_text` and the `quota=[Quota(...)]` list),
compiles the questionnaire, builds the `BackendConfig` and `ClientEnv` from
`PlatformBackend`, and runs the engine's `FrontendBuilder` with the
`PlatformClientTemplate`. The `deploy` worker task calls this through the
sandbox; see [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]].

## `Report` — the report builder

`Report` is a composable document (narrative + tables + charts → Markdown/HTML)
that orchestrates the engine's existing `siamang.reporting` tables and charts.
It lives here so it is buildable in this repo, and the SDK re-exports it as
`from siamang_cloud import Report`. The canonical `Report` now lives in the
engine itself as `siamang.reporting.Report`; the plugin/SDK version is the same
builder, re-exported for cloud analysis scripts. Every builder method returns `self` for
fluent chaining; `save()` is the terminal call. `Report.combine(...)` merges
several reports into one with a table of contents — that is how **Run all**
produces a single document. Full method reference: [[Report Document|Report-Document]].

```python
from siamang_cloud_engine import Report

(Report(title="Satisfaction", description="Q2 2026")
    .heading("Overview")
    .add(freq_df, caption="Table 1. Frequencies")
    .note("49 cases dropped.")
    .save("outputs/report.md"))
```

## `ProjectConfig` / `load_config()`

`project_config.py` is the pure parser for `siamang.yaml`. `load_config(path)`
reads and parses the file into a typed `ProjectConfig` (with `SurveyTask`,
`Environment`, and `AnalysisTask` records); `parse_config(dict)` does the same
from already-loaded YAML:

```python
from siamang_cloud_engine import load_config

cfg = load_config("siamang.yaml")
cfg.name, cfg.org
cfg.survey.entry                 # "survey/questionnaire.py"
cfg.survey.environments          # [Environment(name="pilot", max_responses=50), …]
cfg.analyses                     # [AnalysisTask(name="cleaning", entry="scripts/cleaning.py", …), …]
cfg.analysis("final_tables")     # look one up by name
cfg.runtime, cfg.reports         # raw dicts
```

The fields and the full file format are documented in
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]].

## `engine_patches` — survey page kinds

The platform's example surveys use a few page kinds the engine gained for the
cloud UI, distributed as a patch under `engine_patches/`
(`0003-survey-page-kinds.diff`). A `Page` can carry a `kind` that changes how the
runtime renders it:

- `content` — a non-terminal page that shows arbitrary HTML `body` instead of
  questions (intro / consent).
- `disqualification` — a terminal screen shown when a respondent is screened out
  (records the response as screened-out).
- `final` — a terminal screen with a custom thank-you `body`.
- `redirect` — a terminal screen that redirects to a `redirect_url` (e.g. a panel
  completion URL).

Terminal kinds end the survey when reached (typically gated by `show_if`); these
are exported as `ContentPage`, `DisqualificationPage`, `FinalPage`, and
`RedirectPage` from `siamang.core`. See
[[Pages Blocks and Structure|Pages-Blocks-and-Structure]] for the page model.

## See also

[[Deployment]] · [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] · [[Report Document|Report-Document]] · [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]] · [[Cloud Analysis SDK|Cloud-Analysis-SDK]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]]
