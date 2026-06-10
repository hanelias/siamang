# Quickstart

This page walks through the smallest end-to-end survey: define **Variables**, bind
them to **Questions**, place those on a **Page**, assemble a **Questionnaire**, then
`validate`, `simulate`, `preview`, and `deploy`. A siamang survey is a plain Python
module — nothing more — so you can version, test, and import it like any other code.

## 1. Write the survey module

Save the following as `hello.py`. The CLI looks for a module-level variable named
`survey` (override with `--attribute`).

```python
import siamang as sg

# 1) Variables — the atomic measurement units, with full metadata.
age = sg.Variable("age", scale="ratio", label="Age")
fav = sg.Variable(
    "fav_color", scale="nominal",
    label="Favourite colour",
    labels={1: "Red", 2: "Blue", 3: "Green"},
)

# 2) Questions — bind a prompt to a variable.
q_age = sg.NumericInput("How old are you?", var=age, required=True)
q_fav = sg.SingleChoice("What is your favourite colour?", var=fav)

# 3) Page — one screen grouping the questions.
# 4) Questionnaire — the aggregate root.
survey = sg.Questionnaire(
    title="Hello, siamang",
    pages=[
        sg.Page(
            name="main",
            title="Tell us a bit about yourself",
            items=[q_age, q_fav],
        ),
    ],
)
```

That is a complete, runnable survey. The four layers — Variable → Question → Page →
Questionnaire — are all you need to start.

## 2. Validate

`Questionnaire.validate()` performs structural and logical checks: unique question
IDs and page names, valid `skip_to`/navigation targets, expressions that reference
only known variables, and well-formed scripts. It raises `ValueError` on the first
problem and returns `None` when the questionnaire is well-formed.

```python
from hello import survey

survey.validate()           # raises ValueError if anything is wrong
```

From the command line:

```bash
siamang validate hello.py
# → "OK" if well-formed; otherwise it lists the problems.
```

Pass `strict=True` (or use `lint()`) to surface softer warnings such as empty pages
or categorical variables without labels. See [[Validation and Linting|Validation-and-Linting]].

## 3. Simulate

You do not need a backend to start exploring analysis. `simulate()` generates a
synthetic dataset that respects each variable's scale, labels, and ranges, and
returns a [`SurveyData`](Working-with-Data) wrapping a pandas `DataFrame`.

```python
data = survey.simulate(n=500, seed=42)
print(data.frame.head())

# Declarative, SPSS-like reporting (auto labels + tests)
print(data.report.freq("fav_color").to_markdown())
```

`simulate(n=100, seed=42)` defaults to 100 rows and a fixed seed for reproducibility;
pass `seed=None` for fresh randomness on each call.

## 4. Preview locally

`siamang preview` builds the React frontend, serves it with a FastAPI + uvicorn
server, and stores responses in a local SQLite database (`survey.db`):

```bash
siamang preview hello.py --port 8000
# → http://127.0.0.1:8000 — fill the survey in your browser.
```

## 5. Deploy

When you are ready to collect real responses, deploy to a backend and frontend.
`Questionnaire.deploy()` compiles the survey, provisions the backend, builds a
self-contained bundle, and publishes it — returning a `DeployResult`.

```bash
siamang init                                  # one-time: store credentials
siamang deploy hello.py --backend supabase --frontend vercel
```

Or from Python:

```python
result = survey.deploy(backend="supabase", frontend="vercel")
print(result.url)                 # public survey URL
df = result.collect()             # pull accumulated responses any time
```

Bundled backends are `local` (SQLite), `supabase`, and `gsheets`; bundled
frontends are `local`, `vercel`, and `netlify`. See [[Deployment]].

## 6. Export to your stats package

`SurveyData.export()` round-trips variable labels, value labels, and missing-value
conventions into the format your tools expect:

```python
data.export("csv",   path="hello.csv")
data.export("xlsx",  path="hello.xlsx")
data.export("spss",  path="hello.sav")
data.export("stata", path="hello.dta")
```

## The full lifecycle

```
hello.py
    ├─ siamang validate   → schema + logic checks
    ├─ siamang preview    → local React frontend (SQLite)
    ├─ siamang deploy     → Supabase + Vercel (production)
    └─ survey.simulate()  → synthetic data for testing analysis
```

## See also

- [[Core Concepts|Core-Concepts]] — the data model behind these four layers (plus the optional `Block`).
- [[Variables and Measurement|Variables-and-Measurement]] — everything a `Variable` carries.
- [[Question Types|Question-Types]] — all seven question types.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — pages, blocks, and questionnaires.
