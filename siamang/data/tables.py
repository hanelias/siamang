"""Export-friendly survey table builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class BannerTable:
    frame: pd.DataFrame

    def export_csv(self, path: str | Path, **kwargs: Any) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.frame.to_csv(output, index=False, **kwargs)
        return output

    def export_xlsx(self, path: str | Path, **kwargs: Any) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.frame.to_excel(output, index=False, **kwargs)
        return output


@dataclass(frozen=True, slots=True)
class SurveyTables:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    weight_column: str | None = None

    def banner(
        self,
        rows: list[str],
        columns: list[str],
        weight: str | None = None,
        labels: bool = True,
    ) -> BannerTable:
        if not rows:
            raise ValueError("banner rows must not be empty.")
        if not columns:
            raise ValueError("banner columns must not be empty.")
        weight_column = weight or self.weight_column
        if weight_column is not None and weight_column not in self.frame.columns:
            raise ValueError(f"Weight column '{weight_column}' not found in frame.")

        parts = []
        for row in rows:
            for column in columns:
                parts.append(
                    _banner_pair(self.frame, row, column, weight_column, self.variables, labels)
                )
        if not parts:
            return BannerTable(pd.DataFrame())
        return BannerTable(pd.concat(parts, ignore_index=True))


def _banner_pair(
    frame: pd.DataFrame,
    row: str,
    column: str,
    weight_column: str | None,
    variables: VariableMap | None,
    labels: bool,
) -> pd.DataFrame:
    required = [row, column] + ([weight_column] if weight_column is not None else [])
    data = frame[required].dropna(subset=[row, column])
    if weight_column is None:
        grouped = data.groupby([row, column], dropna=False).size().reset_index(name="n")
    else:
        grouped = (
            data.groupby([row, column], dropna=False)[weight_column].sum().reset_index(name="n")
        )
    grouped["column_total"] = grouped.groupby(column)["n"].transform("sum")
    grouped["percent"] = grouped["n"] / grouped["column_total"].replace({0: pd.NA})
    grouped["percent"] = grouped["percent"].fillna(0.0)

    row_labels = _labels_for(variables, row) if labels else {}
    column_labels = _labels_for(variables, column) if labels else {}
    result = pd.DataFrame(
        {
            "row_variable": row,
            "row_value": grouped[row],
            "row_label": grouped[row].map(row_labels) if labels else None,
            "column_variable": column,
            "column_value": grouped[column],
            "column_label": grouped[column].map(column_labels) if labels else None,
            "n": grouped["n"].astype(float),
            "percent": grouped["percent"].astype(float),
        }
    )
    return result[
        [
            "row_variable",
            "row_value",
            "row_label",
            "column_variable",
            "column_value",
            "column_label",
            "n",
            "percent",
        ]
    ]


def _labels_for(variables: VariableMap | None, name: str) -> dict[Any, str]:
    if variables is None or name not in variables:
        return {}
    return variables[name].labels
