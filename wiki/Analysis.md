# Analysis

The `data.analysis` accessor (`DataAnalysis`) provides descriptive and
inferential statistics that are aware of survey weights and variable metadata.
The `data.processing` accessor offers quick value-level recoding. This page
covers the most common methods with runnable examples on simulated data.

```python
# All examples below assume `data` is a SurveyData (see Simulation):
from siamang.core import Variable, VariableMap, SingleChoice, NumericInput, LikertScale, Page, Questionnaire

age = Variable("age", scale="ratio", label="Age", valid_range=(18, 75))
it_role = Variable("it_role", scale="nominal", label="IT Role",
                   labels={1: "Engineer", 2: "Data Scientist", 3: "DevOps", 4: "PM"})
remote_freq = Variable("remote_freq", scale="ordinal", label="Remote Frequency",
                       labels={1: "Never", 2: "Occasionally", 3: "Hybrid", 4: "Mostly remote", 5: "Fully remote"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

variables = VariableMap()
variables.add_many([age, it_role, remote_freq, autonomy])

survey = Questionnaire(
    title="Work Study",
    pages=[Page(name="main", items=[
        NumericInput("Age?", var=age),
        SingleChoice("Role?", var=it_role),
        SingleChoice("Remote?", var=remote_freq),
        LikertScale("Autonomy?", var=autonomy, points=5),
    ])],
    variables=variables,
)
data = survey.simulate(n=200, seed=123)
```

---

## Descriptive statistics

### `mean`

```python
def mean(self, column: str, weighted: bool = False) -> float: ...
```

Arithmetic mean of a column (NaNs dropped). With `weighted=True`, uses the
default weight column set via `with_weight(...)`; raises `ValueError` if no
weight is configured.

```python
data.analysis.mean("autonomy")        # 3.06
```

### `median`

```python
def median(self, column: str) -> float: ...
```

Median of a column (NaNs dropped).

```python
data.analysis.median("age")
```

### `grouped_mean`

```python
def grouped_mean(self, column: str, by: str,
                 weighted: bool = False, labels: bool = False) -> pd.DataFrame: ...
```

Mean of `column` within each category of `by`. Returns a DataFrame with `group`,
`mean`, and `n`. With `labels=True`, adds a `label` column resolving each
group's value label. With `weighted=True`, `n` is the summed weight per group.

```python
print(data.analysis.grouped_mean("autonomy", by="remote_freq", labels=True))
#    group      mean     n          label
# 0      1  3.222222  45.0          Never
# 1      2  2.923077  39.0   Occasionally
# 2      3  2.897959  49.0         Hybrid
# 3      4  3.000000  31.0  Mostly remote
# 4      5  3.277778  36.0   Fully remote
```

For a formatted, significance-tested version of this comparison, prefer the
[[Reporting Tables|Reporting-Tables]] `data.report.means(...)` table.

---

## Inferential tests

These methods require **`scipy`**, which ships with the base install (they raise
`ImportError` if it is somehow missing). Each returns a plain `dict`.

### `kruskal`

```python
def kruskal(self, column: str, group: str) -> dict[str, float]: ...
```

Kruskal–Wallis H-test for 3+ independent groups (the non-parametric analogue of
one-way ANOVA). Returns `{"statistic", "p_value", "groups"}`, where `groups` is
the number of groups compared. Raises `ValueError` with fewer than two
non-empty groups.

```python
data.analysis.kruskal("autonomy", "remote_freq")
# {'statistic': 2.1330..., 'p_value': 0.7112..., 'groups': 5.0}
```

### `mannwhitney`

```python
def mannwhitney(self, column: str, group: str) -> dict[str, float | object]: ...
```

Mann–Whitney U-test for **exactly two** independent groups (two-sided). Returns
`{"statistic", "p_value", "group_a", "group_b"}`, where `group_a`/`group_b` are
the two group values compared. Raises `ValueError` unless exactly two non-empty
groups are present.

```python
two_levels = data.with_frame(data.frame[data.frame["remote_freq"].isin([1, 5])])
two_levels.analysis.mannwhitney("autonomy", "remote_freq")
# {'statistic': 794.0, 'p_value': 0.8796..., 'group_a': 1, 'group_b': 5}
```

> The [[Reporting Tables|Reporting-Tables]] `GroupMeanTable` picks between
> t-test, ANOVA, Mann–Whitney, and Kruskal–Wallis automatically based on scale
> and group count — use it when you want the test chosen for you.

---

## Weighted statistics

Set a default weight column once with `with_weight(...)`, then pass
`weighted=True` to any method that supports it (`mean`, `grouped_mean`,
`frequencies`, `crosstab`, `proportion_ci`).

```python
import numpy as np

# attach a synthetic design weight for illustration
weighted = data.with_frame(data.frame.assign(w=np.linspace(0.5, 1.5, len(data.frame)))) \
               .with_weight("w")

weighted.analysis.mean("autonomy", weighted=True)
weighted.analysis.effective_sample_size()   # Kish's ESS = (Σw)² / Σw²
```

`effective_sample_size()` reports Kish's effective sample size for the weighted
frame and raises `ValueError` if no weight is set. See
[[Working with Data|Working-with-Data]] for `with_weight`.

---

## Quick recoding: `data.processing.recode`

```python
def recode(self, column: str, mapping: dict[Any, Any]) -> SurveyData: ...
```

`DataProcessing.recode` applies a raw `{old: new}` mapping to a column **in
place** and returns a new `SurveyData`. It is a thin convenience wrapper and
**does not** carry over variable metadata.

```python
# Collapse the 5-point remote-frequency scale into 3 levels
collapsed = data.processing.recode("remote_freq", {1: 1, 2: 1, 3: 2, 4: 3, 5: 3})
```

> **Note:** For research-grade, metadata-aware recoding that registers a new
> variable with proper labels and scale, prefer `SurveyData.recode_values(...)`
> (collapse/remap discrete codes), `SurveyData.recode(...)` (bin a continuous
> variable into ordinal categories), or `SurveyData.derive(...)` (build a 0/1
> indicator from an [[Visibility and Branching|Visibility-and-Branching]]
> expression). These live on `SurveyData` itself, not on the `processing`
> accessor.

```python
# Metadata-aware: bin age into ordinal brackets, registered as a new variable
banded = data.recode("age", into="age_band", bins=[18, 30, 45, 75],
                      labels=["18-29", "30-44", "45+"], label="Age band")
banded.variables["age_band"].labels   # {1: '18-29', 2: '30-44', 3: '45+'}
```

---

See also: [[Working with Data|Working-with-Data]] · [[Reporting Tables|Reporting-Tables]] · [[Banner Tables|Banner-Tables]] · [[Simulation]] · [[Variables and Measurement|Variables-and-Measurement]]
