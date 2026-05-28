# Siamang Declarative Reporting API (Design Document)

This document describes the architecture and specifications of the declarative reporting and visualization system for **siamang**. This module allows quantitative social researchers and sociologists to generate publication-ready tables and figures with minimal configuration [1] [2]. 

Like **SPSS** or **Stata**, the system automatically leverages variable metadata (such as variable labels, value labels, and measurement scales) to choose appropriate statistics, perform significance tests, and format charts [1] [3].

---

## 1. Design Principles

- **Zero Boilerplate**: The user specifies *what* to analyze, not *how* to calculate or plot it [2].
- **Metadata-Driven**: Variable labels, value labels, and scales (`nominal`, `ordinal`, `interval`, `ratio`) are automatically resolved from the attached `VariableMap` [1].
- **Format Flexibility**: All table components support outputting as a raw `pandas.DataFrame`, a GitHub-flavored Markdown table, or a styled HTML table [2].
- **Intelligent Defaults**: Visualizations automatically adjust chart types (e.g., bar chart for nominal, boxplot for ratio grouped by nominal), axis labels, and color palettes based on measurement scales [3].

---

## 2. Table Component Specifications

All table components are subclasses of a base `SurveyTable` class. They are bound to a `SurveyData` container.

### Class Hierarchy

```
SurveyTable (Base)
├── FreqTable (Univariate Frequencies)
├── CrossTable (Bivariate Cross-tabulations)
└── GroupMeanTable (Grouped Means & Comparisons)
```

### 2.1. Base Class: `SurveyTable`

Every table component supports the following common interface:

| Method / Property | Return Type | Description |
|:---|:---|:---|
| `to_frame()` | `pd.DataFrame` | Returns the raw pandas DataFrame representation. |
| `to_markdown()` | `str` | Returns a clean, pipe-formatted GitHub-flavored Markdown table. |
| `to_html()` | `str` | Returns a clean HTML `<table>` string with basic class styling. |
| `export_xlsx(path)` | `Path` | Exports the table directly to an Excel sheet. |

---

### 2.2. Univariate Frequencies: `FreqTable`

Generates frequency distributions with absolute counts, percentages, and cumulative percentages.

**Usage**:
```python
from siamang.reporting import FreqTable

table = FreqTable(data, "remote_freq")
print(table.to_markdown())
```

**Parameters**:
- `data`: `SurveyData` container.
- `column`: `str` — Name of the variable to analyze.
- `exclude_missing`: `bool` (default: `True`) — If `True`, filters out missing values from the base.

**Output Structure**:
- Columns: `Value`, `Label`, `N`, `%`, `Cumulative %`.
- Row labels are automatically resolved from `Variable.labels`.

---

### 2.3. Bivariate Cross-tabulations: `CrossTable`

Generates two-way contingency tables with optional statistical tests (Chi-square, Cramer's V, Phi) and automatic percentages [1] [2].

**Usage**:
```python
from siamang.reporting import CrossTable

table = CrossTable(data, row="it_role", col="remote_freq", pct="row", test=True)
print(table.to_markdown())
```

**Parameters**:
- `data`: `SurveyData` container.
- `row`: `str` — Row variable name.
- `col`: `str` — Column variable name.
- `pct`: `str` (default: `"none"`) — Percentage direction: `"row"`, `"col"`, `"total"`, or `"none"`.
- `test`: `bool` (default: `True`) — If `True`, automatically runs `chi2_contingency` and appends a footer with $\chi^2$, $df$, $p$-value, and Cramér's V [1] [3].

---

### 2.4. Grouped Means: `GroupMeanTable`

Compares means of an interval/ratio variable across categories of a nominal/ordinal grouping variable [1].

**Usage**:
```python
from siamang.reporting import GroupMeanTable

table = GroupMeanTable(data, column="autonomy", by="remote_freq", test=True)
print(table.to_markdown())
```

**Parameters**:
- `data`: `SurveyData` container.
- `column`: `str` — Continuous dependent variable (interval/ratio).
- `by`: `str` — Categorical independent variable (nominal/ordinal).
- `test`: `bool` (default: `True`) — If `True`, automatically runs a significance test:
  - If `by` has 2 categories: **Independent t-test** (parametric) or **Mann-Whitney U** (non-parametric).
  - If `by` has 3+ categories: **One-way ANOVA** (parametric) or **Kruskal-Wallis H** (non-parametric) [1] [3].
  - *Siamang automatically chooses non-parametric tests if the dependent variable scale is `ordinal`.*

---

## 3. Visualization Component Specifications

All chart components are subclasses of a base `SurveyChart` class.

### Class Hierarchy

```
SurveyChart (Base)
├── BarChart (Categorical frequency / means)
├── BoxPlot (Distribution comparison)
├── HeatMap (Correlation / matrix visualization)
└── ScatterPlot (Bivariate continuous relationship)
```

### 3.1. Common Interface: `SurveyChart`

| Method | Return Type | Description |
|:---|:---|:---|
| `plot()` | `plt.Axes` | Builds and returns the matplotlib Axes object. |
| `show()` | `None` | Displays the plot inline (useful in Jupyter notebooks). |
| `save(path, dpi=150)` | `Path` | Saves the plot to a file. |

---

### 3.2. Categorical Distribution: `BarChart`

Plots frequencies or percentages of categorical variables, or mean values of continuous variables across groups.

**Usage**:
```python
from siamang.reporting import BarChart

# 1. Simple frequency bar chart
chart = BarChart(data, "it_role")
chart.show()

# 2. Grouped mean bar chart
chart = BarChart(data, "autonomy", by="remote_freq")
chart.save("autonomy_means.png")
```

**Auto-styling**:
- Automatically fetches variable label for the title.
- Resolves value labels for category tick labels on the X-axis.
- Uses a cohesive color palette based on `UIConfig` theme presets if available [3].

---

### 3.3. Distribution Comparison: `BoxPlot`

Compares the distribution of an interval/ratio variable across groups [1].

**Usage**:
```python
from siamang.reporting import BoxPlot

chart = BoxPlot(data, column="satisfaction", by="remote_freq")
chart.show()
```

**Auto-styling**:
- Automatically sets X-axis tick labels to value labels of the grouping variable.
- Sets Y-axis label to the dependent variable label.

---

### 3.4. Matrix / Correlation: `HeatMap`

Plots a correlation matrix of continuous variables or a mean matrix of a set of Likert items grouped by a category [1] [3].

**Usage**:
```python
from siamang.reporting import HeatMap

# Plot mean agreement for a set of matrix variables
chart = HeatMap(data, columns=["surv_keystroke", "surv_camera", "surv_git"], by="remote_freq")
chart.show()
```

---

## 4. Integration with `SurveyData`

To make this reporting API extremely convenient, we add reporting accessors directly to the `SurveyData` class [2]:

```python
# Accessors
data.report.freq("remote_freq")
data.report.crosstab("it_role", "remote_freq")
data.report.means("autonomy", by="remote_freq")

# Visualizations
data.plot.bar("it_role")
data.plot.boxplot("autonomy", by="remote_freq")
data.plot.heatmap(["surv_keystroke", "surv_camera"], by="remote_freq")
```

---

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2016.
