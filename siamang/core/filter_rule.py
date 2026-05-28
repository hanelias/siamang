"""Conditional logic primitives for questionnaire flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FilterRule:
    """Represents a visibility/branching predicate over a response dictionary."""

    predicate: Callable[[dict[str, Any]], bool]
    description: str | None = None

    def evaluate(self, answers: dict[str, Any]) -> bool:
        return bool(self.predicate(answers))
