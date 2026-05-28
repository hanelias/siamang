"""Variable and VariableMap implementation for siamang."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from siamang.core.expression import Expression, compare

_VALID_SCALES = {"nominal", "ordinal", "interval", "ratio"}
_VALID_DTYPES = {"int", "float", "str", "bool", "category", "datetime"}
_VALID_ROLES = {"input", "target", "weight", "id", "grouping", "derived"}
_VALID_MISSING_KINDS = {
    "refusal",
    "dont_know",
    "not_applicable",
    "not_asked",
    "system_missing",
}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    variable: str | None = None
    column: str | None = None


@dataclass(frozen=True, slots=True)
class MissingValue:
    code: Any
    label: str
    kind: str = "system_missing"

    def __post_init__(self) -> None:
        normalized_kind = self.kind.lower().strip()
        if normalized_kind not in _VALID_MISSING_KINDS:
            allowed = ", ".join(sorted(_VALID_MISSING_KINDS))
            raise ValueError(f"Unknown missing value kind '{self.kind}'. Allowed kinds: {allowed}.")
        if not self.label:
            raise ValueError("MissingValue label must not be empty.")
        object.__setattr__(self, "kind", normalized_kind)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "label": self.label, "kind": self.kind}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MissingValue:
        return cls(
            code=payload["code"],
            label=payload.get("label") or str(payload["code"]),
            kind=payload.get("kind", "system_missing"),
        )


@dataclass(frozen=True, slots=True)
class Variable:
    """Atomic measurement unit used across survey lifecycle."""

    name: str
    scale: str
    label: str | None = None
    labels: dict[Any, str] = field(default_factory=dict)
    missing_values: tuple[Any, ...] = field(default_factory=tuple)
    dtype: str | None = None
    role: str | None = None
    description: str | None = None
    construct: str | None = None
    source: str | None = None
    valid_range: tuple[Any, Any] | None = None
    missing_labels: dict[Any, str] = field(default_factory=dict)
    missing: tuple[MissingValue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Variable name must not be empty.")

        normalized_scale = self.scale.lower().strip()
        if normalized_scale not in _VALID_SCALES:
            allowed = ", ".join(sorted(_VALID_SCALES))
            raise ValueError(f"Unknown scale '{self.scale}'. Allowed scales: {allowed}.")

        object.__setattr__(self, "scale", normalized_scale)
        explicit_missing = tuple(_coerce_missing_value(item) for item in self.missing)
        legacy_missing_values = tuple(self.missing_values)
        explicit_missing_codes = {item.code for item in explicit_missing}
        unknown_missing = [
            code
            for code in self.missing_labels
            if code not in legacy_missing_values and code not in explicit_missing_codes
        ]
        if unknown_missing:
            raise ValueError(
                "missing_labels contains codes not present in missing_values or missing: "
                + ", ".join(map(str, unknown_missing))
            )
        normalized_missing = _normalize_missing_values(
            explicit_missing, legacy_missing_values, self.missing_labels
        )
        object.__setattr__(self, "missing", normalized_missing)
        object.__setattr__(self, "missing_values", tuple(item.code for item in normalized_missing))
        merged_missing_labels = dict(self.missing_labels)
        for item in explicit_missing:
            merged_missing_labels.setdefault(item.code, item.label)
        object.__setattr__(self, "missing_labels", merged_missing_labels)
        if self.dtype is not None:
            normalized_dtype = self.dtype.lower().strip()
            if normalized_dtype not in _VALID_DTYPES:
                allowed = ", ".join(sorted(_VALID_DTYPES))
                raise ValueError(f"Unknown dtype '{self.dtype}'. Allowed dtypes: {allowed}.")
            object.__setattr__(self, "dtype", normalized_dtype)
        if self.role is not None:
            normalized_role = self.role.lower().strip()
            if normalized_role not in _VALID_ROLES:
                allowed = ", ".join(sorted(_VALID_ROLES))
                raise ValueError(f"Unknown role '{self.role}'. Allowed roles: {allowed}.")
            object.__setattr__(self, "role", normalized_role)
        if self.valid_range is not None and len(self.valid_range) != 2:
            raise ValueError("valid_range must be a 2-item tuple (min, max).")
        if self.valid_range is not None:
            min_value, max_value = self.valid_range
            if min_value is not None and max_value is not None and min_value > max_value:
                raise ValueError("valid_range must be ordered as (min, max).")
            object.__setattr__(self, "valid_range", tuple(self.valid_range))

    def structured_missing_values(self) -> tuple[MissingValue, ...]:
        return self.missing

    def missing_kinds_dict(self) -> dict[Any, str]:
        return {item.code: item.kind for item in self.missing}

    def is_missing(self, value: Any) -> bool:
        """Return True when value is configured as missing for this variable."""

        return value in self.missing_values

    def eq(self, other: Any) -> Expression:
        return compare(self.name, "=", other)

    def ne(self, other: Any) -> Expression:
        return compare(self.name, "!=", other)

    def gt(self, other: Any) -> Expression:
        return compare(self.name, ">", other)

    def ge(self, other: Any) -> Expression:
        return compare(self.name, ">=", other)

    def lt(self, other: Any) -> Expression:
        return compare(self.name, "<", other)

    def le(self, other: Any) -> Expression:
        return compare(self.name, "<=", other)

    def isin(self, values: Any) -> Expression:
        return compare(self.name, "in", values)

    def notin(self, values: Any) -> Expression:
        return compare(self.name, "not in", values)

    def __gt__(self, other: Any) -> Expression:
        return self.gt(other)

    def __ge__(self, other: Any) -> Expression:
        return self.ge(other)

    def __lt__(self, other: Any) -> Expression:
        return self.lt(other)

    def __le__(self, other: Any) -> Expression:
        return self.le(other)


class VariableMap(dict[str, Variable]):
    """Dictionary-like registry of variables indexed by name."""

    def add(self, variable: Variable) -> None:
        if variable.name in self:
            raise KeyError(f"Variable '{variable.name}' already exists.")
        self[variable.name] = variable

    def require(self, name: str) -> Variable:
        try:
            return self[name]
        except KeyError as exc:
            raise KeyError(f"Variable '{name}' is not registered.") from exc

    def add_many(self, variables: list[Variable]) -> None:
        for variable in variables:
            self.add(variable)

    def by_scale(self, scale: str) -> list[Variable]:
        normalized = scale.lower().strip()
        return [variable for variable in self.values() if variable.scale == normalized]

    def by_role(self, role: str) -> list[Variable]:
        normalized = role.lower().strip()
        return [
            variable
            for variable in self.values()
            if (variable.role or "").lower().strip() == normalized
        ]

    def labels_dict(self) -> dict[str, str]:
        return {name: (variable.label or name) for name, variable in self.items()}

    def value_labels_dict(self) -> dict[str, dict[Any, str]]:
        return {name: dict(variable.labels) for name, variable in self.items()}

    def missing_dict(self) -> dict[str, list[Any]]:
        return {name: list(variable.missing_values) for name, variable in self.items()}

    def missing_labels_dict(self) -> dict[str, dict[Any, str]]:
        return {name: dict(variable.missing_labels) for name, variable in self.items()}

    def missing_kinds_dict(self) -> dict[str, dict[Any, str]]:
        return {name: variable.missing_kinds_dict() for name, variable in self.items()}

    def validate_frame(
        self, frame: pd.DataFrame, raise_on_error: bool = False
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        expected = set(self.keys())
        actual = set(frame.columns)

        for name in sorted(expected - actual):
            issues.append(
                ValidationIssue(
                    code="MISSING_COLUMN",
                    severity="error",
                    message=f"Variable '{name}' is missing from DataFrame.",
                    variable=name,
                    column=name,
                )
            )
        for name in sorted(actual - expected):
            issues.append(
                ValidationIssue(
                    code="EXTRA_COLUMN",
                    severity="warning",
                    message=f"DataFrame column '{name}' is not declared in VariableMap.",
                    column=name,
                )
            )

        for variable in self.values():
            if variable.name not in frame.columns:
                continue
            series = frame[variable.name]
            non_missing = series.dropna()
            analytic_values = _drop_configured_missing(non_missing, variable.missing_values)

            issues.extend(_dtype_issues(variable, analytic_values))
            issues.extend(_range_issues(variable, analytic_values))
            issues.extend(_label_issues(variable, analytic_values))
            issues.extend(_missing_value_issues(variable))
            issues.extend(_role_issues(variable, series))

        if raise_on_error and any(issue.severity == "error" for issue in issues):
            codes = ", ".join(issue.code for issue in issues if issue.severity == "error")
            raise ValueError(f"DataFrame validation failed: {codes}")
        return issues

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "name": variable.name,
                "scale": variable.scale,
                "label": variable.label,
                "labels": dict(variable.labels),
                "missing_values": list(variable.missing_values),
                "dtype": variable.dtype,
                "role": variable.role,
                "description": variable.description,
                "construct": variable.construct,
                "source": variable.source,
                "valid_range": list(variable.valid_range)
                if variable.valid_range is not None
                else None,
                "missing_labels": dict(variable.missing_labels),
                "missing": [item.to_dict() for item in variable.structured_missing_values()],
            }
            for name, variable in self.items()
        }

    @classmethod
    def from_dict(cls, payload: dict[str, dict[str, Any]]) -> VariableMap:
        def _normalize_key(key: Any) -> Any:
            if isinstance(key, str):
                try:
                    return int(key)
                except ValueError:
                    try:
                        return float(key)
                    except ValueError:
                        return key
            return key

        def _normalize_mapping_keys(mapping: dict[Any, Any]) -> dict[Any, Any]:
            return {_normalize_key(k): v for k, v in mapping.items()}

        variable_map = cls()
        for item in payload.values():
            variable_map.add(
                Variable(
                    name=item["name"],
                    scale=item["scale"],
                    label=item.get("label"),
                    labels=_normalize_mapping_keys(item.get("labels", {})),
                    missing_values=item.get("missing_values", ()),
                    dtype=item.get("dtype"),
                    role=item.get("role"),
                    description=item.get("description"),
                    construct=item.get("construct"),
                    source=item.get("source"),
                    valid_range=tuple(item["valid_range"])
                    if item.get("valid_range") is not None
                    else None,
                    missing_labels=_normalize_mapping_keys(item.get("missing_labels", {})),
                    missing=tuple(
                        MissingValue.from_dict(missing_item)
                        for missing_item in item.get("missing", [])
                    ),
                )
            )
        return variable_map


def _drop_configured_missing(values: pd.Series, missing_values: tuple[Any, ...]) -> pd.Series:
    configured_missing = set(missing_values)
    if not configured_missing or values.empty:
        return values
    missing_mask = values.map(
        lambda value: (
            False if isinstance(value, list | tuple | set) else value in configured_missing
        )
    )
    return values[~missing_mask]


def _coerce_missing_value(value: MissingValue | dict[str, Any]) -> MissingValue:
    if isinstance(value, MissingValue):
        return value
    if isinstance(value, dict):
        return MissingValue.from_dict(value)
    raise TypeError("missing entries must be MissingValue instances or dictionaries.")


def _normalize_missing_values(
    missing: tuple[MissingValue, ...],
    missing_values: tuple[Any, ...],
    missing_labels: dict[Any, str],
) -> tuple[MissingValue, ...]:
    items: list[MissingValue] = []
    seen: set[Any] = set()

    for missing_value in missing:
        items.append(missing_value)
        seen.add(missing_value.code)

    for code in missing_values:
        if code in seen:
            continue
        items.append(
            MissingValue(
                code=code,
                label=missing_labels.get(code) or str(code),
                kind="system_missing",
            )
        )
        seen.add(code)
    return tuple(items)


def _dtype_issues(variable: Variable, values: pd.Series) -> list[ValidationIssue]:
    if variable.dtype is None or values.empty:
        return []
    valid = True
    if variable.dtype in {"int", "float"}:
        valid = pd.api.types.is_numeric_dtype(values)
        if valid and variable.dtype == "int":
            valid = bool((values % 1 == 0).all())
    elif variable.dtype == "bool":
        valid = pd.api.types.is_bool_dtype(values) or values.isin([True, False, 0, 1]).all()
    elif variable.dtype in {"str", "category"}:
        valid = (
            pd.api.types.is_string_dtype(values)
            or isinstance(values.dtype, pd.CategoricalDtype)
            or values.map(lambda v: isinstance(v, str)).all()
        )
    elif variable.dtype == "datetime":
        valid = pd.api.types.is_datetime64_any_dtype(values)
    if valid:
        return []
    return [
        ValidationIssue(
            code="INVALID_DTYPE",
            severity="error",
            message=f"Variable '{variable.name}' values are incompatible with dtype '{variable.dtype}'.",
            variable=variable.name,
            column=variable.name,
        )
    ]


def _range_issues(variable: Variable, values: pd.Series) -> list[ValidationIssue]:
    if variable.valid_range is None or values.empty:
        return []
    minimum, maximum = variable.valid_range
    numeric = pd.to_numeric(values, errors="coerce")
    invalid_mask = numeric.isna()
    if minimum is not None:
        invalid_mask = invalid_mask | (numeric < minimum)
    if maximum is not None:
        invalid_mask = invalid_mask | (numeric > maximum)
    if not invalid_mask.any():
        return []
    return [
        ValidationIssue(
            code="OUT_OF_RANGE",
            severity="error",
            message=f"Variable '{variable.name}' has values outside valid_range {variable.valid_range}.",
            variable=variable.name,
            column=variable.name,
        )
    ]


def _label_issues(variable: Variable, values: pd.Series) -> list[ValidationIssue]:
    if variable.scale not in {"nominal", "ordinal"} or not variable.labels or values.empty:
        return []
    observed = set(_flatten_observed_values(values))
    invalid = observed - set(variable.labels)
    if not invalid:
        return []
    return [
        ValidationIssue(
            code="INVALID_LABEL_VALUE",
            severity="error",
            message=f"Variable '{variable.name}' has values not present in labels: {', '.join(map(str, sorted(invalid, key=repr)))}.",
            variable=variable.name,
            column=variable.name,
        )
    ]


def _flatten_observed_values(values: pd.Series) -> list[Any]:
    observed: list[Any] = []
    for value in values:
        if isinstance(value, list | tuple | set):
            observed.extend(value)
        else:
            observed.append(value)
    return observed


def _missing_value_issues(variable: Variable) -> list[ValidationIssue]:
    missing_without_labels = set(variable.missing_values) - set(variable.missing_labels)
    if not missing_without_labels:
        return []
    return [
        ValidationIssue(
            code="MISSING_VALUE_WITHOUT_LABEL",
            severity="warning",
            message=f"Variable '{variable.name}' has missing values without labels: {', '.join(map(str, sorted(missing_without_labels, key=repr)))}.",
            variable=variable.name,
            column=variable.name,
        )
    ]


def _role_issues(variable: Variable, series: pd.Series) -> list[ValidationIssue]:
    if variable.role == "weight" and not pd.api.types.is_numeric_dtype(series.dropna()):
        return [
            ValidationIssue(
                code="INVALID_WEIGHT",
                severity="error",
                message=f"Weight variable '{variable.name}' must be numeric.",
                variable=variable.name,
                column=variable.name,
            )
        ]
    if variable.role == "id" and series.dropna().duplicated().any():
        return [
            ValidationIssue(
                code="DUPLICATE_ID",
                severity="error",
                message=f"ID variable '{variable.name}' contains duplicate values.",
                variable=variable.name,
                column=variable.name,
            )
        ]
    return []
