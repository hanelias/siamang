"""Typed expression DSL for questionnaire visibility/branching conditions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_COMPARISON_OPS = {"=", "!=", ">", ">=", "<", "<=", "in", "not in"}
_LOGICAL_OPS = {"and", "or", "not"}
_SUPPORTED_OPS = _COMPARISON_OPS | _LOGICAL_OPS | {"raw"}


@dataclass(frozen=True, slots=True)
class VarRef:
    name: str

    def evaluate(self, answers: dict[str, Any]) -> Any:
        return answers.get(self.name)

    def variables(self) -> set[str]:
        return {self.name}

    def to_dict(self) -> dict[str, str]:
        return {"type": "var", "name": self.name}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VarRef:
        if payload.get("type") != "var" or not isinstance(payload.get("name"), str):
            raise ValueError("Variable reference payload must contain type='var' and string name.")
        return cls(payload["name"])

    def __str__(self) -> str:
        return f"{{{self.name}}}"


@dataclass(frozen=True, slots=True)
class Expression:
    op: str
    left: Any = None
    right: Any = None

    def __post_init__(self) -> None:
        # Backwards-compatible escape hatch for callers that constructed
        # Expression("{age} >= 18") before the structured DSL existed.
        if self.left is None and self.right is None and self.op not in _SUPPORTED_OPS:
            object.__setattr__(self, "left", self.op)
            object.__setattr__(self, "op", "raw")

    def __and__(self, other: Expression) -> Expression:
        return Expression("and", self, other)

    def __or__(self, other: Expression) -> Expression:
        return Expression("or", self, other)

    def __invert__(self) -> Expression:
        return Expression("not", self)

    def __str__(self) -> str:
        return self.to_surveyjs()

    def evaluate(self, answers: dict[str, Any]) -> bool:
        return bool(_evaluate_node(self, answers))

    def variables(self) -> set[str]:
        return _variables(self)

    def validate(self, variables: Mapping[str, Any] | set[str]) -> None:
        known = set(variables.keys()) if isinstance(variables, Mapping) else set(variables)
        unknown = self.variables() - known
        if unknown:
            raise ValueError(
                f"Expression references unknown variables: {', '.join(sorted(unknown))}"
            )
        _validate_operator_tree(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "expression",
            "op": self.op,
            "left": _to_payload(self.left),
            "right": _to_payload(self.right),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Expression:
        if payload.get("type") != "expression":
            raise ValueError("Expression payload must contain type='expression'.")
        op = payload.get("op")
        if not isinstance(op, str):
            raise ValueError("Expression payload must contain a string operator.")
        return cls(op, _from_payload(payload.get("left")), _from_payload(payload.get("right")))

    @classmethod
    def raw(cls, text: str) -> Expression:
        return cls("raw", text)

    def to_surveyjs(self) -> str:
        if self.op == "raw":
            return str(self.left)
        if self.op == "not":
            return f"not ({_to_surveyjs_node(self.left)})"
        if self.op in {"and", "or"}:
            return f"({_to_surveyjs_node(self.left)}) {self.op} ({_to_surveyjs_node(self.right)})"
        if self.op in _COMPARISON_OPS:
            return f"{_to_surveyjs_node(self.left)} {self.op} {_literal(self.right)}"
        raise ValueError(f"Unsupported expression operator: {self.op}")


def _evaluate_node(node: Any, answers: dict[str, Any]) -> Any:
    if isinstance(node, VarRef):
        return node.evaluate(answers)
    if not isinstance(node, Expression):
        return node
    if node.op == "raw":
        raise ValueError(
            "Raw string expressions cannot be evaluated safely. Use structured expressions."
        )
    if node.op == "and":
        return _evaluate_node(node.left, answers) and _evaluate_node(node.right, answers)
    if node.op == "or":
        return _evaluate_node(node.left, answers) or _evaluate_node(node.right, answers)
    if node.op == "not":
        return not _evaluate_node(node.left, answers)

    left = _evaluate_node(node.left, answers)
    right = _evaluate_node(node.right, answers)
    if node.op == "=":
        return left == right
    if node.op == "!=":
        return left != right
    if node.op == ">":
        return left > right
    if node.op == ">=":
        return left >= right
    if node.op == "<":
        return left < right
    if node.op == "<=":
        return left <= right
    if node.op == "in":
        return left in right
    if node.op == "not in":
        return left not in right
    raise ValueError(f"Unsupported expression operator: {node.op}")


def _variables(node: Any) -> set[str]:
    if isinstance(node, VarRef):
        return node.variables()
    if isinstance(node, Expression):
        return _variables(node.left) | _variables(node.right)
    return set()


def _validate_operator_tree(node: Any) -> None:
    if isinstance(node, Expression):
        if node.op not in _SUPPORTED_OPS:
            raise ValueError(f"Unsupported expression operator: {node.op}")
        if node.op == "raw":
            raise ValueError(
                "Raw string expressions cannot be validated safely. Use structured expressions."
            )
        _validate_operator_tree(node.left)
        _validate_operator_tree(node.right)


def _to_payload(node: Any) -> Any:
    if isinstance(node, VarRef):
        return node.to_dict()
    if isinstance(node, Expression):
        return node.to_dict()
    if isinstance(node, list | tuple | set):
        return [_to_payload(item) for item in node]
    return node


def _from_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        payload_type = payload.get("type")
        if payload_type == "var":
            return VarRef.from_dict(payload)
        if payload_type == "expression":
            return Expression.from_dict(payload)
    return payload


def _to_surveyjs_node(node: Any) -> str:
    if isinstance(node, Expression):
        return node.to_surveyjs()
    return str(node)


def _literal(value: Any) -> str:
    if isinstance(value, str):
        escaped = value.replace("'", "\\'")
        return f"'{escaped}'"
    if value is None:
        return "null"
    if isinstance(value, set):
        return "[" + ", ".join(_literal(v) for v in sorted(value, key=repr)) + "]"
    if isinstance(value, list | tuple):
        return "[" + ", ".join(_literal(v) for v in value) + "]"
    return str(value)


def compare(var_name: str, op: str, value: Any) -> Expression:
    return Expression(op, VarRef(var_name), value)


def AND(*expressions: Expression) -> Expression:
    """Compose two or more expressions with logical AND."""

    if len(expressions) < 2:
        raise ValueError("AND requires at least two expressions.")
    result = expressions[0]
    for expr in expressions[1:]:
        result = Expression("and", result, expr)
    return result


def OR(*expressions: Expression) -> Expression:
    """Compose two or more expressions with logical OR."""

    if len(expressions) < 2:
        raise ValueError("OR requires at least two expressions.")
    result = expressions[0]
    for expr in expressions[1:]:
        result = Expression("or", result, expr)
    return result


def NOT(expression: Expression) -> Expression:
    """Negate an expression."""

    return Expression("not", expression)
