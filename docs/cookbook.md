# Cookbook

Short, self-contained recipes for common tasks. Each example assumes:

```python
import siamang as sg
```

---

## Visibility logic

### Show a question only to adults

```python
age    = sg.Variable("age", scale="ratio")
income = sg.Variable("income", scale="ratio")

q_income = sg.NumericInput("Household income?", var=income,
                           show_if=age.ge(18))
```

### Hide an option that doesn't apply

```python
status = sg.Variable("status", scale="nominal", labels={1: "Employed", 2: "Other"})
q_employer = sg.OpenText(
    "Who do you work for?",
    var=sg.Variable("employer", scale="nominal"),
    show_if=status.eq(1),
)
```

### Per-option visibility (Option dataclass)

```python
gender = sg.Variable("gender", scale="nominal", labels={1: "Male", 2: "Female"})
fav = sg.Variable("fav_color", scale="nominal",
                  labels={1: "Red", 2: "Blue", 3: "Pink", 4: "Green"})

q_color = sg.SingleChoice(
    "Pick a colour",
    var=fav,
    choices=[
        sg.Option(1, "Red"),
        sg.Option(2, "Blue"),
        sg.Option(3, "Pink",  hide_if=gender.eq(1)),       # hide for men
        sg.Option(4, "Green", show_if=sg.AND(age.ge(18), gender.eq(2))),
    ],
)
```

### Both `show_if` and `hide_if` on the same element

When both are set, the element is rendered iff `show_if` is true **and**
`hide_if` is false.

```python
sg.Page(
    name="adults_capital",
    items=[...],
    show_if=age.ge(18),
    hide_if=region.eq(99),   # mask test region
)
```

### Composite expressions

```python
gate = sg.AND(
    age.ge(18),
    sg.OR(region.eq(1), region.eq(2)),
    sg.NOT(party.eq(99)),
)

sg.Page(name="political", items=[...], show_if=gate)
```

The same `gate` is fine in `Block.show_if`, `Question.show_if`,
`Option.show_if`, or as a `next_if` predicate.

### Page-level branching

```python
sg.Page(
    name="adult_consent",
    items=[q_consent],
    next_if=[("consent == 1", "main"), ("consent == 0", "exit")],
    default_next="main",
)
```

`next_if` accepts SurveyJS-string conditions for now (the strings are
echoed into the runtime payload verbatim). For programmatic control,
use `show_if` / `hide_if` and let the natural page order drive
navigation.

---

## Quotas

### Equal cells

```python
quotas = [
    sg.Quota("gender", 1, limit=200),
    sg.Quota("gender", 2, limit=200),
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

### Tighten one cell over time

Add or change quotas between deploys — siamang reprovisions only when
the schema hash changes, so updating a `limit` is a cheap operation.

---

## Media

### Image next to a question

```python
sg.SingleChoice(
    "Which logo do you prefer?",
    var=logo,
    media=sg.Media("https://cdn.example.com/intro.png", caption="Compare side by side"),
)
```

### Multiple media (gallery)

`Question.media` accepts a list:

```python
sg.OpenText(
    "What do you see in these images?",
    var=description,
    multiline=True,
    media=[
        sg.Media("https://cdn.example.com/a.jpg", alt="Image A"),
        sg.Media("https://cdn.example.com/b.jpg", alt="Image B"),
    ],
)
```

### Audio cue per option

```python
sg.SingleChoice(
    "Which jingle do you like better?",
    var=sg.Variable("jingle", scale="nominal", labels={1: "First", 2: "Second"}),
    choices=[
        sg.Option(1, "First",  media=sg.Media("https://cdn.example.com/j1.mp3")),
        sg.Option(2, "Second", media=sg.Media("https://cdn.example.com/j2.mp3")),
    ],
)
```

### Video that autoplays muted

```python
sg.NumericInput(
    "How long is the clip in seconds?",
    var=duration,
    media=sg.Media(
        "https://cdn.example.com/intro.mp4",
        autoplay=True,   # forces muted in the runtime
        loop=False,
        controls=True,
    ),
)
```

---

## Lifecycle scripts

### Randomise answer order

```python
survey = sg.Questionnaire(
    title="…",
    pages=[…],
    scripts=[sg.Script.randomize_options("q_party")],
)
```

### Cross-field validation

```python
sg.Script.validate_fields_match(
    "email_1", "email_2",
    message="The two email addresses don't match.",
)
```

### Custom snippet

```python
log_dwell = sg.Script(
    name="log_dwell",
    trigger="onPageExit",
    code="""
        const entered = context.entered ?? Date.now();
        const dwell_ms = Date.now() - entered;
        api.post('/diagnostics', {
            survey_id: context.survey_id,
            page: context.page_name,
            dwell_ms,
        });
    """,
)
```

---

## Analysis

### Frequencies with labels and weighting

```python
data = survey.simulate(n=1000, seed=42).with_weight("weight")
# High-level declarative reporting (recommended)
print(data.report.freq("trust", weighted=True).to_markdown())

