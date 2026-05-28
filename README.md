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
  <a href="MANUAL.md">Manual</a>
</p>

---

```bash
pip install git+https://github.com/hanelias/siamang.git
siamang validate my_survey.py
siamang preview  my_survey.py        # local React preview
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
    ├─ siamang preview    → local React frontend (hot-reload)
    ├─ siamang deploy     → Vercel + Supabase (cloud deployment)
    └─ siamang init       → configures deployment credentials
```

**No GUI builders. No drag-and-drop. No lock-in.** Your survey is a
Python module — version-control it, test it, reuse it.

---

## Quick start

```python
from siamang import (
    Variable, Question, SingleChoice, Page, Questionnaire,
)

age = Variable("age", "interval", "How old are you?")
satisfaction = Variable(
    "satisfaction", "ordinal", "Overall satisfaction",
    labels={1: "Very dissatisfied", 2: "Dissatisfied",
            3: "Neutral", 4: "Satisfied", 5: "Very satisfied"},
)

q_age = Question("How old are you?", age, required=True)
q_sat = SingleChoice("How satisfied are you?", satisfaction, required=True)

survey = Questionnaire(
    title="My First Survey",
    pages=[Page("main", "Survey Questions", items=[q_age, q_sat])],
)
```

Save as `survey.py`, then:

```bash
siamang validate survey.py       # check for errors
siamang preview  survey.py       # open in browser at localhost:8000
```

For a hands-on look at every feature, run the bundled
[`examples/demo_survey.py`](examples/demo_survey.py) — an "AI & Work
Attitudes Study 2026" survey that exercises every question type,
visibility rules, conditional logic, theming, and the "Other (specify)"
feature:

```bash
pip install git+https://github.com/hanelias/siamang.git
siamang preview examples/demo_survey.py --port 8000 --open
```

---

## Features

| Area | Capabilities |
|------|-------------|
| **Core** | Variables (nominal/ordinal/interval/ratio), questions (single/multi/open/numeric/likert/matrix/ranking), pages, skip logic (`show_if`), quotas, validation |
| **Scripts** | Inline JavaScript for survey-side behaviour — 7 trigger points (`onInit`, `onPageEnter`, `onPageExit`, `onQuestionShow`, `onAnswer`, `onSubmit`, `onRandomize`) |
| **Frontend** | React 18 runtime, keyboard navigation, swipe gestures, dark mode, per-question error boundaries, auto-save, access codes |
| **CLI** | `validate`, `preview`, `deploy`, `init` |
| **Backend** | Local SQLite for dev, Supabase for cloud (RLS policies, pagination, quota counters, migration export) |
| **Deploy** | Vercel frontend with CSP headers and cache control; survey data is bundled into a self-contained HTML payload |
| **Data I/O** | CSV, Excel (.xlsx), SPSS (.sav), Stata (.dta), R (.rda) — round-trip with `labels`, `missing_values`, `formats` preserved |

---

## Deployment

### Local (development)

```bash
pip install git+https://github.com/hanelias/siamang.git
siamang preview my_survey.py        # → http://127.0.0.1:8000
```

### Cloud deployment (Vercel + Supabase)

```bash
siamang init                                   # one-time: stores credentials
siamang deploy my_survey.py --backend supabase --frontend vercel
```

The deploy command:

1. Bundles your survey into a self-contained HTML payload (pre-built React runtime).
2. Uploads static assets to Vercel.
3. Provisions Supabase tables with row-level security and quota counters.
4. Prints the response dashboard URL.

---

## Key concepts

| Concept | Description |
|---------|-------------|
| **Variable** | The atomic unit — `name`, `scale`, `label`, value `labels`, `missing_values`. |
| **Question** | Binds a variable to a prompt — `text`, `var`, `required`, `hint`, `show_if`, `skip_to`. |
| **Question types** | `Question` (open / numeric), `SingleChoice`, `MultiChoice`, plus matrix / Likert / ranking subclasses. |
| **Script** | Dataclass holding JavaScript snippets that hook into survey lifecycle events. |
| **Page** | Groups questions into one screen: `Page(id, title, items=[...])`. |
| **Questionnaire** | Top-level container: `Questionnaire(title, pages, blocks, deadline, variables, scripts)`. |
| **Quota** | Per-cell respondent target: `Quota(variable, value, target)`. |
| **SurveyData** | Collected responses with `.analysis()` for frequencies, crosstabs, descriptives. |

---

## Project layout

```
siamang/
├── core/      Data model: Variable, Question, Block, Page, Questionnaire, Expression, Quota, Script
├── data/      SurveyData, analysis, processing, frequency/crosstab/banner tables
├── frontend/  React 18 runtime, JSX→JS compiler, bundle builder, theme engine
├── deploy/    Backends (SQLite, Supabase), frontends (Vercel, local), pipeline orchestration
├── cli/       validate, preview, deploy, init
├── io/        Import/export for CSV, Excel, SPSS, Stata, R
└── config/    User configuration (~/.siamang.toml), secrets
```

---

## Requirements

- **Python 3.11+**
- For cloud deployment: a **Supabase** project + anon key, and a
  **Vercel** account.

---

## Documentation

| Resource | Description |
|----------|-------------|
| [`MANUAL.md`](MANUAL.md) | Single-file manual with worked examples for every feature. |
| [`docs/index.md`](docs/index.md) | Full documentation hub: getting started, concepts, per-module reference, cookbook, development guide. |
| [`docs/reference/`](docs/reference/) | API reference — every public class and function in `core`, `data`, `io`, `frontend`, `deploy`, `cli`. |
| [`LICENSE`](LICENSE) | MIT License. |

---

## License

Siamang is released under the [MIT License](LICENSE). Free for any use —
academic, commercial, personal.
