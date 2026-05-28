"""Stata (.dta) I/O via optional pyreadstat."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data.survey_data import SurveyData
from siamang.io.spss import (
    _analytic_value_labels,
    _column_labels,
    _require_pyreadstat,
    _value_labels,
)


class StataWriter:
    def write(
        self,
        data: SurveyData,
        path: str | Path,
        version: int = 15,
        **kwargs: Any,
    ) -> Path:
        pyreadstat = _require_pyreadstat()
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pyreadstat.write_dta(
            data.frame,
            output,
            column_labels=_column_labels(data.variables),
            variable_value_labels=_value_labels(data.variables),
            missing_user_values=_missing_user_values(data.variables),
            version=version,
            **kwargs,
        )
        return output


class StataReader:
    def read(self, path: str | Path, **kwargs: Any) -> SurveyData:
        pyreadstat = _require_pyreadstat()
        kwargs.setdefault("user_missing", True)
        frame, meta = pyreadstat.read_dta(path, **kwargs)
        return SurveyData(frame=frame, variables=_variables_from_meta(meta))


def read_stata(path: str | Path, **kwargs: Any) -> SurveyData:
    return StataReader().read(path, **kwargs)


def _variables_from_meta(meta: Any) -> VariableMap:
    variable_map = VariableMap()
    names = getattr(meta, "column_names", [])
    column_labels = getattr(meta, "column_names_to_labels", {}) or {}
    value_labels = getattr(meta, "variable_value_labels", {}) or {}
    missing_user_values = getattr(meta, "missing_user_values", {}) or {}
    variable_measure = getattr(meta, "variable_measure", {}) or {}
    for name in names:
        variable_map.add(
            Variable(
                name=name,
                scale=_scale_from_measure(variable_measure.get(name)),
                label=column_labels.get(name),
                labels=_analytic_value_labels(
                    value_labels.get(name, {}),
                    missing_user_values.get(name, []),
                ),
                missing=_missing_from_user_values(
                    missing_user_values.get(name, []),
                    value_labels.get(name, {}),
                ),
            )
        )
    return variable_map


def _scale_from_measure(measure: str | None) -> str:
    if measure in {"nominal", "ordinal"}:
        return measure
    return "interval"


def _missing_user_values(variables: VariableMap | None) -> dict[str, list[str]] | None:
    if variables is None:
        return None
    missing = {
        name: [
            item.code
            for item in variable.structured_missing_values()
            if _is_stata_missing_code(item.code)
        ]
        for name, variable in variables.items()
    }
    missing = {name: codes for name, codes in missing.items() if codes}
    return missing or None


def _is_stata_missing_code(code: Any) -> bool:
    return isinstance(code, str) and len(code) == 1 and "a" <= code <= "z"


def _missing_from_user_values(
    codes: list[Any],
    labels: dict[Any, str] | None = None,
) -> tuple[MissingValue, ...]:
    labels = labels or {}
    return tuple(
        MissingValue(code, labels.get(code) or str(code), "system_missing") for code in codes
    )
