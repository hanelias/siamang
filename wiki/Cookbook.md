# Cookbook

Short, self-contained recipes for common tasks. Each assumes:

```python
import siamang as sg
```

For the underlying concepts, follow the cross-links; for a full narrative walkthrough
see [[Tutorial Full Pipeline|Tutorial-Full-Pipeline]].

---

## Visibility logic

See [[Visibility and Branching|Visibility-and-Branching]] for the full Expression DSL.

### Show a question only to adults

```python
age    = sg.Variable("age", scale="ratio")
income = sg.Variable("income", scale="ratio")

q_income = sg.NumericInput("Household income?", var=income, show_if=age.ge(18))
```

### Hide an option that doesn't apply to some respondents

`Option` accepts its own `show_if` / `hide_if`:

```python
gender = sg.Variable("gender", scale="nominal", labels={1: "Male", 2: "Female"})
fav    = sg.Variable("fav_color", scale="nominal",
                     labels={1: "Red", 2: "Blue", 3: "Pink", 4: "Green"})

q_color = sg.SingleChoice(
    "Pick a colour", var=fav,
    choices=[
        sg.Option(1, "Red"),
        sg.Option(2, "Blue"),
        sg.Option(3, "Pink",  hide_if=gender.eq(1)),                  # hide for men
        sg.Option(4, "Green", show_if=sg.AND(age.ge(18), gender.eq(2))),
    ],
)
```

### Composite conditions

```python
gate = sg.AND(
    age.ge(18),
    sg.OR(region.eq(1), region.eq(2)),
    sg.NOT(party.eq(99)),
)
sg.Page(name="political", items=[...], show_if=gate)
```

The same `gate` works on a `Page`, `Block`, `Question`, or `Option`. When both
`show_if` and `hide_if` are set, the element renders iff `show_if` is true **and**
`hide_if` is false.

---

## Quotas

See [[Quotas]]. A `Quota` caps responses for a particular variable value; pass a list
to `deploy(...)` as the `quota` option. When a submission matches a filled cell the
backend returns `{"status": "quota_full"}` and the frontend shows the closed screen.

