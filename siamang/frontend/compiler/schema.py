"""Compile a Questionnaire (and its UIConfig) into a SurveySchema IR."""

from __future__ import annotations

import re
from typing import Any

from siamang.core.block import Block
from siamang.core.page import Page
from siamang.core.question import Question
from siamang.core.questionnaire import Questionnaire
from siamang.core.serialization import question_to_dict
from siamang.core.variable import VariableMap
from siamang.frontend.compiler.logic import compile_expression
from siamang.frontend.compiler.quota import compile_quota
from siamang.frontend.schema import SurveySchema


def compile_questionnaire(
    survey: Questionnaire,
    *,
    options: dict[str, Any] | None = None,
) -> SurveySchema:
    """Convert a `Questionnaire` into a renderable `SurveySchema` (IR).

    ``options`` carries questionnaire-level frontend settings normally provided
    through ``Questionnaire`` (language, description, completion_text,
    show_progress, allow_back, one_question_per_page, max_responses, quotas).
    Plumbed via a separate dict so the core dataclass stays minimal — the
    builder forwards it from ``Questionnaire`` extras.
    """

    opts = dict(options or {})
    pages = _compile_pages(survey)
    variable_map = survey.variables or _autobuild_variable_map(survey)

    return SurveySchema(
        title=survey.title,
        pages=pages,
        variables=variable_map.to_dict()
        if hasattr(variable_map, "to_dict")
        else dict(variable_map),
        language=opts.get("language", "en"),
        description=opts.get("description"),
        completion_text=opts.get("completion_text", "Thank you for your participation!"),
        show_progress=opts.get("show_progress", True),
        allow_back=opts.get("allow_back", True),
        one_question_per_page=opts.get("one_question_per_page", False),
        deadline=survey.deadline,
        max_responses=opts.get("max_responses"),
        quotas=[compile_quota(q) for q in opts.get("quota", [])],
        metadata=opts.get("metadata", {}),
    )


def _compile_pages(survey: Questionnaire) -> list[dict[str, Any]]:
    if survey.pages:
        return [_compile_page(page) for page in survey.pages]
    if survey.blocks and all(isinstance(item, Block) for item in survey.blocks):
        pages = []
        for index, block in enumerate(survey.blocks, start=1):
            assert isinstance(block, Block)
            page_name = _slugify(block.title) if block.title else f"page{index}"
            page = Page(name=page_name, title=block.title, items=block.items)
            pages.append(_compile_page(page))
        return pages
    elements = [_compile_question(q) for q in survey.all_questions()]
    return [{"name": "page1", "elements": elements}]


def _compile_page(page: Page) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": page.name,
        "title": page.title,
        "elements": [_compile_question(question) for question in page.flatten_questions()],
    }
    if page.randomize_blocks:
        payload["randomizeBlocks"] = True
    visible_if = compile_expression(page.show_if)
    if visible_if is not None:
        payload["visibleIf"] = visible_if
    hide_if = compile_expression(page.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if
    return payload


def _compile_question(question: Question) -> dict[str, Any]:
    payload = question_to_dict(question)
    show_if = compile_expression(getattr(question, "show_if", None))
    if show_if:
        payload["visibleIf"] = show_if
    hide_if = compile_expression(getattr(question, "hide_if", None))
    if hide_if:
        payload["hideIf"] = hide_if
    return payload


def _autobuild_variable_map(survey: Questionnaire) -> VariableMap:
    """Build a VariableMap from question variables when none was provided."""

    variable_map = VariableMap()
    for question in survey.all_questions():
        variables = question.var if isinstance(question.var, list) else [question.var]
        for variable in variables:
            if variable.name not in variable_map:
                variable_map.add(variable)
    return variable_map


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    return slug or "page"
