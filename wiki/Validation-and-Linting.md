# Validation and Linting

Before you simulate, deploy, or analyze a survey, siamang can check it for
**hard errors** (`validate`) and **soft warnings** (`lint`). Validation guards
the structural invariants a questionnaire must satisfy; linting surfaces stylistic
and best-practice issues that won't crash the pipeline but probably indicate a
mistake. Both run in pure Python and back the [[CLI Reference|CLI-Reference]]
`siamang validate` command.

---

## `Questionnaire.validate`

```python
from siamang.core import Questionnaire

def validate(self, strict: bool = False) -> None: ...
```

Raises `ValueError` on the first structural problem it finds; returns `None`
when the questionnaire is sound. It is intentionally strict about anything that
would produce a broken survey:

- **Duplicate question IDs** and **duplicate variable names**.
- **Unknown `skip_to` targets** — a question may only skip to a known question
  ID or page name.
- **Page integrity** (pages mode): no empty/duplicate page names, every
  `show_if`/`hide_if`/`next_if` expression references only known variables and
  is itself evaluable, all navigation targets exist, every page is reachable
  from the first page, and the navigation graph contains **no cycles**.
- **Export-safety** of page `show_if` expressions for the SurveyJS frontend.
- **Script triggers/targets** — each script must use a known trigger and point
  at a real question or page.
- **Registry consistency** — if the questionnaire carries a `VariableMap`, every
  question variable must be the same instance registered there.

### `strict=True`

With `strict=True`, `validate` additionally runs `lint(level="strict")` and
**promotes any lint result with `severity == "error"` into a `ValueError`**.
This is how you fail a build on issues such as a `LikertScale` bound to a
non-ordinal variable. See the [[Visibility and Branching|Visibility-and-Branching]]
page for the expression rules that validation enforces.

```python
from siamang.core import Variable, LikertScale, SingleChoice, Page, Questionnaire

consent = Variable("consent", scale="nominal", label="Consent", labels={1: "Yes", 0: "No"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

survey = Questionnaire(
    title="Autonomy Study",
    pages=[
        Page(name="consent", items=[SingleChoice("Do you consent?", var=consent, required=True)]),
        Page(name="main", items=[LikertScale("How much autonomy?", var=autonomy, points=5)],
             show_if=consent.eq(1)),
    ],
)

survey.validate()              # returns None — the survey is structurally valid
survey.validate(strict=True)   # also fails on strict-level lint *errors*
```

---

## `Questionnaire.lint`

```python
def lint(self, level: str = "basic") -> list[LintWarning]: ...
```

Returns a list of `LintWarning` objects (never raises, except on an invalid
`level`). Pass `level="basic"` (default) or `level="strict"`. Unlike `validate`,
linting reports *all* findings at once so you can triage them.

### `LintWarning`

```python
from siamang.core.questionnaire import LintWarning

@dataclass(frozen=True, slots=True)
class LintWarning:
    code: str            # machine-readable, e.g. "EMPTY_PAGE"
    severity: str        # "warning" or "error"
    message: str         # human-readable description
    location: str | None # page name / question id, when applicable
```

### What `basic` checks

| Code | Severity | Meaning |
| :--- | :--- | :--- |
| `EMPTY_QUESTIONNAIRE` | warning | No pages and no blocks. |
| `EMPTY_PAGE` | warning (error in strict) | A page has no items. |
| `REDUNDANT_NAVIGATION` | warning | `default_next` duplicates the implicit next page. |
| `MISSING_NAVIGATION` | warning | A non-terminal page has no outgoing navigation edges. |

### Extra `strict` checks

`level="strict"` adds question-level and registry checks:

| Code | Severity | Meaning |
| :--- | :--- | :--- |
| `REQUIRED_CONDITIONAL` | warning | A required question also has conditional visibility. |
| `INCOMPATIBLE_QUESTION_SCALE` | error | `NumericInput` not on interval/ratio, or `LikertScale` not on ordinal. |
| `CATEGORICAL_WITHOUT_LABELS` | error | A `SingleChoice`/`MultiChoice` variable has no value labels. |
| `UNUSED_VARIABLE` | warning | A registered variable is never used in the questionnaire. |

```python
from siamang.core import Variable, SingleChoice, Page, Questionnaire

gender = Variable("gender", scale="nominal", label="Gender", labels={1: "Male", 2: "Female"})

survey = Questionnaire(
    title="Demo",
    pages=[
        Page(name="p1", items=[SingleChoice("Gender?", var=gender)]),
        Page(name="p2", items=[]),     # empty page!
    ],
)

for w in survey.lint():
    print(f"[{w.severity}] {w.code}: {w.message} ({w.location})")
# [warning] EMPTY_PAGE: Page 'p2' has no items. (p2)
```

---

## Relationship to the `siamang validate` CLI

`siamang validate my_survey.py` is a thin wrapper: it loads the survey object,
calls `validate(strict=...)`, then prints all `lint()` warnings. The exit code
encodes the outcome:

| Exit code | Condition |
| :--- | :--- |
| `0` | Valid; no warnings, or only `warning`-severity lint findings. |
| `1` | Valid structure, but at least one lint finding had `severity == "error"`. |
| `2` | `validate()` raised a `ValueError` (structural failure). |

```bash
siamang validate my_survey.py            # basic lint
siamang validate my_survey.py --strict   # strict validation + lint
```

See the [[CLI Reference|CLI-Reference]] for the full command surface.

---

## Validating *data*, not just the questionnaire

`Questionnaire.validate`/`lint` check the **design**. To check a collected or
simulated **dataset** against its variable metadata (dtypes, ranges, value
labels, weight constraints), use `SurveyData.validate()`, which returns a list
of `ValidationIssue` objects. That workflow is documented on
[[Working with Data|Working-with-Data]].

---

See also: [[Visibility and Branching|Visibility-and-Branching]] · [[Simulation]] · [[Working with Data|Working-with-Data]] · [[CLI Reference|CLI-Reference]]
