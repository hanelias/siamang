"""Compile a Questionnaire into the React-runtime payload (SURVEY + PAGES).

The output of :func:`compile_react_payload` is consumed by
``siamang/frontend/templates/react/app.jsx``. It is a JSON-serialisable dict
with two keys:

* ``SURVEY`` — study / branding metadata pulled from :class:`UIConfig` and
  the questionnaire title.
* ``PAGES`` — one entry per :class:`Page`, each carrying either ``items`` or
  ``blocks`` and (optionally) a compiled visibility condition.

This compiler reads directly from the live :class:`Questionnaire` objects;
unlike the SurveyJS-style serializer it preserves question-type-specific
fields (``display``, ``points``, ``leftLabel``, etc.) that the React
question components need.

Visibility conditions are compiled to JavaScript expression strings with
explicit dependency lists, so the browser runtime can use `new Function()`
once at load time instead of interpreting a JSON AST on every render.
"""

from __future__ import annotations

import re
from typing import Any

from siamang.core.block import Block
from siamang.core.expression import Expression, VarRef
from siamang.core.media import Media
from siamang.core.option import Option
from siamang.core.page import Page
from siamang.core.question import (
    LikertScale,
    Matrix,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
    question_output_name,
)
from siamang.core.questionnaire import Questionnaire
from siamang.frontend.theme.ui_config import UIConfig