# Low-level statistical methods
data.analysis.frequencies("trust", labels=True, weighted=True, normalize=True)
```

### Weighted crosstab + Chi-square

```python
# High-level declarative reporting (includes Chi-square / Cramers V by default)
print(data.report.crosstab("gender", "party", weighted=True).to_markdown())

# Low-level statistical methods
tab, stats = data.analysis.crosstab(
    "gender", "party",
    normalize="columns",
    chi2=True, cramers_v=True,
    weighted=True, labels=True,
)
```

### Confidence interval for a proportion

```python
# Low-level statistical methods
data.analysis.proportion_ci("trust", value=5, confidence=0.95, weighted=True)
# → {"proportion": 0.18, "ci_low": 0.16, "ci_high": 0.21, "n": 1000}
```

### Effective sample size

```python
# Low-level statistical methods
data.with_weight("weight").analysis.effective_sample_size()
# → ESS ≤ N — drops as weighting becomes more uneven
```

### Cronbach's α for a scale

```python
data.scale_alpha(["trust_govt", "trust_courts", "trust_press"])
```

### Compose an index

```python
data = data.create_index(
    "trust_index",
    items=["trust_govt", "trust_courts", "trust_press"],
    method="mean",
    label="General trust",
)
```

### Banner table for export

```python
banner = data.tables.banner(
    rows=["trust", "trust_local"],
    columns=["gender", "region"],
    labels=True,
)
banner.export_xlsx("results.xlsx")
```

---

## Data I/O

### Read SPSS, modify, write SPSS

```python
from siamang.io import read_spss, SPSSWriter

data = read_spss("input.sav")
data = data.recode_values("age", {-1: pd.NA}).apply_missing_values()
SPSSWriter().write(data, "output.sav")
```

### CSV → SurveyData with metadata

CSV doesn't carry metadata. Pair it with a JSON dictionary:

```python
from siamang.io import CSVReader, DictionaryReader

data = CSVReader().read("responses.csv")
data = data.with_frame(data.frame).__class__(
    frame=data.frame,
    variables=DictionaryReader().read("dict.json"),
)
```

### Export to R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
# Writes data.csv, dictionary.json, load_data.R
# Then in R:  source("political_trust_R/load_data.R")
```

---

## Custom backends and frontends

The deploy registry uses entry points. From your package:

```toml
# pyproject.toml of `my-siamang-plugin`
[project.entry-points."siamang.backends"]
mybackend = "my_pkg.backend:MyBackend"

[project.entry-points."siamang.frontends"]
mycdn = "my_pkg.frontend:MyCDNFrontend"
```

Then in user code:

```python
import siamang as sg
sg.Questionnaire(...).deploy(backend="mybackend", frontend="mycdn")
```

See the abstract bases in
[`reference/deploy.md`](reference/deploy.md) for the contract.
