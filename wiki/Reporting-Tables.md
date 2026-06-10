# Reporting Tables

siamang's declarative tables turn a [[Working with Data|Working-with-Data]]
`SurveyData` into publication-ready output. Each table reads variable labels,
value labels, and measurement scales from the attached metadata, computes the
right statistics, and exports to a DataFrame, Markdown, HTML, or Excel. The three
table types are `FreqTable`, `CrossTable`, and `GroupMeanTable`, each also
reachable through the fluent `data.report` accessor.

```python
from siamang.reporting import FreqTable, CrossTable, GroupMeanTable
```

The examples below assume `data` is the simulated `SurveyData` built in
[[Simulation]] / [[Analysis]] (variables `it_role`, `remote_freq`, `autonomy`).

---

## Common interface

All tables subclass `SurveyTable` and share these methods (the table is built
lazily on first use):

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `to_frame()` | `pd.DataFrame` | Raw result table. |
| `to_markdown()` | `str` | GitHub-flavored pipe table; appends a stats footer. |
| `to_html()` | `str` | `<table class="siamang-table">`; renders inline in Jupyter. |
| `export_xlsx(path)` | `Path` | Writes an `.xlsx` sheet named `"Table"`. |

The statistics footer (Chi-square, Cramér's V, the chosen mean-comparison test,
etc.) is rendered automatically beneath `to_markdown()`/`to_html()` output.

---

## `FreqTable` — univariate frequencies

```python
FreqTable(data, column="", exclude_missing=True, sort="value")
```

A frequency distribution with absolute counts, percentages, and cumulative
percentages, plus a `Total` row. Value labels are resolved automatically.

**Parameters**

- **`column`** — variable to tabulate.
- **`exclude_missing`** — drop `NaN` from the base (default `True`).
- **`sort`** — `"value"` (by code, default), `"freq"` (count descending), or
  `"label"` (alphabetical by label).

```python
print(data.report.freq("it_role").to_markdown())
```

```text
| Value | Label | N | % | Cumulative % |
|---|---|---|---|---|
| 1 | Engineer | 58 | 29.0 | 29.0 |
| 2 | Data Scientist | 47 | 23.5 | 52.5 |
| 3 | DevOps | 43 | 21.5 | 74.0 |
| 4 | PM | 52 | 26.0 | 100.0 |
|  | Total | 200 | 100.0 | 100.0 |

Variable = IT Role; N valid = 200
```

---

## `CrossTable` — bivariate cross-tabulation

```python
CrossTable(data, row="", col="", pct="none", test=True)
```

A two-way contingency table with row/column totals and, by default, a
Chi-square test of independence reported in the footer alongside its degrees of
freedom, p-value, Cramér's V, and N.

**Parameters**

- **`row`** — row variable (usually the independent variable).
- **`col`** — column variable (usually the dependent variable).
- **`pct`** — percentage direction: `"none"` (counts), `"row"`, `"col"`, or
  `"total"`. The `Total` row/column always shows raw counts.
- **`test`** — run the Chi-square test and append the footer (default `True`).
  Requires `scipy`; without it the footer reports that scipy is missing.

```python
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())
```

```text
| IT Role | Never | Occasionally | Hybrid | Mostly remote | Fully remote | Total |
|---|---|---|---|---|---|---|
| Engineer | 17.2 | 19.0 | 27.6 | 20.7 | 15.5 | 58 |
| Data Scientist | 19.1 | 10.6 | 17.0 | 21.3 | 31.9 | 47 |
| DevOps | 27.9 | 32.6 | 20.9 | 7.0 | 11.6 | 43 |
| PM | 26.9 | 17.3 | 30.8 | 11.5 | 13.5 | 52 |
| Total | 45.0 | 39.0 | 49.0 | 31.0 | 36.0 | 200 |

χ² = 21.4850; df = 12; p = 0.0437; Cramér's V = 0.1890; N = 200
```

---

## `GroupMeanTable` — grouped means with automatic test

```python
GroupMeanTable(data, column="", by="", test=True)
```

Compares the mean of a continuous variable across categories of a grouping
variable, reporting per-group `Mean`, `SD`, `Median`, and `N`. With `test=True`
it **selects the significance test automatically** based on the dependent
variable's scale and the number of groups:

| Dependent scale | 2 groups | 3+ groups |
| :--- | :--- | :--- |
| `ordinal` (or scale unknown) | Mann–Whitney U | Kruskal–Wallis H |
| `interval` / `ratio` | Independent t-test | One-way ANOVA |

**Parameters**

- **`column`** — continuous dependent variable.
- **`by`** — categorical grouping variable.
- **`test`** — run and report the chosen test (default `True`; requires `scipy`).

```python
print(data.report.means("autonomy", by="remote_freq").to_markdown())
```

```text
| Remote Frequency | Mean | SD | Median | N |
|---|---|---|---|---|
| Never | 3.222 | 1.38 | 4.0 | 45 |
| Occasionally | 2.923 | 1.458 | 3.0 | 39 |
| Hybrid | 2.898 | 1.447 | 3.0 | 49 |
| Mostly remote | 3.0 | 1.653 | 2.0 | 31 |
| Fully remote | 3.278 | 1.386 | 4.0 | 36 |

Kruskal-Wallis H = 2.1330; p = 0.7113; N = 200; Variable = Autonomy
```

Here `autonomy` is ordinal and `remote_freq` has five categories, so
Kruskal–Wallis H is chosen automatically.

---

## The `data.report` accessor

Instead of importing the classes, use the fluent accessor — it returns the same
table objects, so you can chain an exporter directly:

```python
def freq(column, *, exclude_missing=True, sort="value") -> FreqTable
def crosstab(row, col, *, pct="none", test=True) -> CrossTable
def means(column, *, by, test=True) -> GroupMeanTable
```

```python
data.report.freq("it_role", sort="freq").to_frame()
data.report.crosstab("it_role", "remote_freq", pct="col").to_html()
data.report.means("autonomy", by="remote_freq").export_xlsx("autonomy_means.xlsx")
```

---

## Exporting

Every table supports the four exporters from the common interface:

```python
table = data.report.crosstab("it_role", "remote_freq", pct="row")

frame = table.to_frame()            # pandas DataFrame
md    = table.to_markdown()         # str (with stats footer)
html  = table.to_html()            # str
path  = table.export_xlsx("crosstab.xlsx")   # Path (the directory must already exist)
```

To assemble several tables and charts into one narrative document, drop them
into a [[Report Document|Report-Document]]. For multi-variable cross-break
tables, see [[Banner Tables|Banner-Tables]].

---

See also: [[Reporting Charts|Reporting-Charts]] · [[Report Document|Report-Document]] · [[Banner Tables|Banner-Tables]] · [[Analysis]] · [[Working with Data|Working-with-Data]]