def compile_react_payload(
    survey: Questionnaire,
    *,
    ui: UIConfig | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{"SURVEY": {...}, "PAGES": [...]}`` for the React runtime."""

    ui = ui or UIConfig()
    options = dict(options or {})
    pages_src = list(_pages_for_react(survey))

    survey_meta = {
        "title": survey.title,
        "language": options.get("language", "en"),
        "institution": ui.institution_name or "",
        "subtitle": ui.study_subtitle or options.get("description") or "",
        "logoUrl": ui.logo_url or "",
        "logoText": ui.effective_logo_text,
        "logoPosition": ui.logo_position,
        "showHeader": ui.show_title or bool(ui.institution_name) or bool(ui.logo_url),
        "showProgress": options.get("show_progress", True),
        "estimatedMinutes": ui.estimated_minutes,
        "ethics": ui.ethics_statement or "",
        "privacyUrl": ui.privacy_url or "",
        "contactEmail": ui.contact_email or "",
        "completedTitle": options.get("completion_title"),
        "completedBody": options.get("completion_text"),
        "nextButtonText": ui.next_button_text,
        "prevButtonText": ui.prev_button_text,
        "submitButtonText": ui.submit_button_text,
        "submittingText": ui.submitting_text,
        "requiredText": ui.required_text,
        "savingText": ui.saving_text,
        "selectPlaceholder": ui.select_placeholder,
        "ofText": ui.of_text,
        "selectedText": ui.selected_text,
        "resumeTitle": ui.resume_title,
        "resumeAction": ui.resume_action,
        "restartAction": ui.restart_action,
        "pageText": ui.page_text,
        "ofTotalText": ui.of_total_text,
        "retryTitle": ui.retry_title,
        "retryBody": ui.retry_body,
        "retryAction": ui.retry_action,
        "saveLocalAction": ui.save_local_action,
        "progressStyle": ui.progress_style,
        "defaultTheme": ui.default_theme,
        "redirectUrl": ui.redirect_url,
        "requireAccessCode": ui.require_access_code,
        "accessCodes": ui.access_codes,
        "accessTitle": ui.access_title,
        "accessBody": ui.access_body,
        "accessPlaceholder": ui.access_placeholder,
        "accessButton": ui.access_button,
        "enableAnalytics": ui.enable_analytics,
        "allowBack": ui.allow_back,
    }

    pages: list[dict[str, Any]] = []
    total = len(pages_src)
    for index, page in enumerate(pages_src):
        pages.append(_compile_page(page, index=index, total=total))

    # Serialize scripts
    scripts_list = []
    for script in getattr(survey, "scripts", []):
        scripts_list.append(script.to_dict())
    survey_meta["scripts"] = scripts_list

    if any(s.trigger == "onRandomize" for s in getattr(survey, "scripts", [])):
        survey_meta["hasRandomizeScripts"] = True

    return {"SURVEY": survey_meta, "PAGES": pages}


def _pages_for_react(survey: Questionnaire):
    """Yield Page-like objects to render. Wraps a flat `blocks` list if needed."""

    if survey.pages:
        yield from survey.pages
        return
    items = list(survey.blocks)
    if not items:
        yield Page(name="page1", items=[])
        return
    if all(isinstance(item, Block) for item in items):
        for index, block in enumerate(items, start=1):
            assert isinstance(block, Block)
            page_name = _slugify(block.title) if block.title else f"page{index}"
            yield Page(name=page_name, title=block.title, items=block.items)
        return
    yield Page(name="page1", items=items)


def _compile_page(page: Page, *, index: int, total: int) -> dict[str, Any]:
    section = f"Section {index} of {max(0, total - 1)}" if total > 1 and index > 0 else None
    if index == 0:
        section = "Welcome"
    if index == total - 1 and total > 1:
        section = "Final thoughts"

    payload: dict[str, Any] = {
        "name": page.name,
        "title": page.title or "",
        "section": section,
    }

    show_if = _compile_condition(page.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(page.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if

    has_block = any(isinstance(item, Block) for item in page.items)
    if has_block:
        blocks: list[dict[str, Any]] = []
        loose: list[Question] = []
        for item in page.items:
            if isinstance(item, Block):
                if loose:
                    blocks.append({"title": "", "items": [_compile_question(q) for q in loose]})
                    loose = []
                blocks.append(_compile_block(item))
            else:
                loose.append(item)
        if loose:
            blocks.append({"title": "", "items": [_compile_question(q) for q in loose]})
        payload["blocks"] = blocks
    else:
        payload["items"] = [_compile_question(q) for q in page.flatten_questions()]

    return payload


def _compile_block(block: Block) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": block.title or "",
        "items": [_compile_question(q) for q in block.flatten_questions()],
    }
    show_if = _compile_condition(block.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(block.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if
    return payload


def _compile_question(question: Question) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": question_output_name(question),
        "title": question.text,
        "required": bool(question.required),
    }
    if question.hint:
        base["description"] = question.hint
    if question.show_if is not None:
        condition = _compile_condition(question.show_if)
        if condition is not None:
            base["showIf"] = condition
    if question.hide_if is not None:
        condition = _compile_condition(question.hide_if)
        if condition is not None:
            base["hideIf"] = condition
    media = _serialise_media(question.media)
    if media is not None:
        base["media"] = media

    if isinstance(question, SingleChoice):
        kind = "dropdown" if question.display == "dropdown" else "single"
        payload = {
            **base,
            "kind": kind,
            "display": question.display,
            "options": _options_payload(question.var, question.choices),
        }
        if question.other_specify:
            payload["otherSpecify"] = True
            other_meta = question.metadata or {}
            if other_meta.get("other_label"):
                payload["otherLabel"] = other_meta["other_label"]
            if other_meta.get("other_placeholder"):
                payload["otherPlaceholder"] = other_meta["other_placeholder"]
        return payload
    if isinstance(question, MultiChoice):
        if question.mode == "wide":
            options = [{"code": v.name, "label": v.label or v.name} for v in question.var]
        else:
            options = _options_payload(question.var, question.choices)
        payload = {**base, "kind": "multi", "options": options}
        if question.min_answers > 0:
            payload["min"] = question.min_answers
        if question.max_answers is not None:
            payload["max"] = question.max_answers
        if question.other_specify:
            payload["otherSpecify"] = True
            other_meta = question.metadata or {}
            if other_meta.get("other_label"):
                payload["otherLabel"] = other_meta["other_label"]
            if other_meta.get("other_placeholder"):
                payload["otherPlaceholder"] = other_meta["other_placeholder"]
        return payload
    if isinstance(question, LikertScale):
        return {
            **base,
            "kind": "likert",
            "points": question.points,
            "leftLabel": question.left_label or "",
            "rightLabel": question.right_label or "",
            "naOption": question.na_option
            if isinstance(question.na_option, str)
            else ("Not applicable" if question.na_option else None),
        }
    if isinstance(question, NumericInput):
        payload = {**base, "kind": "numeric", "display": question.display}
        if question.unit:
            payload["unit"] = question.unit
        if question.step:
            payload["step"] = question.step
        valid_range = getattr(question.var, "valid_range", None)
        if valid_range:
            payload["min"], payload["max"] = valid_range
        return payload
    if isinstance(question, OpenText):
        return {
            **base,
            "kind": "text",
            "multiline": question.multiline,
            "maxChars": question.max_chars,
            "placeholder": question.placeholder or "",
        }
    if isinstance(question, Matrix):
        columns = question.column_labels or _columns_from_first_var(question.var)
        rows = [{"id": v.name, "label": v.label or v.name} for v in question.var]
        return {**base, "kind": "matrix", "columns": columns, "rows": rows}
    if isinstance(question, Ranking):
        payload = {
            **base,
            "kind": "ranking",
            "options": _options_payload(question.var, question.choices),
        }
        if question.max_ranked:
            payload["max"] = question.max_ranked
        return payload

    return {**base, "kind": "text", "multiline": False}


def _options_payload(var: Any, choices: list[Option] | None) -> list[dict[str, Any]]:
    if choices:
        return [_option_to_dict(opt) for opt in choices]
    variables = var if isinstance(var, list) else [var]
    primary = variables[0]
    labels = getattr(primary, "labels", {}) or {}
    return [{"code": code, "label": label} for code, label in labels.items()]


def _option_to_dict(opt: Option) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": opt.code, "label": opt.label}
    show_if = _compile_condition(opt.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(opt.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if
    if opt.media is not None:
        payload["media"] = opt.media.to_dict()
    return payload


def _serialise_media(media: Media | list[Media] | None) -> list[dict[str, Any]] | None:
    if media is None:
        return None
    items = media if isinstance(media, list) else [media]
    return [item.to_dict() for item in items]


def _columns_from_first_var(variables: list[Any]) -> list[str]:
    if not variables:
        return []
    labels = getattr(variables[0], "labels", {}) or {}
    return [label for _, label in sorted(labels.items())]


# ─── Expression → JS compilation ─────────────────────────────────────────────


def _compile_condition(condition: Any) -> dict[str, Any] | None:
    """Compile a visibility condition into a { deps, fn } payload.

    The browser runtime uses ``new Function("a", "return " + fn)`` once at
    load time. ``deps`` lists the variable names the expression references,
    enabling fine-grained store subscriptions.

    Falls back to the legacy AST format for ``raw`` string expressions that
    cannot be safely compiled.
    """
    if condition is None:
        return None
    if isinstance(condition, (Expression, VarRef)):
        deps = sorted(condition.variables())
        js_body = _expr_to_js(condition)
        if js_body is not None:
            return {"deps": deps, "fn": js_body}
        # Fallback: raw expression that can't be compiled → legacy AST
        return condition.to_dict()
    if isinstance(condition, str):
        # Raw string condition — cannot compile safely
        return condition
    return None


def _expr_to_js(node: Any) -> str | None:
    """Recursively compile an Expression/VarRef tree to a JS expression string.

    Returns None if the expression contains a ``raw`` operator that cannot
    be safely translated.
    """
    if isinstance(node, VarRef):
        return f"a[{_js_string(node.name)}]"

    if isinstance(node, Expression):
        if node.op == "raw":
            return None  # Cannot compile raw strings

        if node.op == "not":
            left_js = _expr_to_js(node.left)
            if left_js is None:
                return None
            return f"!({left_js})"

        if node.op == "and":
            left_js = _expr_to_js(node.left)
            right_js = _expr_to_js(node.right)
            if left_js is None or right_js is None:
                return None
            return f"(({left_js})&&({right_js}))"

        if node.op == "or":
            left_js = _expr_to_js(node.left)
            right_js = _expr_to_js(node.right)
            if left_js is None or right_js is None:
                return None
            return f"(({left_js})||({right_js}))"

        # Comparison operators
        left_js = _expr_to_js(node.left)
        right_js = _value_to_js(node.right)
        if left_js is None or right_js is None:
            return None

        op_map = {
            "=": "===",
            "==": "===",
            "eq": "===",
            "!=": "!==",
            "ne": "!==",
            ">": ">",
            "gt": ">",
            ">=": ">=",
            "ge": ">=",
            "<": "<",
            "lt": "<",
            "<=": "<=",
            "le": "<=",
        }

        if node.op in op_map:
            js_op = op_map[node.op]
            return f"({left_js}{js_op}{right_js})"

        if node.op == "in":
            return f"(Array.isArray({right_js})&&{right_js}.includes({left_js}))"

        if node.op in ("not in", "notin"):
            return f"(!Array.isArray({right_js})||!{right_js}.includes({left_js}))"

        return None  # Unknown operator

    # Literal value (shouldn't appear as top-level condition, but handle gracefully)
    return _value_to_js(node)


def _value_to_js(value: Any) -> str | None:
    """Convert a Python literal to a JS literal string."""
    if isinstance(value, VarRef):
        return f"a[{_js_string(value.name)}]"
    if isinstance(value, Expression):
        return _expr_to_js(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return _js_string(value)
    if isinstance(value, list | tuple | set):
        items = [_value_to_js(v) for v in value]
        if any(i is None for i in items):
            return None
        return "[" + ",".join(items) + "]"
    return repr(value)


def _js_string(s: str) -> str:
    """Safely quote a string for JS (JSON-compatible quoting)."""
    import json

    return json.dumps(s, ensure_ascii=False)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    return slug or "page"
