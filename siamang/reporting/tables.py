"""Declarative table components for survey reporting.

Each table class auto-resolves variable labels and value labels from the
attached SurveyData metadata, similar to SPSS output tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_label(data: SurveyData, var_name: str) -> str:
    """Get the human-readable label for a variable, falling back to the name."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].label or var_name
    return var_name


def _get_value_labels(data: SurveyData, var_name: str) -> dict[Any, str]:
    """Get value labels for a variable."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].labels or {}
    return {}


def _get_scale(data: SurveyData, var_name: str) -> str | None:
    """Get measurement scale for a variable."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].scale
    return None


def _frame_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a GitHub-flavored Markdown pipe table."""
    lines = []
    headers = list(df.columns)
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines)


def _frame_to_html(df: pd.DataFrame, caption: str | None = None) -> str:
    """Convert a DataFrame to a clean HTML table."""
    html = df.to_html(index=False, classes="siamang-table", border=0)
    if caption:
        html = html.replace("<table", f"<table>\n<caption>{caption}</caption", 1)
    return html


# ─── Base Class ───────────────────────────────────────────────────────────────


@dataclass
class SurveyTable:
    """Base class for all declarative table components."""

    data: SurveyData
    _result: pd.DataFrame = field(init=False, repr=False, default=None)
    _stats: dict[str, Any] = field(init=False, repr=False, default_factory=dict)

    def _build(self) -> None:
        """Build the table. Subclasses must implement this."""
        raise NotImplementedError

    def _ensure_built(self) -> None:
        if self._result is None:
            self._build()

    def to_frame(self) -> pd.DataFrame:
        """Return the table as a pandas DataFrame."""
        self._ensure_built()
        return self._result.copy()

    def to_markdown(self) -> str:
        """Return the table as a GitHub-flavored Markdown string."""
        self._ensure_built()
        md = _frame_to_markdown(self._result)
        if self._stats:
            md += "\n\n" + self._format_stats()
        return md

    def to_html(self) -> str:
        """Return the table as an HTML string."""
        self._ensure_built()
        html = _frame_to_html(self._result)
        if self._stats:
            html += f"\n<p class='siamang-stats'>{self._format_stats()}</p>"
        return html

    def export_xlsx(self, path: str | Path) -> Path:
        """Export the table to an Excel file."""
        self._ensure_built()
        path = Path(path)
        self._result.to_excel(path, index=False, sheet_name="Table")
        return path

    def _format_stats(self) -> str:
        """Format statistics footer."""
        parts = []
        for key, val in self._stats.items():
            if isinstance(val, float):
                parts.append(f"{key} = {val:.4f}")
            else:
                parts.append(f"{key} = {val}")
        return "; ".join(parts)

    def __repr__(self) -> str:
        self._ensure_built()
        return self._result.to_string()

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self.to_html()


# ─── FreqTable ────────────────────────────────────────────────────────────────


@dataclass
class FreqTable(SurveyTable):
    """Univariate frequency distribution table.

    Automatically resolves value labels and computes N, %, and cumulative %.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    column : str
        Name of the variable to tabulate.
    exclude_missing : bool
        If True (default), excludes rows where the column is NaN.
    sort : str
        Sort order: "value" (by code, default), "freq" (by count descending),
        or "label" (alphabetical by label).
    """

    column: str = ""
    exclude_missing: bool = True
    sort: str = "value"

    def _build(self) -> None:
        col = self.column
        series = self.data.frame[col]

        if self.exclude_missing:
            series = series.dropna()

        counts = series.value_counts(dropna=self.exclude_missing)
        value_labels = _get_value_labels(self.data, col)

        rows = []
        for value in sorted(counts.index):
            n = int(counts[value])
            label = value_labels.get(value, str(value))
            rows.append({"Value": value, "Label": label, "N": n})

        if rows:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(columns=["Value", "Label", "N"])

        if self.sort == "freq" and not df.empty:
            df = df.sort_values("N", ascending=False).reset_index(drop=True)
        elif self.sort == "label" and not df.empty:
            df = df.sort_values("Label").reset_index(drop=True)

        total = int(df["N"].sum()) if not df.empty else 0
        df["%"] = (df["N"] / total * 100).round(1) if total > 0 else 0.0
        df["Cumulative %"] = df["%"].cumsum().round(1) if not df.empty else 0.0

        # Append total row
        total_row = pd.DataFrame(
            [
                {
                    "Value": "",
                    "Label": "Total",
                    "N": total,
                    "%": 100.0,
                    "Cumulative %": 100.0,
                }
            ]
        )
        df = pd.concat([df, total_row], ignore_index=True)

        self._result = df
        self._stats = {"Variable": _get_label(self.data, col), "N valid": int(total)}


# ─── CrossTable ───────────────────────────────────────────────────────────────


@dataclass
class CrossTable(SurveyTable):
    """Bivariate cross-tabulation with optional statistical tests.

    Automatically resolves value labels for both variables and computes
    Chi-square, Cramer's V, and significance.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    row : str
        Row variable name (independent variable).
    col : str
        Column variable name (dependent variable).
    pct : str
        Percentage direction: "none", "row", "col", or "total".
    test : bool
        If True, runs Chi-square test and reports chi2, df, p, Cramer's V.
    """

    row: str = ""
    col: str = ""
    pct: str = "none"
    test: bool = True

    def _build(self) -> None:
        frame = self.data.frame[[self.row, self.col]].dropna()
        row_labels = _get_value_labels(self.data, self.row)
        col_labels = _get_value_labels(self.data, self.col)

        # Build contingency table
        contingency = pd.crosstab(frame[self.row], frame[self.col])

        # Apply percentage normalization
        if self.pct == "row":
            display = contingency.div(contingency.sum(axis=1), axis=0) * 100
        elif self.pct == "col":
            display = contingency.div(contingency.sum(axis=0), axis=1) * 100
        elif self.pct == "total":
            display = contingency / contingency.values.sum() * 100
        else:
            display = contingency.copy()

        display = display.round(1)

        # Apply labels
        if row_labels:
            display.index = [row_labels.get(v, str(v)) for v in display.index]
        if col_labels:
            display.columns = [col_labels.get(v, str(v)) for v in display.columns]

        # Add row/column totals
        display["Total"] = contingency.sum(axis=1).values
        total_col = list(contingency.sum(axis=0).values) + [contingency.values.sum()]
        display.loc["Total"] = total_col[: len(display.columns)]

        # Reset index for clean output
        display = display.reset_index()
        display = display.rename(columns={"index": _get_label(self.data, self.row)})

        self._result = display

        # Statistical tests
        if self.test:
            try:
                from scipy.stats import chi2_contingency

                chi2_stat, p_value, dof, _ = chi2_contingency(contingency.values)
                n = contingency.values.sum()
                min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
                cramers_v = (chi2_stat / (n * min_dim)) ** 0.5 if n > 0 and min_dim > 0 else 0.0
                self._stats = {
                    "χ²": round(chi2_stat, 3),
                    "df": int(dof),
                    "p": round(p_value, 4),
                    "Cramér's V": round(cramers_v, 3),
                    "N": int(n),
                }
            except ImportError:
                self._stats = {"error": "scipy not installed"}


# ─── GroupMeanTable ───────────────────────────────────────────────────────────


@dataclass
class GroupMeanTable(SurveyTable):
    """Grouped means comparison table with automatic significance testing.

    Compares the mean of a continuous variable across categories of a
    grouping variable. Automatically selects the appropriate test based
    on the number of groups and the measurement scale.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    column : str
        Continuous dependent variable (interval/ratio).
    by : str
        Categorical grouping variable (nominal/ordinal).
    test : bool
        If True, automatically runs the appropriate significance test:
        - 2 groups: Mann-Whitney U (ordinal) or Independent t-test (interval/ratio)
        - 3+ groups: Kruskal-Wallis H (ordinal) or One-way ANOVA (interval/ratio)
    """

    column: str = ""
    by: str = ""
    test: bool = True

    def _build(self) -> None:
        frame = self.data.frame[[self.column, self.by]].dropna()
        by_labels = _get_value_labels(self.data, self.by)
        col_label = _get_label(self.data, self.column)
        col_scale = _get_scale(self.data, self.column)

        grouped = frame.groupby(self.by)[self.column]
        agg = grouped.agg(["mean", "std", "median", "count"])
        agg = agg.round(3)

        # Apply group labels
        if by_labels:
            agg.index = [by_labels.get(v, str(v)) for v in agg.index]

        agg = agg.reset_index()
        by_col_label = _get_label(self.data, self.by)
        agg.columns = [by_col_label, "Mean", "SD", "Median", "N"]

        self._result = agg

        # Significance testing
        if self.test:
            groups = [g[self.column].values for _, g in frame.groupby(self.by)]
            n_groups = len(groups)

            if n_groups < 2:
                self._stats = {"note": "fewer than 2 groups, no test performed"}
                return

            try:
                from scipy import stats as sp_stats

                # Choose test based on scale and number of groups
                use_nonparametric = col_scale in ("ordinal", None)

                if n_groups == 2:
                    if use_nonparametric:
                        stat, p = sp_stats.mannwhitneyu(
                            groups[0], groups[1], alternative="two-sided"
                        )
                        self._stats = {"Mann-Whitney U": round(stat, 3), "p": round(p, 4)}
                    else:
                        stat, p = sp_stats.ttest_ind(groups[0], groups[1])
                        self._stats = {"t": round(stat, 3), "p": round(p, 4)}
                else:
                    if use_nonparametric:
                        stat, p = sp_stats.kruskal(*groups)
                        self._stats = {"Kruskal-Wallis H": round(stat, 3), "p": round(p, 4)}
                    else:
                        stat, p = sp_stats.f_oneway(*groups)
                        self._stats = {"F": round(stat, 3), "p": round(p, 4)}

                self._stats["N"] = int(frame.shape[0])
                self._stats["Variable"] = col_label

            except ImportError:
                self._stats = {"error": "scipy not installed"}