```python
from siamang import Quota

quotas = [
    Quota("gender", target_value=1, limit=200),
    Quota("gender", target_value=2, limit=200),
    Quota("region", target_value=1, limit=400),   # cap on the Capital region
]

survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

Updating a `limit` between deploys is cheap — siamang reprovisions only when the
schema hash changes.

---

## Attaching media

`Media` attaches an image, audio, or video to a question or an option. See
[[Question Types|Question-Types]].

### Image beside a question

```python
sg.SingleChoice(
    "Which logo do you prefer?", var=logo,
    media=sg.Media("https://cdn.example.com/intro.png", caption="Compare side by side"),
)
```

### A gallery (list of media)

```python
sg.OpenText(
    "What do you see in these images?", var=description, multiline=True,
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

### Autoplaying video (forced muted)

```python
sg.NumericInput(
    "How long is the clip in seconds?", var=duration,
    media=sg.Media("https://cdn.example.com/intro.mp4",
                   autoplay=True, loop=False, controls=True),
)
```

---

## Pagination / one question per page

By default a `Page` shows all its items together. To render one question at a time
(a common mobile pattern), set the `one_question_per_page` deploy option — it maps to
SurveyJS's `questionsOnPageMode: "questionPerPage"`. See
[[Frontend and Theming|Frontend-and-Theming]].

```python
survey.deploy(
    backend="supabase", frontend="vercel",
    one_question_per_page=True,
)
```

The same option is accepted by `survey.compile(one_question_per_page=True)` if you
build the bundle manually. Other compile-level options forwarded the same way include
`language`, `show_progress`, and `allow_back`.

---

## Custom lifecycle scripts

See [[Scripts]]. A `Script` binds inline JavaScript to one of seven triggers
(`onInit`, `onPageEnter`, `onPageExit`, `onQuestionShow`, `onAnswer`, `onSubmit`,
`onRandomize`). Factory helpers cover the common cases:

```python
shuffle = sg.Script.randomize_options("q_party")
timer   = sg.Script.timed_question("q_party", seconds=30)
match   = sg.Script.validate_fields_match("email_1", "email_2",
                                          message="The two email addresses don't match.")

survey = sg.Questionnaire(title="…", pages=[...], scripts=[shuffle, timer, match])
```

A custom snippet sees `answers`, `utils` (shuffle, sample, clamp, now, formatDate),
`api` (get, post), and `context`:

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
survey = sg.Questionnaire(title="…", pages=[...], scripts=[log_dwell])
```

---

## Weighting and analysis

See [[Analysis]]. `with_weight(col)` returns a view whose **`analysis` accessor**
honours the weight (pass `weighted=True` per call); the declarative `data.report.*`
tables are unweighted. `simulate()` does not generate a weight column, so attach
one to the frame first:

```python
import numpy as np

data = survey.simulate(n=1000, seed=42)
frame = data.frame.assign(
    weight=np.random.default_rng(0).uniform(0.5, 1.5, len(data.frame))
)
data = data.with_frame(frame).with_weight("weight")

# Weighted statistics (analysis accessor)
data.analysis.mean("trust", weighted=True)
data.analysis.frequencies("trust", labels=True, weighted=True, normalize=True)
data.analysis.grouped_mean("trust", by="gender", weighted=True)
data.analysis.proportion_ci("trust", value=5, confidence=0.95, weighted=True)
data.analysis.effective_sample_size()   # ESS ≤ N

# Declarative tables remain unweighted
print(data.report.freq("trust").to_markdown())
```

### Scale reliability and indices

```python
data.scale_alpha(["trust_govt", "trust_courts", "trust_press"])     # Cronbach's α

data = data.create_index(
    "trust_index",
    items=["trust_govt", "trust_courts", "trust_press"],
    method="mean", label="General trust",
)
```

### Banner table for export

```python
banner = data.tables.banner(rows=["trust", "trust_local"],
                            columns=["gender", "region"], labels=True)
banner.export_xlsx("results.xlsx")
```

See [[Banner Tables|Banner-Tables]].

---

## Exporting to SPSS, Stata, and R

See [[Data Import and Export|Data-Import-and-Export]]. `SurveyData.export(fmt, path)`
is the high-level helper; the `siamang.io` writers give finer control. SPSS and Stata
round-trip variable labels, value labels, and missing-value codes.

```python
# High-level
data.export("spss",  path="out.sav")
data.export("stata", path="out.dta")
data.export("r",     path="out_R/")
data.export_dictionary("dict.json")
```

### Read SPSS, recode, write SPSS

```python
import pandas as pd
from siamang.io import read_spss, SPSSWriter

data = read_spss("input.sav")                                   # full metadata recovered
data = data.recode_values("age", {-1: pd.NA}).apply_missing_values()
SPSSWriter().write(data, "output.sav")                          # opens in SPSS untouched
```

### Export to R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
# Writes data.csv, dictionary.json, load_data.R. Then in R:
#   source("political_trust_R/load_data.R")
```

### CSV with a separate dictionary

CSV carries no metadata, so pair it with a JSON codebook:

```python
from siamang.io import CSVWriter, DictionaryWriter, CSVReader, DictionaryReader

CSVWriter().write(data, "responses.csv")
DictionaryWriter().write(data.variables, "dict.json")

# later …
restored = CSVReader().read("responses.csv")
restored = restored.__class__(frame=restored.frame,
                              variables=DictionaryReader().read("dict.json"))
```

---

## Custom backends and frontends

The deploy registry is driven by entry points, so a plugin only declares the entry
point and implements the abstract base. See [[Deployment]] for the adapter contracts.

```toml
# pyproject.toml of `my-siamang-plugin`
[project.entry-points."siamang.backends"]
mybackend = "my_pkg.backend:MyBackend"

[project.entry-points."siamang.frontends"]
mycdn = "my_pkg.frontend:MyCDNFrontend"
```

```python
import siamang as sg
sg.Questionnaire(...).deploy(backend="mybackend", frontend="mycdn")
```

---

See also: [[Tutorial Full Pipeline|Tutorial-Full-Pipeline]] ·
[[Visibility and Branching|Visibility-and-Branching]] · [[Quotas]] · [[Scripts]] ·
[[Analysis]] · [[Data Import and Export|Data-Import-and-Export]] · [[Deployment]] ·
[[API Reference Index|API-Reference-Index]]
