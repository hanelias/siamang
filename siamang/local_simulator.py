"""Local synthetic response simulator for questionnaires."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

from siamang.core.expression import Expression
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
)


def _simulate_value(question: Question, var=None):
    """Simulate a single value for a question (or a specific variable within a Matrix)."""
    if isinstance(question, NumericInput):
        v = var or question.var
        if hasattr(v, "valid_range") and v.valid_range:
            lo, hi = v.valid_range
            return random.randint(int(lo), int(hi))
        return random.randint(18, 70)
    if isinstance(question, LikertScale):
        return random.randint(1, question.points)
    if isinstance(question, Matrix):
        # For Matrix, simulate based on the variable's labels (Likert-like)
        v = var or (question.var[0] if question.var else None)
        if v and v.labels:
            return random.choice(list(v.labels.keys()))
        return random.randint(1, 5)
    if isinstance(question, SingleChoice):
        codes = _choice_codes(question)
        if codes:
            return random.choice(codes)
        return 1
    if isinstance(question, MultiChoice) and question.mode == "array":
        return _simulate_array_multichoice(question)
    if isinstance(question, Ranking):
        codes = _choice_codes(question)
        if codes:
            max_ranked = question.max_ranked or len(codes)
            count = random.randint(1, min(max_ranked, len(codes)))
            return random.sample(codes, count)
        return [1]
    if isinstance(question, OpenText):
        return "sample text"
    return None


def _choice_codes(question: Question) -> list:
    """Return the option codes a respondent could choose, preferring the
    question's explicit ``choices`` list over the bound Variable.labels."""

    explicit = getattr(question, "choices", None)
    if explicit:
        return [opt.code for opt in explicit]
    labels = getattr(question.var, "labels", {})
    return list(labels.keys()) if labels else []


def _simulate_array_multichoice(question: MultiChoice) -> list:
    choices = _choice_codes(question) or [1]
    max_answers = min(question.max_answers or len(choices), len(choices))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = random.sample(choices, count) if count else []
    exclusive_selected = [value for value in selected if value in question.exclusive]
    if exclusive_selected:
        return [exclusive_selected[0]]
    return selected


def _simulate_wide_multichoice(question: MultiChoice) -> dict[str, int]:
    variables = question.var
    max_answers = min(question.max_answers or len(variables), len(variables))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = (
        set(random.sample([variable.name for variable in variables], count)) if count else set()
    )
    return {variable.name: int(variable.name in selected) for variable in variables}


def _evaluate_condition(condition: Any, answers: dict[str, Any]) -> bool:
    """Evaluate a show_if/hide_if condition against the current row answers.

    Returns True if the condition is met (i.e., the item should be shown).
    Returns True (show) if condition is None.
    """
    if condition is None:
        return True
    if isinstance(condition, Expression):
        try:
            return condition.evaluate(answers)
        except (TypeError, ValueError, KeyError):
            # If evaluation fails (e.g., missing variable), default to not showing
            return False
    # String expressions cannot be evaluated; default to showing
    return True


def _question_variable_names(question: Question) -> list[str]:
    """Get all variable names produced by a question."""
    if (
        isinstance(question, MultiChoice)
        and question.mode == "wide"
        or isinstance(question.var, list)
    ):
        return [v.name for v in question.var]
    else:
        return [question.var.name]


def _simulate_question_into_row(question: Question, row: dict[str, Any]) -> None:
    """Simulate a single question's value(s) and write into the row dict."""
    if isinstance(question, MultiChoice) and question.mode == "wide":
        row.update(_simulate_wide_multichoice(question))
    elif isinstance(question.var, list):
        for var in question.var:
            row[var.name] = _simulate_value(question, var=var)
    else:
        row[question.var.name] = _simulate_value(question)


def _set_question_missing(question: Question, row: dict[str, Any]) -> None:
    """Set all variables for a question to None (missing/NaN)."""
    if (
        isinstance(question, MultiChoice)
        and question.mode == "wide"
        or isinstance(question.var, list)
    ):
        for var in question.var:
            row[var.name] = None
    else:
        row[question.var.name] = None


def simulate_dataframe(
    questions: list[Question], n: int = 100, seed: int | None = 42
) -> pd.DataFrame:
    """Simulate responses without page-level visibility (legacy flat mode).

    This function is kept for backward compatibility. For page-aware simulation
    that respects show_if/hide_if on pages, use ``simulate_from_pages()``.
    """
    if seed is not None:
        random.seed(seed)
    rows = []
    for _ in range(n):
        row: dict[str, Any] = {}
        for q in questions:
            _simulate_question_into_row(q, row)
        rows.append(row)
    return pd.DataFrame(rows)


def simulate_from_pages(pages: list[Page], n: int = 100, seed: int | None = 42) -> pd.DataFrame:
    """Simulate responses respecting page-level and question-level show_if/hide_if.

    For each simulated respondent, pages are processed in order. A page's
    ``show_if`` expression is evaluated against the answers collected so far.
    If the page is not shown, all variables on that page are set to NaN.
    Similarly, individual question-level ``show_if``/``hide_if`` conditions
    are evaluated per-question.
    """
    if seed is not None:
        random.seed(seed)

    # Collect all variable names across all pages to ensure consistent columns
    all_var_names: list[str] = []
    for page in pages:
        for q in page.flatten_questions():
            all_var_names.extend(_question_variable_names(q))

    rows = []
    for _ in range(n):
        row: dict[str, Any] = {name: None for name in all_var_names}

        for page in pages:
            # Evaluate page-level show_if
            page_show = _evaluate_condition(page.show_if, row)
            page_hide = False
            if page.hide_if is not None:
                page_hide = _evaluate_condition(page.hide_if, row)

            page_visible = page_show and not page_hide

            for q in page.flatten_questions():
                if not page_visible:
                    # Page is hidden → all questions on it produce NaN
                    _set_question_missing(q, row)
                    continue

                # Evaluate question-level show_if/hide_if
                q_show = _evaluate_condition(q.show_if, row)
                q_hide = False
                if q.hide_if is not None:
                    q_hide = _evaluate_condition(q.hide_if, row)

                if q_show and not q_hide:
                    _simulate_question_into_row(q, row)
                else:
                    _set_question_missing(q, row)

        rows.append(row)

    return pd.DataFrame(rows)
