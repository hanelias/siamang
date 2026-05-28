"""Declarative chart components for survey reporting.

Each chart class auto-resolves variable labels and value labels from the
attached SurveyData metadata, producing publication-ready figures with
minimal configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.rcParams["figure.dpi"] = 100
except ImportError:
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_label(data: SurveyData, var_name: str) -> str:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].label or var_name
    return var_name


def _get_value_labels(data: SurveyData, var_name: str) -> dict[Any, str]:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].labels or {}
    return {}


def _get_scale(data: SurveyData, var_name: str) -> str | None:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].scale
    return None


def _require_matplotlib():
    if plt is None:
        raise ImportError(
            "matplotlib is required for chart generation. Install it with: pip install matplotlib"
        )


# ─── Base Class ───────────────────────────────────────────────────────────────


@dataclass
class SurveyChart:
    """Base class for all declarative chart components.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    figsize : tuple[float, float]
        Figure size in inches (width, height).
    palette : str
        Seaborn/matplotlib color palette name.
    title : str | None
        Override the auto-generated title.
    """

    data: SurveyData
    figsize: tuple[float, float] = (10, 6)
    palette: str = "muted"
    title: str | None = None

    _fig: Any = field(init=False, repr=False, default=None)
    _ax: Any = field(init=False, repr=False, default=None)

    def _build(self) -> None:
        """Build the chart. Subclasses must implement this."""
        raise NotImplementedError

    def _ensure_built(self) -> None:
        if self._fig is None:
            _require_matplotlib()
            self._build()

    def plot(self):
        """Build and return the matplotlib Axes object."""
        self._ensure_built()
        return self._ax

    def show(self) -> None:
        """Display the chart (works in Jupyter and scripts)."""
        self._ensure_built()
        plt.show()

    def save(self, path: str | Path, dpi: int = 150) -> Path:
        """Save the chart to a file."""
        self._ensure_built()
        path = Path(path)
        self._fig.savefig(path, dpi=dpi, bbox_inches="tight")
        return path

    def _auto_title(self, *parts: str) -> str:
        """Generate a title from variable labels."""
        if self.title:
            return self.title
        return " by ".join(parts)


# ─── BarChart ─────────────────────────────────────────────────────────────────


@dataclass
class BarChart(SurveyChart):
    """Categorical bar chart.

    If only `column` is specified, plots frequency distribution.
    If `by` is also specified, plots mean values of `column` grouped by `by`.

    Parameters
    ----------
    column : str
        Variable to plot (frequencies if categorical, means if continuous with `by`).
    by : str | None
        Optional grouping variable. If provided, plots grouped means.
    horizontal : bool
        If True, plots horizontal bars.
    show_values : bool
        If True, annotates bars with values.
    """

    column: str = ""
    by: str | None = None
    horizontal: bool = False
    show_values: bool = True

    def _build(self) -> None:
        if sns:
            sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        col_label = _get_label(self.data, self.column)
        value_labels = _get_value_labels(self.data, self.column)

        if self.by is None:
            # Frequency bar chart
            series = self.data.frame[self.column].dropna()
            counts = series.value_counts().sort_index()

            if value_labels:
                labels = [value_labels.get(v, str(v)) for v in counts.index]
            else:
                labels = [str(v) for v in counts.index]

            if self.horizontal:
                ax.barh(
                    labels, counts.values, color=sns.color_palette(self.palette) if sns else None
                )
                ax.set_xlabel("Count")
                ax.set_ylabel(col_label)
            else:
                ax.bar(
                    labels, counts.values, color=sns.color_palette(self.palette) if sns else None
                )
                ax.set_ylabel("Count")
                ax.set_xlabel(col_label)
                plt.xticks(rotation=30, ha="right")

            if self.show_values:
                for i, v in enumerate(counts.values):
                    if self.horizontal:
                        ax.text(v + 0.5, i, str(v), va="center")
                    else:
                        ax.text(i, v + 0.5, str(v), ha="center")

            ax.set_title(self._auto_title(col_label))

        else:
            # Grouped mean bar chart
            by_label = _get_label(self.data, self.by)
            by_value_labels = _get_value_labels(self.data, self.by)

            frame = self.data.frame[[self.column, self.by]].dropna()
            grouped = frame.groupby(self.by)[self.column].mean()

            if by_value_labels:
                labels = [by_value_labels.get(v, str(v)) for v in grouped.index]
            else:
                labels = [str(v) for v in grouped.index]

            if self.horizontal:
                ax.barh(labels, grouped.values)
                ax.set_xlabel(f"Mean {col_label}")
                ax.set_ylabel(by_label)
            else:
                ax.bar(labels, grouped.values)
                ax.set_ylabel(f"Mean {col_label}")
                ax.set_xlabel(by_label)
                plt.xticks(rotation=30, ha="right")

            if self.show_values:
                for i, v in enumerate(grouped.values):
                    text = f"{v:.2f}"
                    if self.horizontal:
                        ax.text(v + 0.02, i, text, va="center")
                    else:
                        ax.text(i, v + 0.02, text, ha="center")

            ax.set_title(self._auto_title(f"Mean {col_label}", by_label))

        plt.tight_layout()


# ─── BoxPlot ──────────────────────────────────────────────────────────────────


@dataclass
class BoxPlot(SurveyChart):
    """Distribution comparison box plot.

    Compares the distribution of a continuous variable across categories.

    Parameters
    ----------
    column : str
        Continuous dependent variable (interval/ratio/ordinal).
    by : str
        Categorical grouping variable.
    show_points : bool
        If True, overlays individual data points (strip plot).
    """

    column: str = ""
    by: str = ""
    show_points: bool = False

    def _build(self) -> None:
        if sns:
            sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        col_label = _get_label(self.data, self.column)
        by_label = _get_label(self.data, self.by)
        by_value_labels = _get_value_labels(self.data, self.by)

        frame = self.data.frame[[self.column, self.by]].dropna().copy()

        if by_value_labels:
            frame["_group"] = frame[self.by].map(lambda v: by_value_labels.get(v, str(v)))
            order = [by_value_labels.get(v, str(v)) for v in sorted(by_value_labels.keys())]
        else:
            frame["_group"] = frame[self.by].astype(str)
            order = None

        if sns:
            sns.boxplot(
                data=frame,
                x="_group",
                y=self.column,
                hue="_group",
                ax=ax,
                palette=self.palette,
                order=order,
                legend=False,
            )
            if self.show_points:
                sns.stripplot(
                    data=frame,
                    x="_group",
                    y=self.column,
                    ax=ax,
                    color="0.3",
                    alpha=0.4,
                    size=3,
                    order=order,
                )
        else:
            groups = [g[self.column].values for _, g in frame.groupby("_group")]
            ax.boxplot(groups)

        ax.set_xlabel(by_label)
        ax.set_ylabel(col_label)
        ax.set_title(self._auto_title(col_label, by_label))
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()


# ─── HeatMap ──────────────────────────────────────────────────────────────────


@dataclass
class HeatMap(SurveyChart):
    """Matrix heatmap visualization.

    Plots mean values of multiple variables grouped by a category,
    or a correlation matrix if no `by` is specified.

    Parameters
    ----------
    columns : list[str]
        List of variables to include in the matrix.
    by : str | None
        If specified, plots mean of each column grouped by this variable.
        If None, plots a correlation matrix between the columns.
    annot : bool
        If True, annotates cells with numeric values.
    cmap : str
        Colormap name.
    vmin : float | None
        Minimum value for color scale.
    vmax : float | None
        Maximum value for color scale.
    """

    columns: list[str] = field(default_factory=list)
    by: str | None = None
    annot: bool = True
    cmap: str = "YlOrRd"
    vmin: float | None = None
    vmax: float | None = None

    def _build(self) -> None:
        if sns is None:
            raise ImportError("seaborn is required for HeatMap. Install with: pip install seaborn")

        sns.set_theme(style="whitegrid")

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        # Resolve column labels
        col_labels = [_get_label(self.data, c) for c in self.columns]

        if self.by is not None:
            # Grouped means heatmap
            by_value_labels = _get_value_labels(self.data, self.by)
            by_label = _get_label(self.data, self.by)

            frame = self.data.frame[self.columns + [self.by]].dropna()
            grouped = frame.groupby(self.by)[self.columns].mean()

            if by_value_labels:
                grouped.index = [by_value_labels.get(v, str(v)) for v in grouped.index]

            grouped.columns = col_labels
            matrix = grouped.T

            sns.heatmap(
                matrix,
                annot=self.annot,
                fmt=".2f",
                cmap=self.cmap,
                vmin=self.vmin,
                vmax=self.vmax,
                ax=ax,
                linewidths=0.5,
            )
            ax.set_title(self._auto_title("Mean Values", by_label))
            ax.set_xlabel(by_label)

        else:
            # Correlation matrix
            frame = self.data.frame[self.columns].dropna()
            corr = frame.corr(method="spearman")
            corr.index = col_labels
            corr.columns = col_labels

            sns.heatmap(
                corr,
                annot=self.annot,
                fmt=".2f",
                cmap="RdBu_r",
                vmin=-1,
                vmax=1,
                ax=ax,
                linewidths=0.5,
                center=0,
            )
            ax.set_title(self._auto_title("Spearman Correlation Matrix"))

        plt.tight_layout()


# ─── ScatterPlot ──────────────────────────────────────────────────────────────


@dataclass
class ScatterPlot(SurveyChart):
    """Bivariate scatter plot for continuous variables.

    Parameters
    ----------
    x : str
        X-axis variable name.
    y : str
        Y-axis variable name.
    hue : str | None
        Optional grouping variable for color coding.
    trendline : bool
        If True, adds a linear regression trendline.
    """

    x: str = ""
    y: str = ""
    hue: str | None = None
    trendline: bool = True

    def _build(self) -> None:
        if sns is None:
            raise ImportError("seaborn is required for ScatterPlot.")

        sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        x_label = _get_label(self.data, self.x)
        y_label = _get_label(self.data, self.y)

        cols = [self.x, self.y]
        if self.hue:
            cols.append(self.hue)

        frame = self.data.frame[cols].dropna().copy()

        # Apply hue labels
        hue_col = None
        if self.hue:
            hue_labels = _get_value_labels(self.data, self.hue)
            if hue_labels:
                frame["_hue"] = frame[self.hue].map(lambda v: hue_labels.get(v, str(v)))
                hue_col = "_hue"
            else:
                hue_col = self.hue

        scatter_kwargs = dict(data=frame, x=self.x, y=self.y, ax=ax, alpha=0.7)
        if hue_col:
            scatter_kwargs["hue"] = hue_col
            scatter_kwargs["palette"] = self.palette
        sns.scatterplot(**scatter_kwargs)

        if self.trendline and self.hue is None:
            sns.regplot(
                data=frame,
                x=self.x,
                y=self.y,
                ax=ax,
                scatter=False,
                color="red",
                line_kws={"linewidth": 1.5},
            )

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(self._auto_title(y_label, x_label))
        plt.tight_layout()
