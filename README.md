<p align="center">
  <img src="siamang_logo.png" alt="siamang" width="160">
</p>

<h1 align="center">siamang</h1>

<p align="center">
  <strong>Research-as-code framework for sociological surveys.</strong><br>
  Define variables, questionnaires, and logic in pure Python — then
  deploy, collect, and analyze in a single pipeline.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#full-pipeline-example">Full pipeline example</a> ·
  <a href="docs/reference/">API Reference</a>
</p>

---

```bash
pip install git+https://github.com/hanelias/siamang.git
siamang validate my_survey.py
siamang preview  my_survey.py        # local preview
siamang deploy   my_survey.py --backend supabase --frontend vercel
```

---

## What it does

siamang turns a survey into a running web application from a single
Python script:

```
my_survey.py          ← you write this
    │
    ├─ siamang validate   → catches errors before deployment
    ├─ siamang preview    → local frontend (hot-reload)
    ├─ siamang deploy     → Vercel + Supabase (cloud deployment)
    └─ survey.simulate()  → synthetic data for testing
```

**No GUI builders. No drag-and-drop. No lock-in.** Your survey is a
Python module — version-control it, test it, reuse it.

---

## Quick start

```python
from siamang.core import (
    Variable, SingleChoice, LikertScale, Page, Questionnaire,
)

# Define variables with full metadata
satisfaction = Variable(
    "satisfaction", scale="ordinal",
    label="Overall satisfaction",
    labels={1: "Very dissatisfied", 2: "Dissatisfied",
            3: "Neutral", 4: "Satisfied", 5: "Very satisfied"},
)
remote_freq = Variable(
    "remote_freq", scale="ordinal",
    label="Remote work frequency",
    labels={1: "Never", 2: "1-2 days/week",
            3: "3-4 days/week", 4: "Fully remote"},
)

# Build questions
q_sat = LikertScale("How satisfied are you with your current role?",
                    var=satisfaction, points=5, required=True)
q_remote = SingleChoice("How often do you work remotely?",
                        var=remote_freq, display="radio", required=True)

# Assemble questionnaire
survey = Questionnaire(
    title="Work Attitudes Study",
    pages=[Page("main", items=[q_sat, q_remote])],
)

# Simulate and analyze
data = survey.simulate(n=200)
print(data.report.freq("satisfaction").to_markdown())
data.plot.bar("satisfaction").show()
```

---

## Full Pipeline Example

The [`examples/full_pipeline/`](examples/full_pipeline/) directory contains a complete Jupyter notebook demonstrating the entire research workflow — from survey design to statistical analysis:

1. **Survey Design** — 12 variables, 6 pages, conditional routing (`show_if`), matrix questions, Likert scales
2. **Simulation & Deployment** — 250 synthetic respondents, local SQLite storage, interactive HTML preview
3. **Declarative Reporting** — frequency tables, cross-tabs with Chi², grouped means with auto-selected tests, correlation heatmaps
4. **Visualizations** — bar charts, boxplots, heatmaps, scatter plots — all with one line of code

```bash
cd examples/full_pipeline
jupyter notebook full_pipeline_demo.ipynb
```

The folder also includes `survey_preview.html` — an interactive HTML survey you can open in any browser to see how the questionnaire looks for respondents.

---

## Features

| Area | Capabilities |
| :--- | :--- |
| **Core** | Variables (nominal/ordinal/interval/ratio), questions (single/multi/open/numeric/likert/matrix/ranking), pages, skip logic (`show_if`/`hide_if`), quotas, validation |
| **Reporting** | Declarative tables (`FreqTable`, `CrossTable`, `GroupMeanTable`) and charts (`BarChart`, `BoxPlot`, `HeatMap`, `ScatterPlot`) — automatic labels, statistical tests, and metadata awareness |
| **Scripts** | Inline JavaScript for survey-side behaviour — 7 trigger points |
| **Frontend** | SurveyJS and React 18 runtimes, dark mode, auto-save, access codes, 6 theme presets |
| **Backend** | Local SQLite for development, Supabase for production, Google Sheets for collaborative access |
| **Deploy** | Vercel and Netlify frontends with CSP headers; self-contained HTML bundle for offline use |
| **Data I/O** | CSV, Excel (.xlsx), SPSS (.sav), Stata (.dta), R (.rda) — round-trip with labels and missing values preserved |

---

## Declarative Reporting API

