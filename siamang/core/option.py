"""Per-choice answer option with visibility and media."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from siamang.core.expression import Expression
from siamang.core.media import Media


@dataclass(frozen=True, slots=True)
class Option:
    """A single answer option attached to a choice question.

    Use this when an option needs more than a plain ``{code: label}`` mapping —
    namely conditional visibility (``show_if`` / ``hide_if``) or an attached
    image/video/audio.

    ``code`` must match the type used in :attr:`Variable.labels`.
    ``label`` overrides whatever label is registered on the bound variable
    (so options can be reused across variables with different label sets).
    """

    code: Any
    label: str
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    media: Media | None = None

    def __post_init__(self) -> None:
        if not self.label or not str(self.label).strip():
            raise ValueError("Option.label must not be empty.")
        for field_name in ("show_if", "hide_if"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, (Expression, str)):
                raise TypeError(
                    f"Option.{field_name} must be Expression or str, got {type(value).__name__}."
                )
        if self.media is not None and not isinstance(self.media, Media):
            raise TypeError("Option.media must be a Media instance.")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "label": self.label}
        if self.show_if is not None:
            payload["show_if"] = _serialise_condition(self.show_if)
        if self.hide_if is not None:
            payload["hide_if"] = _serialise_condition(self.hide_if)
        if self.media is not None:
            payload["media"] = self.media.to_dict()
        return payload


def _serialise_condition(value: Expression | str) -> Any:
    if isinstance(value, Expression):
        return value.to_dict()
    return value
