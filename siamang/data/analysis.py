"""Descriptive analysis helpers for SurveyData."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import pandas as pd

from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class DataAnalysis:
    frame: pd.DataFrame
    weight_column: str | None = None
    variables: VariableMap | None = None

    def mean(self, column: str, weighted: bool = False) -> float:
        values = self.frame[column].dropna().astype(float)
        if values.empty:
            return 0.0
        if not weighted:
            return float(values.mean())
        if self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        weights = self.frame.loc[values.index, self.weight_column].astype(float)
        weight_sum = float(weights.sum())
        if weight_sum <= 0:
            return 0.0
        return float((values * weights).sum() / weight_sum)

    def median(self, column: str) -> float:
        values = self.frame[column].dropna().astype(float)
        if values.empty:
            return 0.0
        return float(values.median())

    def grouped_mean(
        self,
        column: str,
        by: str,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.DataFrame:
        selected_columns = [column, by] + (
            [self.weight_column] if weighted and self.weight_column else []
        )
        frame = self.frame[selected_columns].dropna(subset=[column, by])
        if weighted and self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        rows = []
        label_map = (
            self.variables[by].labels
            if labels and self.variables is not None and by in self.variables
            else {}
        )
        for group_value, group in frame.groupby(by, dropna=False):
            values = group[column].astype(float)
            if weighted:
                weights = group[self.weight_column].astype(float)
                weight_sum = float(weights.sum())
                mean_value = float((values * weights).sum() / weight_sum) if weight_sum > 0 else 0.0
                n_value = weight_sum
            else:
                mean_value = float(values.mean()) if not values.empty else 0.0
                n_value = float(values.shape[0])
            row = {"group": group_value, "mean": mean_value, "n": n_value}
            if labels:
                row["label"] = label_map.get(group_value)
            rows.append(row)
        return pd.DataFrame(rows)

    def kruskal(self, column: str, group: str) -> dict[str, float]:
        try:
            from scipy.stats import kruskal
        except ImportError as exc:
            raise ImportError("kruskal() requires scipy to be installed.") from exc
        groups = [
            values[column].dropna().astype(float).to_numpy()
            for _, values in self.frame[[column, group]].dropna().groupby(group)
        ]
        if len(groups) < 2:
            raise ValueError("kruskal() requires at least two non-empty groups.")
        statistic, p_value = kruskal(*groups)
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "groups": float(len(groups)),
        }

    def mannwhitney(self, column: str, group: str) -> dict[str, float | object]:
        try:
            from scipy.stats import mannwhitneyu
        except ImportError as exc:
            raise ImportError("mannwhitney() requires scipy to be installed.") from exc
        grouped = list(self.frame[[column, group]].dropna().groupby(group))
        if len(grouped) != 2:
            raise ValueError("mannwhitney() requires exactly two non-empty groups.")
        (group_a, values_a), (group_b, values_b) = grouped
        statistic, p_value = mannwhitneyu(
            values_a[column].astype(float),
            values_b[column].astype(float),
            alternative="two-sided",
        )
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "group_a": group_a,
            "group_b": group_b,
        }

    def spearman(self, x: str, y: str) -> dict[str, float]:
        try:
            from scipy.stats import spearmanr
        except ImportError as exc:
            raise ImportError("spearman() requires scipy to be installed.") from exc
        frame = self.frame[[x, y]].dropna()
        if frame.empty:
            return {"rho": 0.0, "p_value": 1.0, "n": 0.0}
        result = spearmanr(frame[x], frame[y])
        return {
            "rho": float(result.statistic),
            "p_value": float(result.pvalue),
            "n": float(frame.shape[0]),
        }

    def frequencies(
        self,
        column: str,
        normalize: bool = False,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.Series | pd.DataFrame:
        if not weighted:
            counts = self.frame[column].value_counts(normalize=normalize, dropna=False)
            return self._with_labels(column, counts) if labels else counts
        if self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        grouped = self.frame.groupby(column, dropna=False)[self.weight_column].sum()
        if normalize:
            total = grouped.sum()
            if total == 0:
                counts = grouped * 0
            else:
                counts = grouped / total
        else:
            counts = grouped
        return self._with_labels(column, counts) if labels else counts

    def crosstab(
        self,
        row: str,
        col: str,
        normalize: str | bool = False,
        chi2: bool = False,
        cramers_v: bool = False,
        phi: bool = False,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, float]]:
        norm = normalize if normalize is not False else False
        if weighted:
            if self.weight_column is None:
                raise ValueError("weighted=True requires SurveyData.weight to be set.")
            table = pd.pivot_table(
                self.frame,
                index=row,
                columns=col,
                values=self.weight_column,
                aggfunc="sum",
                fill_value=0.0,
            )
            if norm:
                if norm == "index":
                    table = table.div(table.sum(axis=1).replace({0: pd.NA}), axis=0).fillna(0.0)
                elif norm == "columns":
                    table = table.div(table.sum(axis=0).replace({0: pd.NA}), axis=1).fillna(0.0)
                elif norm is True or norm == "all":
                    total = table.values.sum()
                    table = table / total if total else table * 0.0
                else:
                    raise ValueError(
                        "normalize must be one of False, 'index', 'columns', 'all', or True"
                    )
        else:
            table = pd.crosstab(self.frame[row], self.frame[col], normalize=norm, dropna=False)
        if labels:
            table = self._labeled_crosstab(table, row=row, col=col)
        if not chi2 and not cramers_v and not phi:
            return table
        contingency = pd.crosstab(self.frame[row], self.frame[col], dropna=False)
        try:
            from scipy.stats import chi2_contingency
        except ImportError as exc:
            raise ImportError(
                "chi2=True or cramers_v=True requires scipy to be installed."
            ) from exc
        chi2_stat, p_value, dof, _ = chi2_contingency(contingency.values)
        stats = {"chi2": float(chi2_stat), "p_value": float(p_value), "dof": float(dof)}
        if cramers_v:
            n = float(contingency.values.sum())
            rows, cols = contingency.shape
            min_dim = min(rows - 1, cols - 1)
            stats["cramers_v"] = (
                float((chi2_stat / (n * min_dim)) ** 0.5) if n > 0 and min_dim > 0 else 0.0
            )
        if phi:
            rows, cols = contingency.shape
            n = float(contingency.values.sum())
            if rows == 2 and cols == 2 and n > 0:
                stats["phi"] = float((chi2_stat / n) ** 0.5)
            else:
                raise ValueError("phi=True is only supported for 2x2 tables.")
        return table, stats

    def proportion_ci(
        self,
        column: str,
        value: object,
        confidence: float = 0.95,
        weighted: bool = False,
    ) -> dict[str, float]:
        if confidence <= 0 or confidence >= 1:
            raise ValueError("confidence must be in (0, 1)")
        z = NormalDist().inv_cdf((1 + confidence) / 2)
        if weighted:
            if self.weight_column is None:
                raise ValueError("weighted=True requires SurveyData.weight to be set.")
            weights = self.frame[self.weight_column].astype(float)
            indicator = (self.frame[column] == value).astype(float)
            n_eff = self.effective_sample_size()
            weight_sum = float(weights.sum())
            if n_eff <= 0 or weight_sum <= 0:
                return {"p": 0.0, "lower": 0.0, "upper": 0.0, "n": 0.0}
            p = float((indicator * weights).sum() / weight_sum)
            n = n_eff
        else:
            n = float(self.frame[column].notna().sum())
            if n <= 0:
                return {"p": 0.0, "lower": 0.0, "upper": 0.0, "n": 0.0}
            p = float((self.frame[column] == value).sum() / n)
        margin = z * ((p * (1 - p) / n) ** 0.5)
        lower = max(0.0, p - margin)
        upper = min(1.0, p + margin)
        return {"p": p, "lower": lower, "upper": upper, "n": n}

    def effective_sample_size(self) -> float:
        if self.weight_column is None:
            raise ValueError("effective_sample_size requires SurveyData.weight to be set.")
        weights = self.frame[self.weight_column].astype(float)
        sum_w = float(weights.sum())
        sum_w2 = float((weights**2).sum())
        if sum_w <= 0 or sum_w2 <= 0:
            return 0.0
        return (sum_w**2) / sum_w2

    def _with_labels(self, column: str, counts: pd.Series) -> pd.DataFrame:
        label_map: dict[object, str] = {}
        if self.variables is not None and column in self.variables:
            label_map = self.variables[column].labels
        total = float(counts.sum()) if len(counts) else 0.0
        rows = []
        for value, n in counts.items():
            n_float = float(n)
            percent = (n_float / total) if total else 0.0
            rows.append(
                {
                    "value": value,
                    "label": label_map.get(value),
                    "n": n_float,
                    "percent": percent,
                }
            )
        return pd.DataFrame(rows)

    def _labeled_crosstab(self, table: pd.DataFrame, row: str, col: str) -> pd.DataFrame:
        labeled = table.copy()
        if self.variables is not None and row in self.variables:
            row_map = self.variables[row].labels
            labeled.index = [row_map.get(value, value) for value in labeled.index]
        if self.variables is not None and col in self.variables:
            col_map = self.variables[col].labels
            labeled.columns = [col_map.get(value, value) for value in labeled.columns]
        return labeled
