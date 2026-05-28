# Concepts

## Research-as-code

A siamang questionnaire is a **plain Python module**, not a row in a
proprietary database. That means:

- it lives in your version control with the rest of your code;
- it can be reviewed, diff-ed, branched, and rolled back like any other
  source file;
- it can be tested with the standard tooling (`pytest`, type checkers,
  linters);
- it can be imported and inspected from a notebook or a pipeline.

The same module flows through every stage of the survey lifecycle.

```
my_survey.py
    │
    ├── siamang validate    →  schema + logic validation
    ├── siamang preview     →  local React frontend (SQLite backend)
    ├── siamang deploy      →  Vercel + Supabase (production)
    ├── survey.simulate(n=) →  synthetic dataset for testing analysis
    ├── SurveyData.export() →  CSV / Excel / SPSS / Stata / R round-trip
    └── SurveyData.report   →  declarative tables, charts, banner tables, …
```

## The data model

Five layers, each with a strict responsibility.

### 1. `siamang.core` — the model

The shape of a questionnaire as a tree of immutable dataclasses.

```
Questionnaire
├── pages: list[Page]
│       ├── items: list[Question | Block]
│       └── show_if / hide_if : Expression | str | None
└── variables: VariableMap
```

| Object | Role |
|--------|------|
| `Variable` | An atomic measurement unit (`name`, `scale`, `labels`, `missing_values`, …). |
| `Question` and its subclasses (`SingleChoice`, `MultiChoice`, `LikertScale`, `NumericInput`, `OpenText`, `Matrix`, `Ranking`) | Bind a prompt to one variable (or many, for Matrix and wide MultiChoice). |
| `Option` | A single answer choice with its own `show_if`/`hide_if` and optional `Media`. |
| `Media` | An `image`, `video`, or `audio` attachment to a question or option. |
| `Page` | One screen in the survey. Has its own visibility gate. |
| `Block` | A named container of questions/blocks inside a page; randomisable; can be hidden. |
| `Expression` | The typed DSL for visibility conditions (`age.ge(18) & gender.eq(2)`). |
| `Quota` | A respondent target per cell (`{variable: target_value, limit: int}`). |
| `Script` | A JavaScript snippet hooked into a survey lifecycle event. |
| `Questionnaire` | The aggregate root; owns the pages or blocks and provides `validate()` / `compile()` / `simulate()` / `deploy()`. |

Every dataclass is `frozen=True, slots=True` — once you construct a
questionnaire, no other code can mutate it.

### 2. `siamang.frontend` — schema + bundle

Compiles a `Questionnaire` into:

- a `SurveySchema` IR (used by the SurveyJS runtime path), or
- a React payload (used by the bundled React runtime).

The output is a self-contained `SurveyBundle` (HTML + JS + CSS + env)
that can be deployed as static files.

| Object | Role |
|--------|------|
| `FrontendBuilder` | Combines a `RuntimeAdapter` (React / SurveyJS), a `UIConfig` (theme, labels, branding), and a `BackendClientTemplate` (Local / Supabase) into a `SurveyBundle`. |
| `UIConfig` | All branding and UI-strings settings (logo, colours, progress style, language) — see [`reference/frontend.md`](reference/frontend.md). |
| `ReactRuntime` | Renders the survey using the in-tree React templates; compiles JSX on the fly via `npx sucrase` or `npx babel`. |
| `SurveyJSRuntime` | Older path, renders via SurveyJS CDN. |
| `LocalClientTemplate` / `SupabaseClientTemplate` | Generate the JavaScript snippet that talks to the backend from the browser. |

### 3. `siamang.deploy` — backends & frontends

The pipeline that turns a `Questionnaire` into a publicly-reachable URL.

```
Questionnaire
    │
    ├── BackendAdapter.provision()      →  BackendConfig (DB connection, RLS policies)
    ├── FrontendBuilder.build()         →  SurveyBundle
    └── FrontendAdapter.publish()       →  URL
        ↓
    DeployResult.collect() / .responses()
```

| Object | Role |
|--------|------|
| `BackendAdapter` | Abstract base; subclasses provision storage and return a `BackendConfig`. |
| `FrontendAdapter` | Abstract base; subclasses receive a `SurveyBundle` and publish it (local server or Vercel). |
| `DeployPipeline` | Orchestrator: validate, provision, build, publish. |
| `DeployResult` | Hands back the deployed URL and lets you `.collect()` accumulated responses or `.responses()` filtered/paginated. |

Bundled backends: `local` (SQLite), `supabase`, `gsheets` (Google Sheets). Bundled frontends:
`local` (FastAPI + uvicorn), `vercel`, `netlify`. Custom backends are picked up
via the `siamang.backends` / `siamang.frontends` entry points.

### 4. `siamang.data` — analysis

Wraps a pandas `DataFrame` together with its `VariableMap` and exposes
accessors for analysis, processing, and tabulation.

```python
data = survey.simulate(n=1000)
# High-level declarative reporting (recommended)
data.report.freq("trust")
data.report.crosstab("gender", "party")
data.plot.boxplot("trust", by="gender")

# Low-level data processing and tables
data.tables.banner(rows=["trust"], columns=["gender", "region"])
data.processing.recode("age", {18: "young", 65: "old"})
```

Accessors:

