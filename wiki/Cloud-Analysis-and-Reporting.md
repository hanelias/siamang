# Cloud Analysis and Reporting

A project's analysis is **code**: ordinary Python scripts, committed to the
repository and declared in [[Project Config (siamang.yaml)|Cloud-siamang-yaml]],
that read the project's responses and produce tables, files, and report
documents. The platform runs them in the [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]]
with a Postgres role scoped to the project's own schema, captures their outputs,
and persists each run. Separately, a **server-side dashboard** computes
frequencies and crosstabs straight from the database for quick exploration.

Scripts use the [[Cloud Analysis SDK|Cloud-Analysis-SDK]] (`siamang_cloud`) for
data access and statistics, and the re-exported [[Report Document|Report-Document]]
to assemble Markdown/HTML reports.

## Declaring analysis scripts

Each `type: analysis` task in `siamang.yaml` names an entry script and,
optionally, a report artifact and extra outputs:

```yaml
tasks:
  cleaning:
    type: analysis
    entry: scripts/cleaning.py
    description: "Clean raw responses, write to clean_responses"

  final_tables:
    type: analysis
    entry: scripts/final_tables.py
    description: "Build frequency tables and crosstabs"   # → report section title
    report: outputs/final_tables.md                        # the script's Report.save(...) target
    outputs:
      - outputs/final_tables.xlsx                          # extra files to keep
```

The API exposes these to the web app:

- `GET /projects/{id}/scripts` — the configured analysis scripts.
- `POST /projects/{id}/scripts/{name}/run` — enqueue one script (role `analyst`+).
- `POST /projects/{id}/scripts/run-all` — run every analysis task and combine reports.
- `GET /projects/{id}/runs` — run history (status, log, output/report keys).
- `GET /projects/{id}/reports` — report artifacts indexed under `reports/`.

When a run is enqueued the API pins the project's default branch HEAD to a
concrete commit SHA, so the worker always checks out an immutable commit.

## Running one script — the `run_script` task

`worker/app/tasks/run_script.py` runs a single script and records its outcome on
the `runs` row:

1. Mark the run `running`, then download the commit archive.
2. Resolve the entry path and (optional) report path from `siamang.yaml`.
3. Build the **scoped DSN** — the platform DSN rewritten to the `project_<id>`
   login role, whose password is an HMAC of a shared secret
   (`sandbox_db.scoped_dsn`). No secret is stored; the worker reconstructs the
   same credentials the API provisioned.
4. Run the sandbox in **run_script** mode (`sandbox_run_script`): the checkout is
   mounted **read-write** so the script can write into `<work>/outputs`, and the
   container attaches to a **DB-only network**. The SDK connects with the scoped
   role via injected environment variables (`SIAMANG_CLOUD_PG_DSN`,
   `SIAMANG_CLOUD_PROJECT_SCHEMA`, `SIAMANG_CLOUD_PROJECT_ID`).
5. Collect the files written to `outputs/` (capped by count and total size so a
   runaway script cannot fill storage) and publish them.

On success the run is marked `completed` with the script log, the output prefix,
and the report key; a `run.completed` notification is emitted (and `run.failed`
on failure).

### Where results go

A script can emit results in four non-exclusive ways:

| Way | How | Where it shows |
| :-- | :-- | :-- |
| **Report artifact** | `Report(...).add(...).save("outputs/report.md")` | Repository (rendered Markdown/HTML) |
| New database table | `db.write_table("clean_responses", df)` | Database → Tables |
| File in `outputs/` | `df.to_excel("outputs/result.xlsx")` | Files (object storage) |
| Log | `print(...)` | Analysis → run details / log |

> **Storage vs. surfacing:** the rendered report itself is *stored* in object
> storage (MinIO/S3 — the worker uploads it and records the object key on
> `runs.report_key`), not committed back to the repository; the **Reports**
> tab / `GET /projects/{id}/reports` endpoint is the surfacing layer that lists
> and serves it.

### Artifact storage

When object storage (MinIO/S3) is configured, the worker uploads each `outputs/`
file under a deterministic key, `runs/<run_id>/outputs/<rel>`
(`MinioArtifactSink`), and stores the report's key on `runs.report_key`. Without
object storage it falls back to local metadata (`LocalArtifactSink`) so the run
still records what it produced.

## Running everything — the `run_all` task

`worker/app/tasks/run_all.py` powers **Run all**:

1. Read every `type: analysis` task in declaration order.
2. Run each script in the sandbox (`run_analysis`) with the same scoped DSN and
   DB-only network. If any step fails, the run is marked `failed` and stops.
3. Discover each task's Markdown report artifacts (its `report` plus any `.md`
   `outputs`), validating that paths stay inside the checkout.
4. **Combine** them into one document with `Report.combine(...)` (with a table of
   contents) — each script becomes a section titled by its `description`. The
   combined document is written to the configured `reports.combined` path
   (default `reports/report.md`).
5. Persist the combined report to object storage and index it in `project_files`
   (`record_report_file`) so it survives the checkout teardown and appears under
   `/reports`.

## Server-side dashboard aggregates

The web Dashboard renders aggregates computed in Postgres
(`api/app/routers/dashboard.py`), so frequencies and crosstabs stay correct at
any data volume rather than aggregating client-side over a sample:

- `GET /projects/{id}/dashboard/summary` — response/respondent counts,
  duplicates, partials, last-response time, and a per-day series.
- `GET /projects/{id}/dashboard/variables` — labelled variables available to chart.
- `GET /projects/{id}/dashboard/frequencies?variable=…` — a frequency
  distribution (`value`, `count`, `percent`).
- `GET /projects/{id}/dashboard/crosstab?rows=…&cols=…` — a two-way table with
  row/column totals.

These are read-only summaries; full analysis (weighting, significance tests,
custom tables, exports) belongs in the sandboxed scripts above.

## See also

[[Cloud Analysis SDK|Cloud-Analysis-SDK]] · [[Report Document|Report-Document]] · [[Cloud Scheduling and Webhooks|Cloud-Scheduling-and-Webhooks]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Cloud REST API|Cloud-REST-API]]
