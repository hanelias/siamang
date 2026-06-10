# Simulation

Every `Questionnaire` can generate synthetic respondents with a single call.
Simulation is the fastest way to test a survey end to end before you collect a
single real response: you get a fully-populated [[Working with Data|Working-with-Data]]
`SurveyData` object you can immediately run [[Analysis]], [[Reporting Tables|Reporting-Tables]],
and [[Reporting Charts|Reporting-Charts]] against.

---

## `Questionnaire.simulate`

```python
from siamang.core import Questionnaire

def simulate(self, n: int = 100, seed: int | None = 42) -> "SurveyData": ...
```

Generates `n` synthetic respondents and returns a `SurveyData` whose `frame`
holds one row per respondent, with the questionnaire's `VariableMap` and the
questionnaire itself attached.

**Parameters**

- **`n`** — number of synthetic respondents (default `100`).
- **`seed`** — RNG seed for reproducibility (default `42`). Pass `seed=None`
  for a fresh draw each call; pass a fixed integer to get the same dataset every
  time — invaluable in tests and documentation.

If the questionnaire has no explicit `variables` registry, `simulate` builds one
on the fly from the bound question variables, so the returned `SurveyData` always
carries metadata (labels, scales) for reporting.

### How values are drawn

Each question type produces plausible values:

| Question type | Simulated value |
| :--- | :--- |
| `NumericInput` | uniform integer within the variable's `valid_range` (else `18–70`). |
| `LikertScale` | uniform integer in `1..points`. |
| `SingleChoice` | a random option code. |
| `MultiChoice` | a random subset honoring `min_answers`/`max_answers`/`exclusive`. |
| `Ranking` | a random ranked subset up to `max_ranked`. |
| `Matrix` | a random code per sub-variable from its labels. |
| `OpenText` | the placeholder string `"sample text"`. |

> **Note:** Simulation produces values drawn at random, *not* from any modeled
> correlation structure. Use it to exercise plumbing, validate logic, and
> preview report layouts — not to study real associations.

---

## Skip logic is respected

When the questionnaire is defined with **pages**, `simulate` evaluates each
respondent's answers row-by-row in page order and honors visibility logic:

- A page's `show_if`/`hide_if` is evaluated against the answers collected *so
  far*. If the page is hidden, **every variable on it is set to `NaN`** for that
  respondent.
- Each question's own `show_if`/`hide_if` is likewise evaluated; hidden
  questions produce `NaN`.

This means simulated data reproduces the *missingness pattern* your real data
will have. A question gated behind `consent == 1` will only have values for the
respondents whose simulated `consent` is `1`. See
[[Visibility and Branching|Visibility-and-Branching]] for the expression DSL.

```python
from siamang.core import Variable, SingleChoice, LikertScale, Page, Questionnaire

consent = Variable("consent", scale="nominal", label="Consent", labels={1: "Yes", 0: "No"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

survey = Questionnaire(
    title="Autonomy Study",
    pages=[
        Page(name="consent", items=[SingleChoice("Do you consent?", var=consent, required=True)]),
        Page(name="main", items=[LikertScale("How much autonomy?", var=autonomy, points=5)],
             show_if=consent.eq(1)),   # only consenters see this page
    ],
)

data = survey.simulate(n=200, seed=123)

print(data.frame.shape)                 # (200, 2)
print(data.frame["consent"].value_counts(dropna=False).to_dict())
# autonomy is NaN for every respondent whose consent != 1:
print(int(data.frame["autonomy"].isna().sum()))
```

> Page-level skip logic is only applied in **pages mode**. In the legacy flat
> (`blocks`) mode every question is answered for every respondent.

---

## Using simulated data for testing and preview

Because `simulate` returns a real `SurveyData`, the full analysis and reporting
stack is available immediately:

```python
# Publication-ready frequency table straight from synthetic data
print(data.report.freq("autonomy").to_markdown())

# Quick descriptive: how complete is each variable?
print(data.describe_variables())

# Validate the synthetic frame against its metadata (should be clean)
issues = data.validate()
assert all(i.severity != "error" for i in issues)
```

Typical uses:

- **Unit tests** — seed the RNG (`seed=42`) and assert on report output or
  validation results without any network or database.
- **Report layout previews** — confirm tables and charts render before real data
  arrives.
- **Demos and documentation** — reproducible figures with a fixed seed.

---

See also: [[Working with Data|Working-with-Data]] · [[Analysis]] · [[Validation and Linting|Validation-and-Linting]] · [[Visibility and Branching|Visibility-and-Branching]] · [[Reporting Tables|Reporting-Tables]]