| Accessor | Purpose |
|----------|---------|
| `data.report` (`ReportAccessor`) | Declarative, SPSS-like tables (`freq`, `crosstab`, `means`) with auto-labels and statistical tests. |
| `data.plot` (`PlotAccessor`) | Declarative, SPSS-like charts (`bar`, `boxplot`, `heatmap`, `scatter`) with auto-labels and layout. |
| `data.analysis` (`DataAnalysis`) | Low-level statistical methods (frequencies, crosstabs, proportion CIs, scale alpha, ESS, etc.). |
| `data.processing` (`DataProcessing`) | Value-level transforms (recode, derive). |
| `data.tables` (`SurveyTables`) | Banner / multi-cell tables for export. |

### 5. `siamang.io` — round-trip with stats packages

Every reader and writer round-trips metadata (variable labels, value
labels, missing-value conventions, formats) so that a `Questionnaire`
defined in siamang produces an SPSS `.sav` that opens identically in
SPSS, and a `.sav` written elsewhere reads back into siamang with the
same `VariableMap`.

Supported formats:

| Format | Reader | Writer | Extra |
|--------|--------|--------|-------|
| CSV | `CSVReader` | `CSVWriter` | — |
| Excel (`.xlsx`) | `ExcelReader` | `ExcelWriter` | `excel` |
| SPSS (`.sav`) | `SPSSReader` / `read_spss` | `SPSSWriter` | `pyreadstat` |
| Stata (`.dta`) | `StataReader` / `read_stata` | `StataWriter` | `pyreadstat` |
| R | — | `RScriptWriter` | — (writes CSV + JSON dict + R loader script) |
| JSON dictionary | `DictionaryReader` | `DictionaryWriter` | — |

## Variables vs. answers

A `Variable` carries the **definition** (`name`, `scale`, `labels`,
`missing_values`, `valid_range`, `role`, …). An answer is a row in the
collected `DataFrame`, keyed by `variable.name`.

When you simulate or deploy a survey, siamang derives the schema for the
generated dataset from the `VariableMap`. If you pass an explicit
`Questionnaire(variables=VariableMap([...]))`, that registry is the
source of truth; otherwise siamang auto-builds one by walking every
question.

## Expressions — `show_if`, `hide_if`, `skip_to`

Visibility gates accept either a string in the SurveyJS dialect
(`"age >= 18 AND gender == 2"`) or a typed `Expression` you build from
the `Variable` helpers:

```python
age >= 18                       # → Expression(">=", VarRef("age"), 18)
age.ge(18) & gender.eq(2)       # → Expression("and", ..., ...)
~ age.isin([18, 19])            # → NOT
sg.AND(age.ge(18), gender.eq(2), region.isin([1, 2]))
```

The typed form is preferred because:

- it is **type-checked** at construction;
- it can be **evaluated in Python** (`expr.evaluate(answers)`), which is
  what `survey.simulate()`, `survey.validate()`, and the React runtime's
  client-side evaluator all use;
- it serialises losslessly to JSON via `to_dict()` / `from_dict()`.

The same gate can be attached to:

| Level | Field(s) |
|-------|----------|
| `Page` | `show_if`, `hide_if` |
| `Block` | `show_if`, `hide_if` |
| `Question` | `show_if`, `hide_if`, `skip_to` (page or question id) |
| `Option` | `show_if`, `hide_if` |

An element is rendered iff `show_if` evaluates true (or is absent) and
`hide_if` does not (or is absent).

## Lifecycle scripts

`Script` injects a sandboxed JavaScript snippet that runs in the
respondent's browser at a chosen trigger:

| Trigger | When |
|---------|------|
| `onInit` | Once when the survey loads |
| `onPageEnter` | A page becomes visible |
| `onPageExit` | A page is left |
| `onQuestionShow` | A question becomes visible |
| `onAnswer` | An answer changes |
| `onSubmit` | The survey is submitted |
| `onRandomize` | Randomisation is requested |

Inside the snippet you have `answers`, `utils` (`shuffle`, `sample`,
`clamp`, `now`, `formatDate`), `api` (`get`, `post`), and `context`.
Built-in `Script.randomize_options`, `Script.randomize_pages`,
`Script.validate_fields_match`, `Script.timed_question` cover the
common cases.

## Pipeline diagram

```
                       ┌───────────────┐
                       │ Questionnaire │
                       └───────┬───────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────────┐    ┌──────────────┐
│   validate()  │    │     simulate()    │    │   deploy()   │
└───────────────┘    └────────┬──────────┘    └──────┬───────┘
                              │                       │
                              ▼                       ▼
                      ┌────────────┐         ┌────────────────┐
                      │ SurveyData │         │ DeployPipeline │
                      └──┬──────┬──┘         └───────┬────────┘
                  .analysis  .tables                 │
                         │      │                    │
                         ▼      ▼                    ▼
                    DataAnalysis · BannerTable   DeployResult
                                                     │
                                          .collect() │ .responses()
                                                     ▼
                                                 SurveyData
                                                     │
                                                     ▼
                                            export / analysis / IO
```

For a worked end-to-end example see the **[manual](../MANUAL.md)**, and
for a fully-featured sociological pipeline with pre-executed notebook see
**[`examples/full_pipeline/`](../examples/full_pipeline/)**.
