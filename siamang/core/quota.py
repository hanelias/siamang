"""Quota control primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Quota:
    variable: str
    target_value: Any
    limit: int

    def reached(self, answers: list[dict[str, Any]]) -> bool:
        matched = sum(1 for row in answers if row.get(self.variable) == self.target_value)
        return matched >= self.limit
