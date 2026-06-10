# Variables and Measurement

A `Variable` is the atomic measurement unit in siamang: it binds a data column to a
measurement scale, a data type, an analytical role, and codebook metadata (labels,
missing-value conventions, descriptions). Variables are used to validate collected
responses, generate dataset schemas, and drive labelled, SPSS-like analysis.

All classes on this page are frozen dataclasses (immutable after construction).

```python
from siamang.core import Variable, VariableMap, MissingValue, ValidationIssue
```

## `Variable`

```python
@dataclass(frozen=True, slots=True)
class Variable:
    name: str
    scale: str
    label: str | None = None
    labels: dict[Any, str] = {}
    missing_values: tuple[Any, ...] = ()
    dtype: str | None = None
    role: str | None = None
    description: str | None = None
    construct: str | None = None
    source: str | None = None
    valid_range: tuple[Any, Any] | None = None
    missing_labels: dict[Any, str] = {}
    missing: tuple[MissingValue, ...] = ()
```

Construction validates and normalizes the inputs: `name` must be non-empty; `scale`,
`dtype`, and `role` are lowercased and checked against their allowed sets;
`valid_range` must be an ordered 2-tuple `(min, max)`; and the legacy
`missing_values`/`missing_labels` fields are merged into the structured `missing`
tuple. An invalid value raises `ValueError` (or `TypeError` for malformed `missing`
entries).

### Fields

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | *required* | Unique identifier and output column name. Must be non-empty. |
| `scale` | `str` | *required* | Level of measurement: `"nominal"`, `"ordinal"`, `"interval"`, `"ratio"`. Case-insensitive. |
| `label` | `str \| None` | `None` | Human-readable variable label (used as the SPSS/Stata variable label). |
| `labels` | `dict[Any, str]` | `{}` | `{code: label}` value labels for nominal/ordinal variables. |
| `missing_values` | `tuple[Any, ...]` | `()` | Legacy plain codes treated as missing. Normalized into `missing`. |
| `dtype` | `str \| None` | `None` | Physical type: `"int"`, `"float"`, `"str"`, `"bool"`, `"category"`, `"datetime"`. Inferred during validation if omitted. |
| `role` | `str \| None` | `None` | Analytical role: `"input"`, `"target"`, `"weight"`, `"id"`, `"grouping"`, `"derived"`. |
| `description` | `str \| None` | `None` | Long-form description of what the variable measures. |
| `construct` | `str \| None` | `None` | Latent construct being measured (e.g. `"trust_in_institutions"`). |
| `source` | `str \| None` | `None` | Provenance of the question wording (e.g. `"ESS Wave 10"`). |
| `valid_range` | `tuple[Any, Any] \| None` | `None` | Inclusive `(min, max)`. Must be ordered. |
| `missing_labels` | `dict[Any, str]` | `{}` | `{code: label}` for missing codes. Every key must appear in `missing_values` or `missing`. |
| `missing` | `tuple[MissingValue, ...]` | `()` | Structured missing-value definitions (code + label + kind). |

> **Note on `missing` normalization.** After construction, `missing` always holds the
> canonical `MissingValue` tuple, `missing_values` mirrors their codes, and
> `missing_labels` is back-filled from any structured entries. You can populate
> missing values either way — legacy (`missing_values` + `missing_labels`) or
> structured (`missing=`) — and they are merged.

### Methods

- **`is_missing(value) -> bool`** — `True` when `value` matches a configured missing code.
- **`structured_missing_values() -> tuple[MissingValue, ...]`** — the canonical `MissingValue` tuple.
- **`missing_kinds_dict() -> dict[Any, str]`** — `{code: kind}` for the missing values.

### Comparison helpers

`Variable` exposes methods that return `Expression` trees for use in `show_if`,
`hide_if`, `skip_to`, and `next_if`:

| Method | Operator | Example |
| :--- | :--- | :--- |
| `var.eq(value)` | `=` | `gender.eq(1)` |
| `var.ne(value)` | `!=` | `gender.ne(1)` |
| `var.gt(value)` | `>` | `age.gt(18)` |
| `var.ge(value)` | `>=` | `age.ge(18)` |
| `var.lt(value)` | `<` | `age.lt(65)` |
| `var.le(value)` | `<=` | `age.le(65)` |
| `var.isin(values)` | `in` | `region.isin([1, 2, 3])` |
| `var.notin(values)` | `not in` | `region.notin([99])` |

The operators `>`, `>=`, `<`, `<=` are also overloaded, so `age >= 18` works
directly. Equality cannot be overloaded (Python reserves `==` for dataclass
identity), so use `var.eq(value)`. See [[Visibility and Branching|Visibility-and-Branching]].

### Measurement scales

| Scale | Meaning | Typical questions |
| :--- | :--- | :--- |
| `nominal` | Unordered categories | `SingleChoice`, `MultiChoice` |
| `ordinal` | Ordered categories | `LikertScale`, `Ranking`, ordinal `SingleChoice` |
| `interval` | Numeric, no true zero | `NumericInput` |
| `ratio` | Numeric with a true zero | `NumericInput` |

Scale choice matters: strict linting flags a `LikertScale` whose variable is not
`ordinal`, or a `NumericInput` whose variable is not `interval`/`ratio`, and warns
about categorical (`nominal`/`ordinal`) variables that have no `labels`.

