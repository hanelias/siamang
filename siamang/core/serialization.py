"""Serialization helpers for rendering questionnaire schemas."""

from __future__ import annotations

from siamang.core.question import (
    LikertScale,
    Matrix,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
    question_fallback_id,
    question_output_name,
)


def question_to_dict(question: Question) -> dict:
    base = {
        "id": question_fallback_id(question),
        "name": question_output_name(question),
        "title": question.text,
        "isRequired": question.required,
    }
    if question.metadata:
        base["metadata"] = dict(question.metadata)
    if question.media is not None:
        items = question.media if isinstance(question.media, list) else [question.media]
        base["media"] = [item.to_dict() for item in items]
    if isinstance(question, SingleChoice):
        return {**base, "type": "radiogroup", "choices": _choices(question)}
    if isinstance(question, MultiChoice):
        payload = {
            **base,
            "type": "checkbox",
            "choices": _choices(question),
            "multiChoiceMode": question.mode,
        }
        if question.mode == "wide":
            payload["variables"] = [v.name for v in question.var]
        return payload
    if isinstance(question, LikertScale):
        return {
            **base,
            "type": "rating",
            "rateMax": question.points,
            "rateMin": 1,
        }
    if isinstance(question, NumericInput):
        return {**base, "type": "text", "inputType": "number"}
    if isinstance(question, OpenText):
        return {**base, "type": "comment" if question.multiline else "text"}
    if isinstance(question, Matrix):
        columns = [{"value": k, "text": v} for k, v in (question.var[0].labels or {}).items()]
        rows = [{"value": v.name, "text": v.label or v.name} for v in question.var]
        return {**base, "type": "matrix", "columns": columns, "rows": rows}
    if isinstance(question, Ranking):
        return {**base, "type": "ranking", "choices": _choices(question)}
    return {**base, "type": "text"}


def _choices(question: Question) -> list[dict]:
    if isinstance(question, MultiChoice) and question.mode == "wide":
        return [
            {"value": variable.name, "text": variable.label or variable.name}
            for variable in question.var
        ]
    choices = getattr(question, "choices", None)
    if choices:
        return [_option_to_choice(opt) for opt in choices]
    var = question.var if not isinstance(question.var, list) else question.var[0]
    return [{"value": code, "text": label} for code, label in var.labels.items()]


def _option_to_choice(opt) -> dict:
    payload: dict = {"value": opt.code, "text": opt.label}
    if opt.show_if is not None:
        payload["visibleIf"] = _condition_to_payload(opt.show_if)
    if opt.hide_if is not None:
        payload["hideIf"] = _condition_to_payload(opt.hide_if)
    if opt.media is not None:
        payload["media"] = opt.media.to_dict()
    return payload


def _condition_to_payload(value):
    from siamang.core.expression import Expression

    if isinstance(value, Expression):
        return value.to_dict()
    return value
