"""Script — injectable JavaScript behavior for surveys.

Scripts allow researchers to add custom dynamic behavior without modifying
the core runtime. Examples:
- Randomize answer options based on previous answers
- Shuffle page order
- Show timed questions
- Custom validation (e.g., password confirmation)
- External API calls (e.g., verify postal code)
- A/B test assignment
- Dynamic piped text
- Custom event tracking

Each script runs at a specified trigger point and has access to:
- answers: current respondent answers
- utils: built-in helper functions (shuffle, sample, etc.)
- api: { get, post } for external HTTP calls
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_VALID_TRIGGERS = {
    "onInit",  # Runs once when survey loads (before first page)
    "onPageEnter",  # Runs when a page becomes visible
    "onPageExit",  # Runs when leaving a page
    "onQuestionShow",  # Runs when a question becomes visible (show_if resolved)
    "onAnswer",  # Runs when any answer changes
    "onSubmit",  # Runs before submission (can modify answers)
    "onRandomize",  # Runs to determine randomization
}


@dataclass(frozen=True, slots=True)
class Script:
    """A JavaScript snippet that runs at a specific trigger point.

    Args:
        code: JavaScript source code (string)
        trigger: When to run. One of: onInit, onPageEnter, onPageExit,
                onQuestionShow, onAnswer, onSubmit, onRandomize
        name: Optional identifier (shown in logs, useful for debugging)
        target: Optional scope — page name or question ID to limit scope.
                If None, runs globally at the trigger point.
        context: Optional dict of static data passed to the script at runtime
        sandbox: If True, run in a restricted scope (no DOM access)

    Example:
        Script(
            name="shuffle_options",
            trigger="onRandomize",
            target="q_trust",
            code=\"\"\"
                // Randomize question options on every show
                answers.__options__['q_trust'] = utils.shuffle(
                    answers.__options__['q_trust']
                );
            \"\"\"
        )
    """

    code: str
    trigger: str = "onPageEnter"
    name: str | None = None
    target: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    sandbox: bool = True

    def __post_init__(self) -> None:
        if self.trigger not in _VALID_TRIGGERS:
            allowed = ", ".join(sorted(_VALID_TRIGGERS))
            raise ValueError(f"Unknown trigger '{self.trigger}'. Allowed triggers: {allowed}.")
        if not self.code.strip():
            raise ValueError("Script code must not be empty.")
        if self.name is not None and not self.name.strip():
            raise ValueError("Script name must not be empty when provided.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "trigger": self.trigger,
            "name": self.name,
            "target": self.target,
            "context": self.context,
            "sandbox": self.sandbox,
        }

    @classmethod
    def randomize_options(cls, question_id: str, seed: str | None = None) -> Script:
        """Factory: create a script that randomizes answer options for a question."""
        qid = json.dumps(question_id)
        code = f"""
            const qid = {qid};
            const opts = answers.__options__?.[qid];
            if (opts && Array.isArray(opts)) {{
                answers.__options__[qid] = utils.shuffle(opts);
            }}
        """
        return cls(
            name=f"randomize_{question_id}",
            trigger="onQuestionShow",
            target=question_id,
            code=code,
            context={"seed": seed} if seed else {},
        )

    @classmethod
    def randomize_pages(cls) -> Script:
        """Factory: shuffle all visible page order on init."""
        code = """
            // Shuffle all visible pages except the first (welcome) and last
            const pages = answers.__pages__ || [];
            if (pages.length > 3) {
                const first = pages[0];
                const last = pages[pages.length - 1];
                const middle = pages.slice(1, -1);
                const shuffled = utils.shuffle(middle);
                answers.__pages__ = [first, ...shuffled, last];
            }
        """
        return cls(
            name="randomize_pages",
            trigger="onInit",
            code=code,
        )

    @classmethod
    def validate_fields_match(
        cls, field_a: str, field_b: str, message: str = "Fields do not match."
    ) -> Script:
        """Factory: validate that two answer fields have the same value."""
        fa = json.dumps(field_a)
        fb = json.dumps(field_b)
        msg = json.dumps(message)
        code = f"""
            const fa = {fa};
            const fb = {fb};
            if (answers[fa] !== undefined &&
                answers[fb] !== undefined &&
                answers[fa] !== answers[fb]) {{
                answers.__errors__[fb] = {msg};
            }}
        """
        return cls(
            name=f"validate_match_{field_a}_{field_b}",
            trigger="onAnswer",
            target=field_b,
            code=code,
        )

    @classmethod
    def timed_question(cls, question_id: str, seconds: int = 30) -> Script:
        """Factory: show a question for limited time, then auto-advance."""
        qid = json.dumps(question_id)
        timeout_ms = seconds * 1000
        code = f"""
            const qid = {qid};
            const timeout = {timeout_ms};
            if (!answers.__timers__) answers.__timers__ = {{}};
            if (!answers.__timers__[qid]) {{
                answers.__timers__[qid] = setTimeout(() => {{
                    if (window.siamangNext) window.siamangNext();
                }}, timeout);
            }}
        """
        return cls(
            name=f"timed_{question_id}",
            trigger="onQuestionShow",
            target=question_id,
            code=code,
        )
