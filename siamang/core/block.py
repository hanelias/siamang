"""Survey block for grouping questions and nested blocks."""

from __future__ import annotations

from dataclasses import dataclass, field

from siamang.core.expression import Expression
from siamang.core.question import Question


@dataclass(frozen=True, slots=True)
class Block:
    title: str | None = None
    items: list[Question | Block] = field(default_factory=list)
    randomize: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None

    def flatten_questions(self) -> list[Question]:
        flat: list[Question] = []
        for item in self.items:
            if isinstance(item, Block):
                flat.extend(item.flatten_questions())
            else:
                flat.append(item)
        return flat
