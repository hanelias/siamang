# Quotas

A `Quota` caps the number of accepted responses that match a specific category,
keeping a sample within target proportions (e.g. no more than 200 male and 200 female
respondents). Quotas are enforced server-side at submission time and surfaced to the
respondent through the frontend's "quota full" screen.

```python
from siamang.core import Quota
# or: import siamang as sg  →  sg.Quota
```

## `Quota`

```python
@dataclass(frozen=True, slots=True)
class Quota:
    variable: str
    target_value: Any
    limit: int
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `variable` | `str` | Name of the variable to monitor (must match a `Variable.name`). |
| `target_value` | `Any` | The category code to count (e.g. `1` for "Male"). |
| `limit` | `int` | Maximum accepted responses matching `variable == target_value`. |

Each `Quota` describes **one cell** — a single variable/value pair. Build several
quotas to constrain multiple cells or several variables.

### `reached`

```python
def reached(self, answers: list[dict[str, Any]]) -> bool
```

Counts how many rows in `answers` have `row[variable] == target_value` and returns
`True` once that count reaches `limit`. This is the same predicate the backend uses to
decide whether a cell is full.

```python
from siamang.core import Quota

male_cap = Quota("gender", target_value=1, limit=200)

responses = [{"gender": 1}, {"gender": 2}, {"gender": 1}]
male_cap.reached(responses)          # False (2 < 200)
male_cap.reached([{"gender": 1}] * 200)   # True
```

## How enforcement works

Quotas are attached at **deploy time** via the `quota=` option, not stored on the
`Questionnaire`. siamang serializes each quota and hands it to:

- the **backend**, which creates quota counters and enforces the limits server-side on
  every submission; and
- the **frontend client**, which displays a "quota full" message when the backend
  rejects a submission.

When a respondent's submission would exceed a filled cell, the backend reports the
cell as full (e.g. returns a `quota_full` status / `403`), and the frontend shows the
closed screen instead of accepting the response.

```python
from siamang.core import Quota

quotas = [
    Quota("gender", target_value=1, limit=200),
    Quota("gender", target_value=2, limit=200),
    Quota("region", target_value=1, limit=400),   # cap on the capital region
]

survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

## Examples

### Equal cells

Cap two genders at the same limit:

```python
import siamang as sg

quotas = [
    sg.Quota("gender", 1, limit=200),
    sg.Quota("gender", 2, limit=200),
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

### Constraining several variables

Quotas on different variables are independent — a submission must clear every cell it
falls into:

```python
quotas = [
    sg.Quota("gender", 1, limit=200),
    sg.Quota("gender", 2, limit=200),
    sg.Quota("region", 1, limit=400),
    sg.Quota("region", 2, limit=400),
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

### Tightening a cell between deploys

Quotas live in the deploy call, so adjusting a `limit` is just a code change followed
by another deploy. Note that each deploy provisions a **new survey instance** with
fresh quota counters — counts do not carry over from the previous deployment:

```python
quotas = [
    sg.Quota("gender", 1, limit=150),   # lowered from 200
    sg.Quota("gender", 2, limit=250),   # raised from 200
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

> **Backend support.** All bundled backends enforce quotas server-side — including
> the `local` SQLite backend, which keeps atomic quota counters. The difference is
> reachability: `local` is not publicly accessible, so use it for development and
> preview; consult [[Deployment]] for production backends.

## See also

- [[Deployment]] — the `deploy()` call where `quota=` is passed.
- [[Question Types|Question-Types]] — the variables a quota monitors.
- [[Variables and Measurement|Variables-and-Measurement]] — variable names and category codes.
- [[Scripts]] — additional respondent-side behaviour via JavaScript.
