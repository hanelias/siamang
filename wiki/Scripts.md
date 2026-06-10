# Scripts

A `Script` injects a custom JavaScript snippet that runs in the respondent's browser
at a chosen lifecycle trigger. Scripts cover behaviour the declarative model does not:
option/page randomization, cross-field validation, timed questions, external API
calls, A/B assignment, piped text, and custom event tracking — all without modifying
the core runtime.

```python
from siamang.core import Script
# or: import siamang as sg  →  sg.Script
```

## `Script`

```python
@dataclass(frozen=True, slots=True)
class Script:
    code: str
    trigger: str = "onPageEnter"
    name: str | None = None
    target: str | None = None
    context: dict[str, Any] = {}
    sandbox: bool = True
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `code` | `str` | *required* | JavaScript source. Must be non-empty. |
| `trigger` | `str` | `"onPageEnter"` | Lifecycle event that runs the script (see below). |
| `name` | `str \| None` | `None` | Optional identifier shown in logs; useful for debugging. |
| `target` | `str \| None` | `None` | Scope to a page name or question id; `None` runs globally at the trigger. |
| `context` | `dict[str, Any]` | `{}` | Static data passed into the script at runtime. |
| `sandbox` | `bool` | `True` | Run in a restricted scope (no DOM access). |

Construction validates the trigger (unknown triggers raise `ValueError`), requires
non-empty `code`, and rejects an empty `name`. `to_dict()` serializes the script for
the frontend bundle.

Scripts are attached to a survey through `Questionnaire(scripts=[...])`.
`Questionnaire.validate()` checks that every script has a known trigger and that a
non-`None` `target` matches an existing question id or page name.

## Trigger points

| Trigger | When it runs |
| :--- | :--- |
| `onInit` | Once when the survey loads, before the first page. |
| `onPageEnter` | A page becomes visible. |
| `onPageExit` | A page is left. |
| `onQuestionShow` | A question becomes visible (its `show_if` resolved). |
| `onAnswer` | Any answer changes. |
| `onSubmit` | Before submission — can modify answers. |
| `onRandomize` | Randomization is requested. |

## The JavaScript runtime context

Inside a snippet you have these globals:

- **`answers`** — the current respondent answers (read/write). Special keys the
  runtime understands include `answers.__options__[qid]` (per-question option order),
  `answers.__pages__` (page order), `answers.__errors__[field]` (validation messages),
  and `answers.__timers__` (timer handles).
- **`utils`** — helper functions: `shuffle`, `sample`, `clamp`, `debounce`, `now`,
  `formatDate`.
- **`api`** — `{ get, post }` for external HTTP calls.
- **`context`** — exactly the static `context` dict you passed on the `Script`;
  the runtime injects nothing else into it.

```python
import siamang as sg

custom = sg.Script(
    name="log_exit",
    trigger="onPageExit",
    context={"endpoint": "/diagnostics"},
    code="""
        api.post(context.endpoint, { left_at: utils.now() });
    """,
)
```

## Factory classmethods

Four classmethods build ready-made scripts for the most common patterns. Each returns
a fully-configured `Script` (trigger, target, and name preset).

### `Script.randomize_options(question_id, seed=None)`

Shuffle a question's answer options when it is shown (`trigger="onQuestionShow"`,
scoped to `question_id`). An optional `seed` is stored in `context`.

```python
shuffle_party = sg.Script.randomize_options("q_party")
```

### `Script.randomize_pages()`

Shuffle visible page order on `onInit`, keeping the first (welcome) and last page
fixed. Runs globally.

```python
shuffle_pages = sg.Script.randomize_pages()
```

### `Script.validate_fields_match(field_a, field_b, message="Fields do not match.")`

Validate that two answer fields hold the same value (e.g. email confirmation). Runs on
`onAnswer`, scoped to `field_b`, and writes `message` to `answers.__errors__[field_b]`
on mismatch.

```python
match_emails = sg.Script.validate_fields_match(
    "email_1", "email_2", message="Emails don't match.",
)
```

### `Script.timed_question(question_id, seconds=30)`

Show a question for a limited time, then auto-advance. Runs on `onQuestionShow`, scoped
to `question_id`, and sets a timer that calls the runtime's next-page hook after
`seconds`.

```python
timer = sg.Script.timed_question("q_party", seconds=30)
```

## Attaching scripts to a survey

Pass scripts to the questionnaire's `scripts=` list. `target` values must resolve to
real question ids or page names.

```python
import siamang as sg

shuffle_party = sg.Script.randomize_options("q_party")
timer         = sg.Script.timed_question("q_party", seconds=30)
match_emails  = sg.Script.validate_fields_match(
    "email_1", "email_2", message="Emails don't match.",
)
custom = sg.Script(
    name="log_exit",
    trigger="onPageExit",
    context={"endpoint": "/diagnostics"},
    code="""
        api.post(context.endpoint, { left_at: utils.now() });
    """,
)

survey = sg.Questionnaire(
    title="Political Trust — 2026",
    pages=[...],
    scripts=[shuffle_party, timer, match_emails, custom],
)

survey.validate()      # rejects unknown triggers or targets that don't exist
```

## See also

- [[Visibility and Branching|Visibility-and-Branching]] — declarative logic that runs before reaching for a script.
- [[Question Types|Question-Types]] — the question ids scripts target.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — page names scripts target, and the `scripts=` field.
- [[Frontend and Theming|Frontend-and-Theming]] — how scripts run inside the runtime.
