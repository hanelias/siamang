# siamang — Manual with examples

A single-file tour of every feature, by example. For the deep
reference (every class, every field), see [`docs/`](docs/index.md).

**Contents**

1. [Install](#install)
2. [Hello, siamang](#hello-siamang)
3. [Variables](#variables)
4. [Questions](#questions)
   - [Single choice](#single-choice)
   - [Multi-choice (array and wide)](#multi-choice-array-and-wide)
   - [Likert scale](#likert-scale)
   - [Numeric input](#numeric-input)
   - [Open text](#open-text)
   - [Matrix](#matrix)
   - [Ranking](#ranking)
5. [Visibility logic (`show_if`, `hide_if`)](#visibility-logic-show_if-hide_if)
6. [Pages, blocks, and navigation](#pages-blocks-and-navigation)
7. [Per-option visibility and media](#per-option-visibility-and-media)
8. [Quotas](#quotas)
9. [Lifecycle scripts](#lifecycle-scripts)
10. [Validate and lint](#validate-and-lint)
11. [Simulate a dataset](#simulate-a-dataset)
12. [Analyse the data](#analyse-the-data)
13. [Banner tables](#banner-tables)
14. [Import / export (CSV, Excel, SPSS, Stata, R)](#import--export-csv-excel-spss-stata-r)
15. [Preview locally](#preview-locally)
16. [Deploy (Supabase + Vercel)](#deploy-supabase--vercel)
17. [Customise the look (UIConfig)](#customise-the-look-uiconfig)
18. [Custom backends and frontends](#custom-backends-and-frontends)

---

## Install

```bash
pip install git+https://github.com/hanelias/siamang.git
```

That's it — every feature is included by default (Excel / SPSS / Stata
I/O, the local preview server, scipy-backed statistics, Supabase and
Vercel deploy).

---

## Hello, siamang

```python
import siamang as sg

age = sg.Variable("age", scale="ratio", label="Age")
fav = sg.Variable(
    "fav_color", scale="nominal", label="Favourite colour",
    labels={1: "Red", 2: "Blue", 3: "Green"},
)

survey = sg.Questionnaire(
    title="Hello, siamang",
    pages=[
        sg.Page(
            name="main", title="Tell us a bit about yourself",
            items=[
                sg.NumericInput("How old are you?", var=age, required=True),
                sg.SingleChoice("Favourite colour?", var=fav),
            ],
        ),
    ],
)
```

```bash
siamang validate hello.py
siamang preview  hello.py --port 8000
```

---

## Variables

```python
age = sg.Variable("age", scale="ratio", label="Age")

gender = sg.Variable(
    "gender", scale="nominal", label="Gender",
    labels={1: "Male", 2: "Female", 3: "Other"},
)

income = sg.Variable(
    "income", scale="ratio", label="Monthly income (USD)",
    missing_values=[-1, -2],
    missing_labels={-1: "Refused", -2: "Don't know"},
)

trust = sg.Variable(
    "trust", scale="ordinal", label="Trust in government",
    labels={1: "No trust", 5: "Full trust"},
    missing_values=[9],
)
```

| Argument | Purpose |
|----------|---------|
| `name` | Column name in the output dataset. |
| `scale` | `"nominal"` / `"ordinal"` / `"interval"` / `"ratio"`. |
| `label` | Human-readable variable label (codebook). |
| `labels` | `{code: label}` for nominal/ordinal vars. |
| `missing_values` | Codes treated as missing across all readers/writers. |
| `missing_labels` | Codes → labels for the missing-value table. |
| `missing` | Structured `tuple[MissingValue, ...]` (kind: refusal, dont_know, …). |
| `dtype`, `role`, `description`, `construct`, `source`, `valid_range` | Codebook metadata; surfaced in `SurveyData.codebook()`. |

Variables expose comparison helpers used in expressions: `age.ge(18)`,
`gender.eq(2)`, `region.isin([1, 2])`, etc. See
[`docs/reference/core.md#variable`](docs/reference/core.md#variable).

---

## Questions

Every question subclass binds a `Variable` (or many, for matrix and
wide multi-choice) to a respondent-facing prompt.

### Single choice

```python
q_gender = sg.SingleChoice(
    "What is your gender?", var=gender,
    display="buttons",          # "radio" (default) | "buttons" | "dropdown"
    required=True,
)
```

### Multi-choice (array and wide)

**Array mode** — one column, list of selected codes:

```python
hobbies = sg.Variable("hobbies", scale="nominal",
                     labels={1: "Music", 2: "Sport", 3: "Reading", 99: "None"})

q_hobbies = sg.MultiChoice(
    "Which hobbies do you have?", var=hobbies,
    min_answers=1, max_answers=3,
    exclusive=[99],            # picking "None" clears the others
)
```

**Wide mode** — one column per option (binary flags):

```python
sources = [sg.Variable(f"src_{n}", scale="nominal", labels={0: "No", 1: "Yes"},
                       label=f"Source {n}") for n in ("tv", "radio", "web")]

q_sources = sg.MultiChoice(
    "Where do you get news from?",
    vars=sources,                # keyword-only triggers wide mode
)
```

### Likert scale

```python
q_trust = sg.LikertScale(
    "How much do you trust the government?",
    var=trust, points=5,
    left_label="No trust", right_label="Full trust",
    na_option=True,             # show a "Not applicable" choice
)
```

### Numeric input

```python
q_age = sg.NumericInput(
    "How old are you?", var=age,
    display="input",            # or "slider"
    step=1, unit="years",
    required=True,
)
```

If `age.valid_range=(min, max)` is set, the React runtime forwards it
as the input's `min`/`max`.

### Open text

```python
explanation = sg.Variable("explanation", scale="nominal")

q_open = sg.OpenText(
    "Anything else you would like to add?", var=explanation,
    multiline=True, max_chars=500,
    placeholder="Optional comments…",
)
```

### Matrix

A matrix has one variable per row; all rows share a column scale.

```python
trust_dim = lambda name, label: sg.Variable(
    name, scale="ordinal",
    label=label,
    labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"},
)

q_trust_matrix = sg.Matrix(
    "How much do you trust each of the following?",
    var=[
        trust_dim("trust_govt",   "The government"),
        trust_dim("trust_courts", "The courts"),
        trust_dim("trust_media",  "The press"),
    ],
)
```

### Ranking

```python
brands = sg.Variable("brand_rank", scale="ordinal",
                    labels={1: "Acme", 2: "Globex", 3: "Initech"})

q_rank = sg.Ranking(
    "Rank these brands from best to worst",
    var=brands, max_ranked=3,
)
```

---

## Visibility logic (`show_if`, `hide_if`)

Every level accepts both `show_if` and `hide_if`. An element is
rendered iff `show_if` evaluates to true (or is unset) and `hide_if`
does not (or is unset).

| Level | Field |
|-------|-------|
| `Page` | `show_if`, `hide_if` |
| `Block` | `show_if`, `hide_if` |
| `Question` | `show_if`, `hide_if`, `skip_to` |
| `Option` | `show_if`, `hide_if` |

```python
# Typed expressions (preferred — type-checked + evaluable in Python)
q_kids = sg.NumericInput(
    "How many children?", var=num_children,
    show_if=has_children.eq(1),
    hide_if=age.lt(18),
)

# Composite conditions
gate = sg.AND(age.ge(18), sg.OR(region.eq(1), region.eq(2)),
              sg.NOT(party.eq(99)))
sg.Page(name="political", items=[...], show_if=gate)

# Operator overloads
sg.Page(name="adults", items=[...], show_if=age >= 18)
sg.Page(name="not_kids", items=[...], show_if=~ age.lt(13))

# String form (SurveyJS dialect — preserved verbatim, not evaluated in Python)
sg.Page(name="adults", items=[...], show_if="age >= 18")
```

---

## Pages, blocks, and navigation

```python
demographics = sg.Block(
    title="About you",
    items=[q_age, q_gender, q_region],
    randomize=False,
)

attitudes = sg.Block(
    title="Political attitudes",
    items=[q_trust, q_party],
    show_if=age.ge(18),
)

survey = sg.Questionnaire(
    title="Political Trust — 2026",
    pages=[
        sg.Page(name="welcome",  items=[…]),
        sg.Page(name="main",     items=[demographics, attitudes]),
        sg.Page(
            name="adult_only",
            items=[…],
            show_if=age.ge(18),
            default_next="thanks",
        ),
        sg.Page(name="thanks",   items=[…]),
    ],
)
```

`Page.next_if=[("expr", "next_page_name"), ...]` lets you encode
conditional navigation; `default_next` is the fallback. Block-level
randomisation is `Page(randomize_blocks=True)`.

---

## Per-option visibility and media

Pass `choices=[Option(...)]` to unlock per-option `show_if`/`hide_if`
and media:

```python
from siamang import Option, Media

q_color = sg.SingleChoice(
    "Pick a colour",
    var=fav,
    media=Media("https://cdn.example.com/intro.mp4",
                caption="Watch before answering."),
    choices=[
        Option(1, "Red",   media=Media("https://cdn.example.com/red.png")),
        Option(2, "Blue",  media=Media("https://cdn.example.com/blue.png")),
        Option(3, "Pink",  hide_if=gender.eq(1)),
        Option(4, "Green", show_if=age.ge(18)),
    ],
)
```

`Media.kind` defaults from the URL extension (`png/jpg/...` → image,
`mp4/webm/...` → video, `mp3/wav/...` → audio). The library refuses to
guess for URLs without an extension — pass `kind=` explicitly.

---

## Quotas

```python
from siamang import Quota

quotas = [
    Quota("gender", target_value=1, limit=200),
    Quota("gender", target_value=2, limit=200),
    Quota("region", target_value=1, limit=400),   # cap on Capital
]

survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

When a respondent's submission matches a filled cell the backend
returns `{"status": "quota_full"}`; the frontend shows the closed
screen.

---

## Lifecycle scripts

```python
shuffle_party = sg.Script.randomize_options("q_party")
timer         = sg.Script.timed_question("q_party", seconds=30)
match_emails  = sg.Script.validate_fields_match("email_1", "email_2",
                                                message="Emails don't match.")

custom = sg.Script(
    name="log_dwell",
    trigger="onPageExit",
    code="""
        const ms = Date.now() - (context.entered ?? Date.now());
        api.post('/dwell', { page: context.page_name, ms });
    """,
)

survey = sg.Questionnaire(
    title="…", pages=[…],
    scripts=[shuffle_party, timer, match_emails, custom],
)
```

Triggers: `onInit`, `onPageEnter`, `onPageExit`, `onQuestionShow`,
`onAnswer`, `onSubmit`, `onRandomize`. Each snippet sees
`answers`, `utils` (shuffle, sample, clamp, now, formatDate),
`api` (get, post), and `context`.

---

## Validate and lint

```bash
$ siamang validate hello.py
OK: Questionnaire<Hello, siamang> with 2 questions
```

```python
survey.validate(strict=True)
# Raises ValueError on any structural problem.
# strict=True also raises on lint(level="strict") errors.

for warning in survey.lint(level="strict"):
    print(warning.code, warning.severity, warning.message)
```

Checks include: duplicate question ids, broken `skip_to` targets,
unreachable / cyclic page navigation, unknown variables in any
`show_if` / `hide_if`, expression evaluability, script targets, and
variable registry coherence.

---

## Simulate a dataset

```python
data = survey.simulate(n=500, seed=42)
print(data.frame.head())
print(data.codebook())
```

`simulate()` honours visibility (invisible questions and choices are
not sampled), respects `min_answers` / `max_answers` / `exclusive` on
multi-choice, samples from `choices=` when present, falls back to
`Variable.labels` otherwise.

---

## Analyse and Report Data

Siamang provides a dual-layer analysis API:
1. **High-Level Declarative Reporting (`data.report.*` & `data.plot.*`)**: Recommended for most use cases. Returns rich, formatted table and chart objects that automatically handle value labels, weights, and standard statistical tests.
2. **Low-Level Statistical Methods (`data.analysis.*`)**: For direct access to raw statistical metrics, custom confidence intervals, and scale reliability tests.

### High-Level Declarative Reporting (Recommended)

```python
# Frequencies
freq_table = data.report.freq("trust")
print(freq_table.to_markdown())
freq_table.to_dataframe()

# Crosstabs (automatically runs Chi-square / Cramer's V tests)
cross_table = data.report.crosstab("gender", "party")
print(cross_table.to_markdown())

# Group Means
means_table = data.report.means("age", by="party")
print(means_table.to_markdown())

# Declarative Plotting
data.plot.bar("trust").save("trust_bar.png")
data.plot.boxplot("age", by="party").save("age_by_party.png")
data.plot.heatmap(["trust_govt", "trust_courts", "trust_media"]).save("trust_heatmap.png")
data.plot.scatter("age", "income").save("age_income_scatter.png")
```

### Low-Level Statistical Methods

```python
ana = data.analysis

ana.mean("age")                                # 42.7
ana.median("age")                              # 41.0

# Returns raw pandas objects
ana.frequencies("trust", labels=True, normalize=True)
ana.crosstab("gender", "party", normalize="columns", chi2=True)

ana.proportion_ci("trust", value=5, confidence=0.95)
data.scale_alpha(["trust_govt", "trust_courts", "trust_media"])

# Weighted analysis
data = data.with_weight("weight")
data.analysis.frequencies("party", weighted=True)
data.analysis.effective_sample_size()
```

Available tests (require `scipy`): `kruskal`, `mannwhitney`,
`spearman`, and `crosstab(chi2=True, cramers_v=True, phi=True)`.

---

## Banner tables

```python
banner = data.tables.banner(
    rows=["trust", "trust_local"],
    columns=["gender", "region"],
    labels=True,
)
banner.export_xlsx("banner.xlsx")
banner.export_csv("banner.csv")
```

---

## Import / export (CSV, Excel, SPSS, Stata, R)

```python
# Export
data.export("csv",   path="out.csv")
data.export("xlsx",  path="out.xlsx")
data.export("spss",  path="out.sav")
data.export("stata", path="out.dta")
data.export("r",     path="out_R/")
data.export_dictionary("dict.json")

# Read
from siamang.io import read_spss, read_stata, CSVReader, DictionaryReader

data2 = read_spss("input.sav")        # variables reconstructed from metadata
data3 = read_stata("input.dta")
csv   = CSVReader().read("input.csv") # CSV carries data only; pair with JSON dict:
csv   = csv.__class__(
    frame=csv.frame,
    variables=DictionaryReader().read("dict.json"),
)
```

SPSS and Stata I/O round-trip variable labels, value labels,
missing-value codes, and column formats so the same file can be opened
in SPSS / Stata / siamang interchangeably.

---

## Preview locally

```bash
siamang preview hello.py --port 8000 --open
```

Spins up a FastAPI server with the React
frontend and SQLite backend. Responses land in `survey.db`. Read them
from Python:

```python
from siamang.deploy.backends.local import LocalBackend

backend = LocalBackend(path="survey.db")
df = backend.get_responses(survey_id="<id from server log>")
```

---

## Deploy (Supabase + Vercel)

First time only — write the config file:

```bash
siamang init
```

Then:

```bash
siamang deploy hello.py --profile production
```

Or programmatically:

```python
result = survey.deploy(
    backend="supabase",
    frontend="vercel",
    backend_kwargs={
        "url":         "https://abcdef.supabase.co",
        "anon_key":    "...",
        "service_key": "...",
    },
    frontend_kwargs={
        "token":        "...",
        "project_name": "political-trust-2026",
    },
    quota=quotas,
)
print(result.url, result.dashboard)
df = result.collect()   # pull responses any time later
```

Environment variables: `SIAMANG_SUPABASE_URL`,
`SIAMANG_SUPABASE_ANON_KEY`, `SIAMANG_SUPABASE_SERVICE_KEY`,
`VERCEL_TOKEN`. Legacy `SURVLIB_*` names are also accepted as fallback.

---

## Customise the look (UIConfig)

```python
from siamang.frontend import UIConfig

ui = UIConfig(
    institution_name="Independent Polling Lab",
    study_subtitle="Wave 4 · April 2026",
    logo_url="https://cdn.example.com/logo.svg",
    primary_color="#a8324b",
    accent_color="#1f3a93",
    font_pair="mixed",          # serif headings + sans body
    progress_style="dots",
    default_theme="system",     # respects prefers-color-scheme
    require_access_code=True,
    access_codes=["wave1-001", "wave1-002"],
    enable_analytics=True,      # Vercel Analytics if frontend=="vercel"
    estimated_minutes=8,
    privacy_url="https://example.com/privacy",
    contact_email="research@example.com",
    ethics_statement="IRB #2026-…",
)

survey.deploy(backend="supabase", frontend="vercel", ui=ui)
```

Full field reference: [`docs/reference/frontend.md#uiconfig`](docs/reference/frontend.md#uiconfig).

---

## Custom backends and frontends

Backends and frontends are discovered through Python entry points. A
third-party plugin only needs to declare the entry point and implement
the abstract `BackendAdapter` / `FrontendAdapter`.

```toml
# my_siamang_plugin/pyproject.toml
[project.entry-points."siamang.backends"]
mybackend = "my_pkg.backend:MyBackend"

[project.entry-points."siamang.frontends"]
mycdn = "my_pkg.frontend:MyCDNFrontend"
```

```python
survey.deploy(backend="mybackend", frontend="mycdn")
```

See [`docs/reference/deploy.md`](docs/reference/deploy.md) for the
adapter contracts.

---

## Where to go next

- **[`docs/index.md`](docs/index.md)** — full documentation index.
- **[`docs/reference/core.md`](docs/reference/core.md)** — every class
  and function in `siamang.core`.
- **[`docs/reference/data.md`](docs/reference/data.md)** — analysis
  layer.
- **[`docs/reference/io.md`](docs/reference/io.md)** — readers and
  writers.
- **[`docs/reference/frontend.md`](docs/reference/frontend.md)** —
  bundle builder, runtimes, `UIConfig`.
- **[`docs/reference/deploy.md`](docs/reference/deploy.md)** — pipeline,
  backends, frontends.
- **[`docs/reference/cli.md`](docs/reference/cli.md)** — every CLI
  subcommand and flag.
- **[`docs/cookbook.md`](docs/cookbook.md)** — short recipes.
- **[`docs/development.md`](docs/development.md)** — building from
  source, running tests.
