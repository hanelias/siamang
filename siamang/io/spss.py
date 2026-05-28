"""SPSS (.sav) I/O via optional pyreadstat."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data.survey_data import SurveyData


class SPSSWriter:
    def write(self, data: SurveyData, path: str | Path, **kwargs: Any) -> Path:
        pyreadstat = _require_pyreadstat()
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pyreadstat.write_sav(
            data.frame,
            output,
            column_labels=_column_labels(data.variables),
            variable_value_labels=_value_labels(data.variables),
            missing_ranges=_missing_ranges(data.variables),
            variable_measure=_variable_measure(data.variables),
            **kwargs,
        )
        return output


class SPSSReader:
    def read(self, path: str | Path, **kwargs: Any) -> SurveyData:
        pyreadstat = _require_pyreadstat()
        kwargs.setdefault("user_missing", True)
        frame, meta = pyreadstat.read_sav(path, **kwargs)
        return SurveyData(frame=frame, variables=_variables_from_meta(meta))


def read_spss(path: str | Path, **kwargs: Any) -> SurveyData:
    return SPSSReader().read(path, **kwargs)


def _require_pyreadstat():
    try:
        import pyreadstat
    except ImportError as exc:
        raise ImportError("SPSS I/O requires pyreadstat to be installed.") from exc
    return pyreadstat


def _column_labels(variables: VariableMap | None) -> dict[str, str] | None:
    if variables is None:
        return None
    return {name: variable.label or name for name, variable in variables.items()}


def _value_labels(variables: VariableMap | None) -> dict[str, dict[Any, str]] | None:
    if variables is None:
        return None
    labels: dict[str, dict[Any, str]] = {}
    for name, variable in variables.items():
        value_labels = dict(variable.labels)
        for code, label in variable.missing_labels.items():
            value_labels.setdefault(code, label)
        if value_labels:
            labels[name] = value_labels
    return labels or None


def _missing_ranges(variables: VariableMap | None) -> dict[str, list[Any]] | None:
    if variables is None:
        return None
    missing = {
        name: list(variable.missing_values)
        for name, variable in variables.items()
        if variable.missing_values
    }
    return missing or None


def _variable_measure(variables: VariableMap | None) -> dict[str, str] | None:
    if variables is None:
        return None
    measure = {}
    for name, variable in variables.items():
        if variable.scale in {"nominal", "ordinal"}:
            measure[name] = variable.scale
        else:
            measure[name] = "scale"
    return measure


def _variables_from_meta(meta: Any) -> VariableMap:
    variable_map = VariableMap()
    names = getattr(meta, "column_names", [])
    column_labels = getattr(meta, "column_names_to_labels", {}) or {}
    value_labels = getattr(meta, "variable_value_labels", {}) or {}
    missing_ranges = getattr(meta, "missing_ranges", {}) or {}
    variable_measure = getattr(meta, "variable_measure", {}) or {}
    for name in names:
        scale = _scale_from_measure(variable_measure.get(name))
        variable_map.add(
            Variable(
                name=name,
                scale=scale,
                label=column_labels.get(name),
                labels=_analytic_value_labels(
                    value_labels.get(name, {}),
                    missing_ranges.get(name, []),
                ),
                missing=_missing_from_ranges(
                    missing_ranges.get(name, []),
                    value_labels.get(name, {}),
                ),
            )
        )
    return variable_map


def _scale_from_measure(measure: str | None) -> str:
    if measure in {"nominal", "ordinal"}:
        return measure
    return "interval"


def _analytic_value_labels(
    labels: dict[Any, str],
    missing_ranges: list[Any],
) -> dict[Any, str]:
    missing_codes = set(_discrete_missing_codes(missing_ranges))
    if not missing_codes:
        return dict(labels)
    return {code: label for code, label in labels.items() if code not in missing_codes}


def _missing_from_ranges(
    ranges: list[Any],
    labels: dict[Any, str] | None = None,
) -> tuple[MissingValue, ...]:
    labels = labels or {}
    missing = []
    for code in _discrete_missing_codes(ranges):
        missing.append(MissingValue(code, labels.get(code) or str(code), "system_missing"))
    return tuple(missing)


def _discrete_missing_codes(ranges: list[Any]) -> list[Any]:
    codes = []
    for item in ranges:
        if isinstance(item, dict):
            lo = item.get("lo")
            hi = item.get("hi")
            if lo == hi:
                codes.append(lo)
        else:
            codes.append(item)
    return codes
