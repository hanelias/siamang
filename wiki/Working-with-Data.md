# Working with Data

`SurveyData` is the central data container in siamang: it binds a pandas
`DataFrame` to the variable metadata (`VariableMap`) that gives every column a
label, a measurement scale, value labels, and missing-value rules. Everything
downstream — [[Analysis]], [[Reporting Tables|Reporting-Tables]],
[[Reporting Charts|Reporting-Charts]], [[Banner Tables|Banner-Tables]] — reads
from this object.

```python
from siamang.data import SurveyData
```

---

## `SurveyData`

```python
@dataclass(frozen=True, slots=True)
class SurveyData:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    questionnaire: Questionnaire | None = None
    weight: str | None = None     # default weight column for weighted stats
```

`SurveyData` is **frozen and immutable**: every transformation returns a *new*
instance. You usually obtain one from [[Simulation|Simulation]]
(`survey.simulate(...)`), from deployment (`result.collect()`), or by
constructing it directly from a DataFrame plus a `VariableMap` (below).

### Constructing from a DataFrame + VariableMap

```python
import pandas as pd
from siamang.data import SurveyData
from siamang.core import Variable, VariableMap

variables = VariableMap()
variables.add(Variable("gender", scale="nominal", label="Gender", labels={1: "Male", 2: "Female"}))
variables.add(Variable("age", scale="ratio", label="Age", valid_range=(18, 99)))

frame = pd.DataFrame({"gender": [1, 2, 1, 2], "age": [34, 28, 45, 52]})

data = SurveyData(frame=frame, variables=variables)
print(data.analysis.mean("age"))      # 39.75
```

See [[Variables and Measurement|Variables-and-Measurement]] for how to define
variables, scales, and missing values, and [[Data Import and Export|Data-Import-and-Export]]
for loading frames from CSV/Excel/SPSS/Stata/R with labels preserved.

---

## Lazy accessors

Five properties expose specialized toolkits. Each is cheap to access (it just
wraps the current frame and metadata), so call them inline as needed.

| Accessor | Type | Purpose | Page |
| :--- | :--- | :--- | :--- |
| `data.processing` | `DataProcessing` | Ad-hoc value-level transforms. | [[Analysis]] |
| `data.analysis` | `DataAnalysis` | Descriptive & inferential statistics. | [[Analysis]] |
| `data.tables` | `SurveyTables` | Multi-cell banner/cross-break tables. | [[Banner Tables\|Banner-Tables]] |
| `data.report` | `ReportAccessor` | Declarative, labeled tables. | [[Reporting Tables\|Reporting-Tables]] |
| `data.plot` | `PlotAccessor` | Declarative, labeled charts. | [[Reporting Charts\|Reporting-Charts]] |

```python
data.analysis.mean("age")
data.report.freq("gender").to_markdown()
data.plot.bar("gender").show()
data.tables.banner(rows=["gender"], columns=["age"])
```

---

## Immutable updates

### `with_frame`

```python
def with_frame(self, frame: pd.DataFrame) -> SurveyData: ...
```

Returns a new `SurveyData` with the underlying DataFrame replaced (metadata,
questionnaire, and weight carried over). Use it after dropping rows, filtering,
or any custom pandas manipulation:

```python
adults = data.with_frame(data.frame[data.frame["age"] >= 40])
```

### `with_weight`

```python
def with_weight(self, column: str) -> SurveyData: ...
```

Sets the default survey weight column, used by every `weighted=True` statistic
in [[Analysis]]. Raises `ValueError` if the column is not in the frame.

```python
weighted = data.with_weight("design_weight")
weighted.analysis.mean("age", weighted=True)
```

---

## Inspection

### `codebook`

```python
def codebook(self) -> pd.DataFrame: ...
```

Returns a metadata-only DataFrame — one row per registered variable with `name`,
`label`, `scale`, `dtype`, `role`, `description`, `missing_values`,
`missing_kinds`, `missing`, and `valid_range`. Raises `ValueError` if no
`VariableMap` is attached.

### `describe_variables`

```python
def describe_variables(self) -> pd.DataFrame: ...
```

Returns a quick completeness summary — `name`, `label`, `scale`, plus `n`
(rows), `n_missing` (NaN count), and `n_unique` per variable. Also requires
metadata.

```python
print(data.describe_variables())
#      name   label    scale  n  n_missing  n_unique
# 0  gender  Gender  nominal  4          0         2
# 1     age     Age    ratio  4          0         4
```

---

## Validation

### `validate`

```python
def validate(self, raise_on_error: bool = False) -> list[ValidationIssue]: ...
```

Checks the **DataFrame against its metadata** and returns a list of
`ValidationIssue` objects (this is distinct from `Questionnaire.validate`, which
checks survey *design* — see [[Validation and Linting|Validation-and-Linting]]).
It verifies:

- column presence vs. the `VariableMap`;
- dtype compatibility, `valid_range` bounds, and value-label coverage for
  categorical variables;
- the weight column exists and is numeric (when `weight` is set);
- every questionnaire variable is present in the frame (when a questionnaire is
  attached).

`ValidationIssue` carries `code`, `severity` (`"error"`/`"warning"`), `message`,
and optional `variable`/`column`. With `raise_on_error=True`, the method raises
`ValueError` if any **error**-severity issue is present.

```python
import pandas as pd
from siamang.data import SurveyData
from siamang.core import Variable, VariableMap

variables = VariableMap()
variables.add(Variable("gender", scale="nominal", label="Gender", labels={1: "Male", 2: "Female"}))
variables.add(Variable("age", scale="ratio", label="Age", valid_range=(18, 99)))

bad = SurveyData(frame=pd.DataFrame({"gender": [1, 5], "age": [34, 200]}), variables=variables)
for issue in bad.validate():
    print(issue.code, "-", issue.message)
# INVALID_LABEL_VALUE - Variable 'gender' has values not present in labels: 5.
# OUT_OF_RANGE - Variable 'age' has values outside valid_range (18, 99).
```

If no `VariableMap` is attached, `validate` returns a single `MISSING_METADATA`
warning rather than erroring.

---

## Beyond the basics

`SurveyData` also offers missing-value handling (`apply_missing_values`,
`drop_missing`), metadata-aware recoding and derivation (`recode`,
`recode_values`, `derive`), composite measures (`scale_alpha`, `create_index`),
and multi-format export (`export`, `export_dictionary`). Recoding is covered on
[[Analysis]]; import/export on [[Data Import and Export|Data-Import-and-Export]].

---

See also: [[Simulation]] · [[Analysis]] · [[Reporting Tables|Reporting-Tables]] · [[Banner Tables|Banner-Tables]] · [[Variables and Measurement|Variables-and-Measurement]] · [[Data Import and Export|Data-Import-and-Export]]
