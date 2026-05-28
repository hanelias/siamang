# Getting started

## Install

siamang requires **Python 3.11+**.

```bash
pip install git+https://github.com/hanelias/siamang.git
```

That's it — every feature is included out of the box:

| Comes with | What it enables |
|------------|-----------------|
| `pandas` | Data model, analysis |
| `fastapi`, `uvicorn` | `siamang preview` local server |
| `openpyxl` | Excel reader / writer |
| `pyreadstat` | SPSS `.sav` and Stata `.dta` I/O |
| `scipy` | Chi-square, Kruskal-Wallis, Mann-Whitney, Spearman |
| `supabase`, `requests` | Supabase backend / Vercel deploy |

(The old `siamang[server]`, `siamang[excel]`, `siamang[all]`, … install
commands still work — they're no-ops now.)

## Your first survey

Save the following as `hello.py`:

```python
import siamang as sg

age = sg.Variable("age", scale="ratio", label="Age")
fav = sg.Variable(
    "fav_color", scale="nominal",
    label="Favourite colour",
    labels={1: "Red", 2: "Blue", 3: "Green"},
)

survey = sg.Questionnaire(
    title="Hello, siamang",
    pages=[
        sg.Page(
            name="main",
            title="Tell us a bit about yourself",
            items=[
                sg.NumericInput("How old are you?", var=age, required=True),
                sg.SingleChoice("What is your favourite colour?", var=fav),
            ],
        ),
    ],
)
```

The CLI looks for a module-level `survey` variable (you can override with
`--attribute`):

```bash
siamang validate hello.py
# → "OK" if the questionnaire is well-formed; lists problems otherwise.

siamang preview hello.py --port 8000
# → http://127.0.0.1:8000 — fill the survey in your browser, responses
#   land in survey.db (SQLite).

siamang deploy hello.py --backend supabase --frontend vercel
# → provisions a Supabase project and publishes the static frontend to
#   Vercel; prints the public URL.
```

## Try it without a server — `simulate`

You don't need a backend to start exploring the analysis layer. Generate
a synthetic dataset:

```python
from hello import survey

data = survey.simulate(n=500, seed=42)
print(data.frame.head())

# High-level declarative reporting
print(data.report.freq("fav_color").to_markdown())

# For low-level statistical methods (e.g. data.analysis.frequencies), see docs/reference/data.md
```

## Export to your stats package

```python
data.export("csv",   path="hello.csv")
data.export("xlsx",  path="hello.xlsx")
data.export("spss",  path="hello.sav")
data.export("stata", path="hello.dta")
data.export("r",     path="hello_R/")            # CSV + JSON dict + .R loader
```

Round-trip: `SPSSReader().read("hello.sav")` gives you a `SurveyData`
back with all variable labels, value labels, and missing-value
conventions intact.

## Where to go next

- **[`examples/full_pipeline/`](../examples/full_pipeline/)** — a complete,
  fully worked sociological research pipeline. Includes a pre-executed
  Jupyter notebook (`full_pipeline_demo.ipynb`) showcasing variables,
  blocks, conditional pages, local deployment, data simulation,
  and comprehensive declarative reporting.
- **[Manual with examples](../MANUAL.md)** — single-file tour of every
  feature.
- **[Concepts](concepts.md)** — the data model end-to-end.
- **[Reference](reference/core.md)** — every public class and function.
- **[Cookbook](cookbook.md)** — short recipes for common tasks.
