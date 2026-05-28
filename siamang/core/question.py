"""Question abstractions and concrete question types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from siamang.core.media import Media
from siamang.core.option import Option
from siamang.core.variable import Variable


@dataclass(frozen=True, slots=True)
class Question:
    """Base question binding a prompt to one variable (or many for matrix)."""

    text: str
    var: Variable | list[Variable]
    required: bool = False
    hint: str | None = None
    show_if: Any = None
    hide_if: Any = None
    skip_to: str | None = None
    randomize: bool = False
    other_specify: bool = False
    tag: str | list[str] | None = None
    id: str | None = None
    name: str | None = None
    media: Media | list[Media] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Question text must not be empty.")
        if self.id is not None and not self.id.strip():
            raise ValueError("Question id must not be empty when provided.")
        if self.name is not None and not self.name.strip():
            raise ValueError("Question name must not be empty when provided.")
        if self.media is not None:
            items = self.media if isinstance(self.media, list) else [self.media]
            for item in items:
                if not isinstance(item, Media):
                    raise TypeError("Question.media must be Media or list[Media].")


@dataclass(frozen=True, slots=True)
class SingleChoice(Question):
    display: str = "radio"
    none_of_above: bool = False
    choices: list[Option] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if self.display not in {"radio", "dropdown", "buttons"}:
            raise ValueError("display must be one of: radio, dropdown, buttons")
        if not isinstance(self.var, Variable):
            raise TypeError("SingleChoice expects var to be a Variable.")
        _validate_choices(self.choices)


@dataclass(frozen=True, slots=True, init=False)
class MultiChoice(Question):
    min_answers: int = 1
    max_answers: int | None = None
    exclusive: list[int] = field(default_factory=list)
    mode: str = "array"
    choices: list[Option] | None = None

    def __init__(
        self,
        text: str,
        var: Variable | list[Variable] | None = None,
        *,
        vars: list[Variable] | None = None,
        required: bool = False,
        hint: str | None = None,
        show_if: Any = None,
        hide_if: Any = None,
        skip_to: str | None = None,
        randomize: bool = False,
        other_specify: bool = False,
        tag: str | list[str] | None = None,
        id: str | None = None,
        name: str | None = None,
        media: Media | list[Media] | None = None,
        metadata: dict[str, Any] | None = None,
        min_answers: int = 1,
        max_answers: int | None = None,
        exclusive: list[int] | None = None,
        mode: str = "array",
        choices: list[Option] | None = None,
    ) -> None:
        if vars is not None:
            if var is not None:
                raise ValueError("Use either 'var' or 'vars' for MultiChoice, not both.")
            var = vars
            mode = "wide"
        if var is None:
            raise TypeError("MultiChoice requires 'var' for array mode or 'vars' for wide mode.")
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "var", var)
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "hint", hint)
        object.__setattr__(self, "show_if", show_if)
        object.__setattr__(self, "hide_if", hide_if)
        object.__setattr__(self, "skip_to", skip_to)
        object.__setattr__(self, "randomize", randomize)
        object.__setattr__(self, "other_specify", other_specify)
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "media", media)
        object.__setattr__(self, "metadata", dict(metadata or {}))
        object.__setattr__(self, "min_answers", min_answers)
        object.__setattr__(self, "max_answers", max_answers)
        object.__setattr__(self, "exclusive", list(exclusive or []))
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "choices", list(choices) if choices is not None else None)
        self.__post_init__()

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if self.mode not in {"array", "wide"}:
            raise ValueError("MultiChoice mode must be either 'array' or 'wide'.")
        if self.mode == "array" and not isinstance(self.var, Variable):
            raise TypeError("MultiChoice array mode expects var to be a Variable.")
        if self.mode == "wide" and (not isinstance(self.var, list) or not self.var):
            raise TypeError(
                "MultiChoice wide mode expects vars to be a non-empty list of Variables."
            )
        if self.mode == "wide" and self.var and any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("MultiChoice wide mode vars must contain only Variable instances.")
        if self.min_answers < 0:
            raise ValueError("min_answers must be >= 0")
        if self.max_answers is not None and self.max_answers < self.min_answers:
            raise ValueError("max_answers must be >= min_answers")
        if (
            self.mode == "wide"
            and self.max_answers is not None
            and self.max_answers > len(self.var)
        ):
            raise ValueError("max_answers cannot exceed number of wide-mode variables")
        _validate_choices(self.choices)


@dataclass(frozen=True, slots=True)
class LikertScale(Question):
    points: int = 5
    left_label: str | None = None
    right_label: str | None = None
    na_option: bool | str = False

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("LikertScale expects var to be a Variable.")
        if self.points < 2:
            raise ValueError("points must be >= 2")


@dataclass(frozen=True, slots=True)
class NumericInput(Question):
    display: str = "input"
    unit: str | None = None
    step: int | float = 1

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("NumericInput expects var to be a Variable.")
        if self.display not in {"input", "slider"}:
            raise ValueError("display must be one of: input, slider")
        if self.step <= 0:
            raise ValueError("step must be > 0")


@dataclass(frozen=True, slots=True)
class OpenText(Question):
    multiline: bool = False
    max_chars: int | None = None
    placeholder: str | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("OpenText expects var to be a Variable.")
        if self.max_chars is not None and self.max_chars <= 0:
            raise ValueError("max_chars must be > 0")


@dataclass(frozen=True, slots=True)
class Matrix(Question):
    var: list[Variable]
    subquestions: list[str] | None = None
    column_labels: list[str] | None = None
    na_option: bool | str = False

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not self.var:
            raise ValueError("Matrix requires at least one variable")
        if any(not isinstance(v, Variable) for v in self.var):
            raise TypeError("Matrix var must contain only Variable instances")


@dataclass(frozen=True, slots=True)
class Ranking(Question):
    max_ranked: int | None = None
    choices: list[Option] | None = None

    def __post_init__(self) -> None:
        Question.__post_init__(self)
        if not isinstance(self.var, Variable):
            raise TypeError("Ranking expects var to be a Variable.")
        if self.max_ranked is not None and self.max_ranked <= 0:
            raise ValueError("max_ranked must be > 0")
        _validate_choices(self.choices)


def _validate_choices(choices: list[Option] | None) -> None:
    if choices is None:
        return
    if not isinstance(choices, list):
        raise TypeError("choices must be a list of Option instances.")
    if not choices:
        raise ValueError("choices must not be an empty list.")
    seen: set[Any] = set()
    for choice in choices:
        if not isinstance(choice, Option):
            raise TypeError("All entries in choices must be Option instances.")
        if choice.code in seen:
            raise ValueError(f"Duplicate option code in choices: {choice.code!r}.")
        seen.add(choice.code)


def question_variable_names(question: Question) -> list[str]:
    variables = question.var if isinstance(question.var, list) else [question.var]
    return [variable.name for variable in variables]


def question_fallback_id(question: Question) -> str:
    if question.id is not None:
        return question.id
    if question.name is not None:
        return question.name
    if isinstance(question, Matrix):
        return "matrix_" + question.var[0].name
    if isinstance(question, MultiChoice) and question.mode == "wide":
        return "multi_" + question.var[0].name
    return question_variable_names(question)[0]


def question_output_name(question: Question) -> str:
    return question.name or question_fallback_id(question)
