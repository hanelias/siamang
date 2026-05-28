# siamang documentation

Welcome to **siamang** — a research-as-code framework for sociological
surveys. Define your variables, questionnaire, and logic in pure Python;
then validate, preview, simulate, deploy, collect, and analyse from a
single pipeline.

---

## Documentation map

### Get started

- **[Getting started](getting-started.md)** — install, write your first
  survey, run `validate`/`preview`/`simulate`.
- **[Manual with examples](../MANUAL.md)** — a single-file tour of every
  feature with worked examples (variables, questions, visibility,
  blocks, quotas, scripts, analysis, I/O, deploy, theming).
- **[Concepts](concepts.md)** — the philosophy, the data model, and the
  pipeline as a whole.

### Reference

Per-module API reference. Each page is an authoritative listing of every
public class, dataclass field, and helper exported from the subpackage.

- **[`siamang.core`](reference/core.md)** — `Variable`, `Question` and
  its subclasses, `Page`, `Block`, `Questionnaire`, `Option`, `Media`,
  `Expression`, `Quota`, `Script`, `FilterRule`.
- **[`siamang.data`](reference/data.md)** — `SurveyData`, the analysis
  layer (frequencies, crosstabs, descriptives, banner tables, weighted
  statistics), and `SurveyTables`.
- **[`siamang.reporting`](reference/reporting.md)** — High-level declarative
  reporting tables (`FreqTable`, `CrossTable`, `GroupMeanTable`) and charts
  (`BarChart`, `BoxPlot`, `HeatMap`, `ScatterPlot`).
- **[`siamang.io`](reference/io.md)** — CSV, Excel, SPSS (`.sav`),
  Stata (`.dta`), R script export, and the data dictionary
  reader/writer.
- **[`siamang.frontend`](reference/frontend.md)** — `FrontendBuilder`,
  `UIConfig`, runtimes (React, SurveyJS), client templates (Local,
  Supabase), the `SurveySchema` IR, and the React payload compiler.
- **[`siamang.deploy`](reference/deploy.md)** — `DeployPipeline`,
  `DeployResult`, the abstract `BackendAdapter` / `FrontendAdapter`,
  the bundled backends (Local, Supabase, Google Sheets), and frontends
  (Local, Vercel, Netlify).
- **[CLI](reference/cli.md)** — `siamang validate / preview / deploy /
  init`, every flag documented.

### Other

- **[Cookbook](cookbook.md)** — recipes: visibility logic, quotas,
  custom scripts, attaching media, importing/exporting datasets.

---

## What `siamang` is, in one screen

```python
import siamang as sg

age    = sg.Variable("age",    scale="ratio",    label="Age")
gender = sg.Variable("gender", scale="nominal", label="Gender",
                    labels={1: "Male", 2: "Female", 3: "Other"})
trust  = sg.Variable("trust",  scale="ordinal", label="Trust in government",
                    labels={1: "No trust", 5: "Full trust"})

survey = sg.Questionnaire(
    title="Political Trust — 2026",
    pages=[
        sg.Page(
            name="demographics",
            title="About you",
            items=[
                sg.NumericInput("How old are you?", var=age, required=True),
                sg.SingleChoice("What is your gender?", var=gender),
            ],
        ),
        sg.Page(
            name="trust",
            items=[
                sg.LikertScale("How much do you trust the government?",
                               var=trust, points=5,
                               left_label="No trust", right_label="Full trust"),
            ],
            show_if=age.ge(18),
        ),
    ],
)
```

```bash
siamang validate my_survey.py
siamang preview  my_survey.py        # → http://127.0.0.1:8000
siamang deploy   my_survey.py --backend supabase --frontend vercel
```

```python
data = survey.simulate(n=500, seed=42)
# High-level declarative reporting API
print(data.report.freq("trust").to_markdown())
data.export("csv", "trust.csv")
```

Continue with **[Getting started →](getting-started.md)**.