### Examples

```python
import siamang as sg

age = sg.Variable("age", scale="ratio", label="Age", valid_range=(18, 99), dtype="int")

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
    labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full trust"},
    construct="institutional_trust", source="ESS Wave 10",
)
```

## `MissingValue`

```python
@dataclass(frozen=True, slots=True)
class MissingValue:
    code: Any
    label: str
    kind: str = "system_missing"
```

A structured representation of a non-substantive response. Distinguishing *why* a
value is missing is essential for high-quality analysis. `label` must be non-empty
and `kind` is normalized and validated.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `Any` | *required* | The stored code (e.g. `99`, `-1`). |
| `label` | `str` | *required* | Human-readable description (e.g. `"Don't know"`). Non-empty. |
| `kind` | `str` | `"system_missing"` | One of `"refusal"`, `"dont_know"`, `"not_applicable"`, `"not_asked"`, `"system_missing"`. |

Methods: `to_dict()` and the classmethod `from_dict(payload)` for serialization.

```python
from siamang.core import Variable, MissingValue

employment = Variable(
    "employment", scale="nominal", label="Employment status",
    labels={1: "Employed", 2: "Unemployed", 3: "Retired"},
    missing=(
        MissingValue(code=98, label="Don't know", kind="dont_know"),
        MissingValue(code=99, label="Refused", kind="refusal"),
    ),
)

employment.is_missing(99)          # True
employment.missing_kinds_dict()    # {98: 'dont_know', 99: 'refusal'}
```

## `VariableMap`

```python
class VariableMap(dict[str, Variable]):
    ...
```

A `dict`-like registry of variables indexed by `name`. It is the centralized schema
for a survey and the bridge to collected data. Construct an empty map and add
variables, or build one from a serialized payload with `VariableMap.from_dict`.

### Adding and looking up

- **`add(variable)`** — register one variable; raises `KeyError` if the name already exists.
- **`add_many(variables)`** — register a list of variables in order.
- **`require(name) -> Variable`** — look up by name; raises `KeyError` if absent.
- **`by_scale(scale) -> list[Variable]`** — all variables with a given scale.
- **`by_role(role) -> list[Variable]`** — all variables with a given role.

```python
from siamang.core import VariableMap

vm = VariableMap()
vm.add_many([age, gender, income, trust])

vm.require("trust")            # -> Variable('trust', ...)
vm.by_scale("ordinal")         # [Variable('trust', ...)]
vm.by_role("weight")           # []
```

### Codebook accessors

These flatten the registry into the dictionaries used by readers, writers, and
reporting:

| Method | Returns |
| :--- | :--- |
| `labels_dict()` | `{name: label}` (falls back to `name` when no label) |
| `value_labels_dict()` | `{name: {code: label}}` |
| `missing_dict()` | `{name: [missing codes]}` |
| `missing_labels_dict()` | `{name: {code: label}}` |
| `missing_kinds_dict()` | `{name: {code: kind}}` |
| `to_dict()` | full nested serialization of every variable |

### Validating a DataFrame

**`validate_frame(frame, raise_on_error=False) -> list[ValidationIssue]`** checks a
pandas `DataFrame` against the registered schema and returns a list of
`ValidationIssue`. With `raise_on_error=True` it raises `ValueError` if any issue has
`severity == "error"`. Checks include:

- `MISSING_COLUMN` — a declared variable is absent from the frame (error).
- `EXTRA_COLUMN` — a frame column is not declared in the map (warning).
- `INVALID_DTYPE` — values are incompatible with the declared `dtype` (error).
- `OUT_OF_RANGE` — numeric values fall outside `valid_range` (error).
- `INVALID_LABEL_VALUE` — a nominal/ordinal value is not present in `labels` (error).
- `MISSING_VALUE_WITHOUT_LABEL` — a missing code has no label (warning).
- `INVALID_WEIGHT` / `DUPLICATE_ID` — role constraints for `weight`/`id` (error).

```python
issues = vm.validate_frame(data.frame)
errors = [i for i in issues if i.severity == "error"]
for issue in errors:
    print(issue.code, issue.message)
```

## `ValidationIssue`

```python
@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    variable: str | None = None
    column: str | None = None
```

A single finding from `validate_frame`. `severity` is `"error"` or `"warning"`;
`code` is a machine-readable identifier (e.g. `"OUT_OF_RANGE"`); `variable` and
`column` point to the offending variable/column when applicable.

## Codebook usage

A `VariableMap` *is* your codebook: scales, labels, missing-value conventions, and
provenance (`description`, `construct`, `source`) travel with the survey. When you
`simulate()` or `deploy()`, siamang derives the dataset schema from the map (building
one automatically if you do not pass `variables=`). The same metadata renders labels
in [[Reporting Tables|Reporting-Tables]] and is preserved on export to SPSS/Stata —
see [[Data Import and Export|Data-Import-and-Export]].

## See also

- [[Question Types|Question-Types]] — how questions bind to variables.
- [[Core Concepts|Core-Concepts]] — the data model and the variables-vs-answers distinction.
- [[Visibility and Branching|Visibility-and-Branching]] — building expressions from variables.
- [[Validation and Linting|Validation-and-Linting]] — questionnaire-level checks.