Siamang automatically uses variable metadata (labels, scales, missing values) to produce publication-ready outputs — like SPSS, but in Python:

```python
data = survey.simulate(n=300)

# Tables — automatic labels, tests, and formatting
data.report.freq("it_role")                              # frequency table
data.report.crosstab("gender", "satisfaction", pct="col") # cross-tab + Chi²
data.report.means("autonomy", by="remote_freq")          # means + Kruskal-Wallis

# Charts — one line, automatic axis labels
data.plot.bar("it_role")
data.plot.boxplot("satisfaction", by="remote_freq", show_points=True)
data.plot.heatmap(["surv_keystroke", "surv_camera"], by="remote_freq")
data.plot.scatter("satisfaction", "autonomy", hue="gender")

# Export
data.report.freq("it_role").to_markdown()   # Markdown string
data.report.freq("it_role").to_dataframe()  # pandas DataFrame
data.report.freq("it_role").to_html()       # HTML table
```

---

## Deployment

### Local (development)

```bash
siamang preview my_survey.py        # → http://127.0.0.1:8000
```

### Cloud — Vercel + Supabase (high concurrency)

```bash
siamang init                        # one-time: stores credentials
siamang deploy my_survey.py --backend supabase --frontend vercel
```

### Cloud — Netlify + Google Sheets (lightweight)

```bash
export SIAMANG_GSHEETS_CREDENTIALS_FILE=./service-account-key.json
export NETLIFY_AUTH_TOKEN=nfp_...
siamang deploy my_survey.py --backend gsheets --frontend netlify
```

Responses are written to a Google Spreadsheet (one row per respondent) via an **Apps Script proxy** that acts as a secure intermediary. The survey is hosted on Netlify CDN with automatic HTTPS and global edge distribution.

> **Note:** The Google Sheets backend is currently **experimental** for public web deployments. Browser-to-Sheets writes require an Apps Script Web App URL to avoid exposing credentials. See [`docs/reference/deploy.md`](docs/reference/deploy.md#googlesheetsbackend) for setup instructions.

### Deployment combinations

| Use case | Backend | Frontend |
| :--- | :--- | :--- |
| Local development / testing | `local` | `local` |
| Small survey, shared with team | `gsheets` | `netlify` |
| Production, high concurrency | `supabase` | `vercel` or `netlify` |
| Offline / air-gapped | `local` | `local` (HTML bundle) |

---

## Project Layout

```
siamang/
├── core/        Variable, Question types, Block, Page, Questionnaire, Expression, Quota, Script
├── data/        SurveyData, DataAnalysis, DataProcessing, SurveyTables
├── reporting/   Declarative tables (FreqTable, CrossTable, GroupMeanTable) and charts (BarChart, BoxPlot, HeatMap, ScatterPlot)
├── frontend/    SurveyJS & React runtimes, bundle builder, UIConfig theme engine, presets
├── deploy/      Backends (SQLite, Supabase, Google Sheets), frontends (Vercel, Netlify, local), pipeline orchestration
├── cli/         validate, preview, deploy, init
├── io/          Import/export for CSV, Excel, SPSS, Stata, R
└── config/      User configuration (~/.siamang.toml), secrets
```

---

## Documentation

| Resource | Description |
| :--- | :--- |
| [`docs/reference/core.md`](docs/reference/core.md) | API reference — Variable, Expression, all Question types, Page, Questionnaire |
| [`docs/reference/data.md`](docs/reference/data.md) | API reference — SurveyData, DataAnalysis, DataProcessing, SurveyTables |
| [`docs/reference/reporting.md`](docs/reference/reporting.md) | API reference — Declarative tables and charts |
| [`docs/reference/frontend.md`](docs/reference/frontend.md) | API reference — UIConfig, theme presets, runtimes, bundle builder |
| [`docs/reference/deploy.md`](docs/reference/deploy.md) | API reference — Backends (Local, Supabase, Google Sheets), Frontends (Local, Vercel, Netlify), pipeline |
| [`examples/full_pipeline/`](examples/full_pipeline/) | Complete worked example: design → deploy → analyze |

---

## Requirements

- **Python 3.11+**
- For cloud deployment (option A): a **Supabase** project and a **Vercel** account
- For cloud deployment (option B): a **Google Cloud** service account and a **Netlify** account
- For Google Sheets backend: `pip install google-auth google-auth-httplib2 google-api-python-client`

---

## License

Siamang is released under the [MIT License](LICENSE). Free for any use —
academic, commercial, personal.
