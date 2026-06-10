# Installation

`siamang` is published to PyPI as a single package. Installing it pulls in every
core dependency — the analysis stack, the local preview server, the I/O formats,
and the Supabase/Vercel deployment clients. A handful of heavier or
service-specific features live behind **optional extras**.

## Requirements

- **Python 3.11+** (3.11, 3.12, and 3.13 are supported and tested).
- A POSIX or Windows environment — `siamang` is OS-independent and ships with
  type hints (`py.typed`).

## Install from PyPI

```bash
pip install siamang
```

That is everything you need to define surveys, validate and lint them, simulate
synthetic data, run the local preview server, deploy to Supabase + Vercel, and
round-trip data through CSV/Excel/SPSS/Stata/R.

## Optional extras

Extras are declared in `pyproject.toml` and installed with the usual
`pip install "siamang[extra]"` syntax.

| Extra | Install | What it adds |
| :--- | :--- | :--- |
| `charts` | `pip install "siamang[charts]"` | `matplotlib` + `seaborn` — required for the `data.plot.*` chart accessors (`bar`, `boxplot`, `heatmap`, `scatter`). |
| `gsheets` | `pip install "siamang[gsheets]"` | Google API client libraries for the Google Sheets backend. |
| `dev` | `pip install "siamang[dev]"` | `ruff`, `mypy`, `pytest`, plus `siamang[charts]` — the full contributor toolchain. |

> **Legacy extras.** The names `all`, `excel`, `pyreadstat`, `server`,
> `supabase`, `vercel`, and `scipy` still resolve (they are kept for old install
> scripts) but are now **empty** — their dependencies are bundled with the base
> package, so these extras are no-ops.

### Core dependencies (installed automatically)

| Package | Version | Purpose |
| :--- | :--- | :--- |
| `pandas` | ≥ 2.0 | Data model and `SurveyData` backbone |
| `scipy` | ≥ 1.11 | Statistical tests (chi-square, t-test, ANOVA, …) |
| `openpyxl` | ≥ 3.1 | Excel (`.xlsx`) import/export |
| `pyreadstat` | ≥ 1.2 | SPSS (`.sav`) and Stata (`.dta`) import/export |
| `fastapi` | ≥ 0.110 | Local preview server (`siamang preview`) |
| `uvicorn` | ≥ 0.29 | ASGI server for the local preview |
| `markdown` | ≥ 3.5 | `Report.to_html` rendering |
| `tabulate` | ≥ 0.9 | `to_markdown()` table output |
| `supabase` | ≥ 2.0 | Supabase backend |
| `requests` | ≥ 2.31 | HTTP client for Netlify/Vercel deploy APIs |

### Charts extra

```bash
pip install "siamang[charts]"
```

| Package | Version | Purpose |
| :--- | :--- | :--- |
| `matplotlib` | ≥ 3.7 | Chart rendering |
| `seaborn` | ≥ 0.13 | Statistical visualization helpers |

Charts are optional: if you only use tables (`data.report.freq()`,
`data.report.crosstab()`), matplotlib is not needed. A clear error message guides
you if you call a chart method without it.

### Google Sheets extra

```bash
pip install "siamang[gsheets]"
```

| Package | Version | Purpose |
| :--- | :--- | :--- |
| `google-auth` | ≥ 2.0 | Service-account authentication |
| `google-auth-httplib2` | ≥ 0.1 | HTTP transport for Google APIs |
| `google-api-python-client` | ≥ 2.0 | Google Sheets and Drive API clients |

## Editable / development install

Clone the repository and install in editable mode with the `dev` extra to get the
linter, type checker, and test runner:

```bash
git clone https://github.com/hanelias/siamang.git
cd siamang
pip install -e ".[dev]"
```

You can also install the latest unreleased code straight from Git:

```bash
pip install "git+https://github.com/hanelias/siamang.git"
```

## Verifying the install

Confirm the package imports and check the version:

```python
import siamang as sg

print(sg.__version__)        # e.g. "0.5.0"
print(sg.SingleChoice)        # <class 'siamang.core.question.SingleChoice'>
```

The package installs a console entry point named `siamang`. Confirm the CLI is on
your `PATH`:

```bash
siamang --help
```

A quick end-to-end smoke test — define a one-question survey and simulate it
without any backend:

```python
import siamang as sg

age = sg.Variable("age", scale="ratio", label="Age")
survey = sg.Questionnaire(
    title="Smoke test",
    pages=[sg.Page("main", items=[sg.NumericInput("How old are you?", var=age)])],
)
survey.validate()                 # raises if anything is wrong
data = survey.simulate(n=50)      # synthetic respondents — no server needed
print(data.frame.head())
```

## See also

- [[Quickstart]] — build and run your first survey end to end.
- [[Core Concepts|Core-Concepts]] — the research-as-code philosophy and data model.
- [[CLI Reference|CLI-Reference]] — every `siamang` command.
- [[Reporting Charts|Reporting-Charts]] — what the `charts` extra unlocks.
