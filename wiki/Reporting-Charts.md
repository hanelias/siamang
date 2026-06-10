# Reporting Charts

siamang's declarative charts mirror the [[Reporting Tables|Reporting-Tables]]
API: each chart reads variable labels, value labels, and scales from the
attached metadata and produces a publication-ready figure with minimal
configuration. The four chart types are `BarChart`, `BoxPlot`, `HeatMap`, and
`ScatterPlot`, each also reachable through the fluent `data.plot` accessor.

```python
from siamang.reporting import BarChart, BoxPlot, HeatMap, ScatterPlot
```

> **Requires the `charts` extra.** Charts depend on matplotlib (and seaborn for
> `HeatMap`/`ScatterPlot`). Install with `pip install "siamang[charts]"`. If
> matplotlib is missing, building any chart raises a friendly
> `ImportError: matplotlib is required for chart generation. Install it with:
> pip install matplotlib`. See [[Installation]].

The examples below assume `data` is the simulated `SurveyData` from
[[Simulation]] / [[Analysis]].

---

## Common interface

All charts subclass `SurveyChart` and share these parameters and methods. The
figure is built lazily on first use.

**Shared parameters**

- **`figsize`** — `(width, height)` in inches, default `(10, 6)`.
- **`palette`** — seaborn palette name, default `"muted"` (e.g. `"deep"`,
  `"pastel"`, `"colorblind"`).
- **`title`** — override the auto-generated title (default `None` → derived from
  variable labels).

**Methods**

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `plot()` | `matplotlib.axes.Axes` | Build and return the Axes for further tweaking. |
| `show()` | `None` | Display inline (Jupyter) or in a window. |
| `save(path, dpi=150)` | `Path` | Write to file (the directory must already exist); `bbox_inches="tight"`. |

---

## `BarChart`

```python
BarChart(data, column="", by=None, horizontal=False, show_values=True,
         figsize=(10, 6), palette="muted", title=None)
```

With only `column`, plots a **frequency** distribution of a categorical
variable. With `by` set, plots the **mean** of `column` within each category of
`by`.

**Extra parameters**

- **`column`** — variable on the category axis (or whose mean is plotted).
- **`by`** — optional grouping variable; switches to grouped-mean mode.
- **`horizontal`** — draw horizontal bars (default `False`).
- **`show_values`** — annotate each bar with its value (default `True`).

```python
# Frequency of IT roles
data.plot.bar("it_role").show()

# Mean autonomy by remote frequency, saved to disk
data.plot.bar("autonomy", by="remote_freq", palette="pastel").save("autonomy_means.png")
```

---

## `BoxPlot`

```python
BoxPlot(data, column="", by="", show_points=False,
        figsize=(10, 6), palette="muted", title=None)
```

Compares the distribution of a continuous variable across categories.

**Extra parameters**

- **`column`** — continuous dependent variable (Y-axis).
- **`by`** — categorical grouping variable (X-axis).
- **`show_points`** — overlay a jittered strip plot of the raw points
  (default `False`).

```python
data.plot.boxplot("autonomy", by="remote_freq", show_points=True).show()
```

---

## `HeatMap`

```python
HeatMap(data, columns=[], by=None, annot=True, cmap="YlOrRd",
        vmin=None, vmax=None, figsize=(10, 6), title=None)
```

With `by` set, plots a matrix of **group means** (each of `columns` averaged
within categories of `by`). With `by=None`, plots a **Spearman correlation
matrix** of `columns` (using a diverging `RdBu_r` scale centered at 0).

**Extra parameters**

- **`columns`** — list of variables in the matrix.
- **`by`** — grouping variable for means; `None` for a correlation matrix.
- **`annot`** — write the numeric value in each cell (default `True`).
- **`cmap`** — colormap name (default `"YlOrRd"`; ignored for the correlation
  matrix).
- **`vmin`/`vmax`** — color-scale anchors.

> `HeatMap` requires **seaborn** specifically; it raises
> `ImportError: seaborn is required for HeatMap` if seaborn is unavailable.

```python
# Mean autonomy and age across remote-frequency groups
data.plot.heatmap(["autonomy", "age"], by="remote_freq", cmap="Blues").show()

# Spearman correlation matrix of continuous measures
data.plot.heatmap(["age", "autonomy"]).show()
```

---

## `ScatterPlot`

```python
ScatterPlot(data, x="", y="", hue=None, trendline=True,
            figsize=(10, 6), palette="muted", title=None)
```

Plots two continuous variables against each other, with an optional color
grouping and a linear regression trendline.

**Extra parameters**

- **`x`** — X-axis variable.
- **`y`** — Y-axis variable.
- **`hue`** — optional categorical variable to color points by.
- **`trendline`** — add a linear regression line (default `True`). The
  trendline is drawn only when `hue` is `None`.

```python
data.plot.scatter("age", "autonomy", hue="remote_freq").show()
```

---

## The `data.plot` accessor

The accessor returns the same chart objects, so you can chain `show()`/`save()`:

```python
def bar(column, *, by=None, horizontal=False, show_values=True,
        figsize=(10, 6), palette="muted", title=None) -> BarChart
def boxplot(column, *, by, show_points=False,
            figsize=(10, 6), palette="muted", title=None) -> BoxPlot
def heatmap(columns, *, by=None, annot=True, cmap="YlOrRd",
            vmin=None, vmax=None, figsize=(10, 6), title=None) -> HeatMap
def scatter(x, y, *, hue=None, trendline=True,
            figsize=(10, 6), palette="muted", title=None) -> ScatterPlot
```

```python
ax = data.plot.bar("it_role", horizontal=True).plot()   # get Axes to customize
ax.set_xlabel("Respondents")
```

To embed charts in a narrative document alongside tables and prose, add them to
a [[Report Document|Report-Document]] — it calls `save()` for you and links the
generated PNGs.

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Report Document|Report-Document]] · [[Analysis]] · [[Working with Data|Working-with-Data]] · [[Installation]]
