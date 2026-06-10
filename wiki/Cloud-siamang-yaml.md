# Project Config (siamang.yaml)

Every siamang Cloud project has a `siamang.yaml` at the repository root. It wires
the project together: where the survey lives, which deployment environments
exist, what analysis scripts to run, the sandbox runtime, and where reports go.
It is committed to the repo (every push is validated), and the platform reads it
at validate, deploy, and analysis time.

The canonical parser is `project_config.py` in `siamang_cloud_engine`, exposed as
`load_config()` / `parse_config()` (see [[Cloud Engine Plugin|Cloud-Engine-Plugin]]).

## Annotated example

This is the example committed to every new project, with comments on each key:

```yaml
name: "Brand Awareness Study 2026"   # human-readable project name
org: "research-agency"               # owning organization slug
version: "1.0"                       # config schema version

tasks:
  # ── The survey itself: compiled and served as a static bundle ────────────
  survey:
    type: survey
    entry: survey/questionnaire.py   # module exporting `survey = Questionnaire(...)`
    environments:
      - { name: pilot, max_responses: 50 }     # separate deployment + survey_id
      - { name: main,  max_responses: 1200 }   # response cap enforced at ingest

  # ── Analysis scripts: Python run in the sandbox with the SDK ─────────────
  cleaning:
    type: analysis
    entry: scripts/cleaning.py
    description: "Clean raw responses, write to clean_responses"

  final_tables:
    type: analysis
    entry: scripts/final_tables.py
    description: "Build frequency tables and crosstabs"   # → report section title
    report: outputs/final_tables.md     # the Markdown the script saves via Report.save(...)
    outputs:                            # extra files kept (object storage / Files)
      - outputs/final_tables.xlsx
      - outputs/freq.xlsx

runtime:
  python: "3.11"                        # sandbox interpreter
  packages:                             # installed in the sandbox (must be allowlisted)
    - "siamang[charts]>=0.5"
    - "pandas>=2.0"

database:
  backend: platform                     # managed Postgres
  schema: auto                          # resolves to project_<id>

storage:
  outputs: outputs/                     # root folder for generated files
  commit_outputs: false                 # commit outputs/ back to the repo after a run

reports:
  dir: reports/                         # where the combined report is written
  combined: reports/report.md           # combined document name (Run all)
  formats: [md, html]                   # formats to render (pdf on request)
```

## Top-level keys

| Key | Type | Parsed by `project_config.py` | Notes |
| :-- | :--- | :---: | :--- |
| `name` | string | yes (`ProjectConfig.name`) | display name |
| `org` | string | yes (`ProjectConfig.org`) | organization slug |
| `version` | string | no | config schema version (informational) |
| `tasks` | mapping | yes | survey + analysis tasks (below) |
| `runtime` | mapping | yes (`ProjectConfig.runtime`) | sandbox interpreter + packages |
| `reports` | mapping | yes (`ProjectConfig.reports`) | combined-report settings |
| `database` | mapping | no | storage backend; reserved (the platform always uses `project_<id>`) |
| `storage` | mapping | no | `outputs/` root and `commit_outputs` toggle |

> `project_config.py` parses `name`, `org`, `tasks`, `runtime`, and `reports`
> into typed objects. `version`, `database`, and `storage` are recognised parts
> of the file format (they appear in every generated project) but are consumed by
> other components or reserved, not by the typed `ProjectConfig`.

## `tasks`

`tasks` is a **mapping** of task name → spec. The task name is its identifier
(e.g. the section title in a combined report). Each spec has a `type`.

### `type: survey`

Exactly one survey task drives Deployments. Fields:

- `entry` (required) — repository path to the questionnaire module that exports a
  module-level `survey` object (and, optionally, an `options` dict for compiler
  settings and quotas).
- `environments` — a list of `{ name, max_responses }`. Each environment is a
  separate deployment with its own `survey_id`; its `max_responses` overrides the
  questionnaire's own cap at deploy time.

```python
from siamang_cloud_engine import load_config

cfg = load_config("siamang.yaml")
cfg.survey.entry                  # "survey/questionnaire.py"
cfg.survey.environments[0].name   # "pilot"
cfg.survey.environments[0].max_responses  # 50
```

### `type: analysis`

Each analysis task is one script (see [[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]]).
Fields:

- `entry` (required) — repository path to the Python script.
- `description` — human label; becomes the section title in the combined report.
- `report` — path to the Markdown report the script saves (via `Report.save`);
  opened as a document in the Repository and listed in the run's outputs.
- `outputs` — extra generated files to keep (object storage / Files); `.md`
  outputs are also treated as report artifacts by Run all.

```python
cfg.analyses                  # list[AnalysisTask] in declaration order
cfg.analysis("final_tables")  # look one up by name
```

### `type: connector` (data connectors)

A project may also declare `type: connector` tasks for moving data in or out
(S3, GCS, Azure, a database, Sheets, BigQuery, Snowflake). These are not part of
the typed `ProjectConfig`; the worker parses them separately
(`deploy_util.connector_tasks` → `ConnectorSpec`). The shape:

```yaml
tasks:
  export_to_s3:
    type: connector
    target: s3            # registry key: s3 | gcs | azure | database | sheets | bigquery | snowflake
    direction: out        # out | in
    table: clean_responses  # project table to export (or destination on import)
    secret: aws_creds     # project_secrets key holding credentials
    config:               # adapter-specific settings
      bucket: my-research-exports
      prefix: brand-study/
```

See [[Cloud Connectors|Cloud-Connectors]] for the connector targets and how they
run.

## `runtime`

- `python` — interpreter version string (defaults to `"3.11"` when omitted).
- `packages` — packages installed in the sandbox for both survey and analysis
  tasks. **Every package must be on the curated allowlist**; validation fails a
  commit otherwise. The API exposes the resolved runtime at
  `GET /projects/{id}/runtime`.

## `reports`

Settings for the combined **Run all** document (see
[[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]]):

- `dir` — folder for the combined report.
- `combined` — combined document path (default `reports/report.md`); must be a
  Markdown filename.
- `formats` — formats to render (`md`, `html`; PDF on request).

## See also

[[Cloud Engine Plugin|Cloud-Engine-Plugin]] · [[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]] · [[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]] · [[Cloud Analysis SDK|Cloud-Analysis-SDK]] · [[Cloud Connectors|Cloud-Connectors]] · [[Cloud Scheduling and Webhooks|Cloud-Scheduling-and-Webhooks]]
