# Pages, Blocks, and Structure

Surveys are organized into **pages** (screens shown to the respondent) and **blocks**
(logical groups of items within a page). A `Questionnaire` is the aggregate root that
ties pages, variables, and scripts together. This page covers `Page` and its special
*kinds*, the factory helpers, `Block`, and assembling a `Questionnaire`.

```python
from siamang.core import (
    Page, Block, Questionnaire,
    ContentPage, DisqualificationPage, FinalPage, RedirectPage,
)
```

## `Page`

A `Page` is one screen. It holds questions and blocks, page-level routing, a
visibility gate, and an optional `kind` that changes how the runtime renders it.

```python
@dataclass(frozen=True, slots=True)
class Page:
    name: str
    title: str | None = None
    items: list[Question | Block] = []
    next_if: list[tuple[str, str]] = []
    default_next: str | None = None
    randomize_blocks: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    kind: str | None = None
    body: str | None = None
    redirect_url: str | None = None
    redirect_delay: int | None = None
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | *required* | Unique page identifier; used as a branching/skip target. |
| `title` | `str \| None` | `None` | Title shown at the top of the page. |
| `items` | `list[Question \| Block]` | `[]` | Questions and blocks rendered on the page. |
| `next_if` | `list[tuple[str, str]]` | `[]` | Conditional routing: `[(condition, target_page_name), ...]`, evaluated in order. |
| `default_next` | `str \| None` | `None` | Fallback next page when no `next_if` matches. |
| `randomize_blocks` | `bool` | `False` | Shuffle the order of immediate `Block` items. |
| `show_if` | `Expression \| str \| None` | `None` | Render the page only when this is true. |
| `hide_if` | `Expression \| str \| None` | `None` | Hide the page when this is true. |
| `kind` | `str \| None` | `None` | Page kind (see below); `None` is an ordinary question page. |
| `body` | `str \| None` | `None` | HTML body for content/terminal pages. |
| `redirect_url` | `str \| None` | `None` | Target URL for terminal pages that redirect. |
| `redirect_delay` | `int \| None` | `None` | Seconds before redirecting (runtime default 5). |

### Properties and methods

- **`is_terminal -> bool`** — `True` for kinds that end the survey (`disqualification`, `final`, `redirect`).
- **`flatten_questions() -> list[Question]`** — all questions on the page, recursing into nested blocks.

### Page kinds

The `kind` field selects a rendering mode. Constructing a `Page` with an unknown kind
raises `ValueError`.

| `kind` | Terminal? | Behavior |
| :--- | :--- | :--- |
| `None` | no | Ordinary question page (the default). |
| `"content"` | no | Renders arbitrary HTML (`body`) instead of questions — intro/consent/etc. Stays in the normal Next/Prev flow. |
| `"disqualification"` | yes | Terminal screen-out; records the response as screened-out. |
| `"final"` | yes | Terminal custom thank-you screen (`body`). |
| `"redirect"` | yes | Terminal screen that redirects to `redirect_url` (e.g. a panel completion URL). |

Terminal pages end the survey when reached — typically gated by `show_if`. Content
pages remain navigable.

## Page factory helpers

Rather than setting `kind`/`body`/`redirect_url` by hand, use the factories. Each
returns a `Page` with the appropriate `kind` preset; keyword-only arguments keep call
sites explicit.

> **Note.** The page factories live in `siamang.core` — they are *not* re-exported
> from the top-level `siamang` namespace, so import them explicitly.

```python
def ContentPage(name, *, body, title=None, show_if=None, hide_if=None) -> Page
def DisqualificationPage(name, *, title=None, body=None, redirect_url=None,
                         redirect_delay=None, show_if=None, hide_if=None) -> Page
def FinalPage(name, *, title=None, body=None, redirect_url=None,
              redirect_delay=None, show_if=None) -> Page
def RedirectPage(name, *, redirect_url, title=None, body=None,
                 redirect_delay=None, show_if=None) -> Page
```

| Factory | `kind` | Required keyword |
| :--- | :--- | :--- |
| `ContentPage` | `"content"` | `body` |
| `DisqualificationPage` | `"disqualification"` | — |
| `FinalPage` | `"final"` | — |
| `RedirectPage` | `"redirect"` | `redirect_url` |

```python
from siamang.core import ContentPage, DisqualificationPage, FinalPage, RedirectPage

intro = ContentPage("intro", body="<p>Welcome to the study.</p>")

dq = DisqualificationPage(
    "dq", title="Sorry", body="<p>You are not eligible.</p>",
    show_if=age.lt(18),                      # gate the screen-out
)

done = FinalPage(
    "done", title="Thanks", body="<p>Thank you for participating.</p>",
    redirect_url="https://panel.example.com/done", redirect_delay=3,
)

rd = RedirectPage("rd", redirect_url="https://panel.example.com/complete")

# is_terminal reflects the kind
intro.is_terminal     # False
dq.is_terminal        # True
```

## `Block`

A `Block` groups questions (and nested blocks) inside a page. Use it to apply a bulk
visibility rule to several items at once, or to randomize a subset.

```python
@dataclass(frozen=True, slots=True)
class Block:
    title: str | None = None
    items: list[Question | Block] = []
    randomize: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `str \| None` | `None` | Optional header above the block items. |
| `items` | `list[Question \| Block]` | `[]` | Questions or nested blocks inside the block. |
| `randomize` | `bool` | `False` | Shuffle the order of items within the block. |
| `show_if` | `Expression \| str \| None` | `None` | Show the whole block only when this is true. |
| `hide_if` | `Expression \| str \| None` | `None` | Hide the whole block when this is true. |

`Block.flatten_questions()` returns the questions inside it, recursing into nested
blocks.

```python
demographics = sg.Block(
    title="About you",
    items=[q_age, q_gender, q_region],
)

attitudes = sg.Block(
    title="Political attitudes",
    items=[q_trust, q_party],
    show_if=age.ge(18),            # whole block gated to adults
    randomize=True,                # shuffle the two questions
)

page = sg.Page(name="main", items=[demographics, attitudes], randomize_blocks=True)
```

## Assembling a `Questionnaire`

The `Questionnaire` aggregate root combines pages (or blocks), variables, a deadline,
and scripts.

```python
@dataclass(frozen=True, slots=True)
class Questionnaire:
    title: str
    blocks: list[Question | Block] = []
    pages: list[Page] = []
    deadline: datetime | None = None
    variables: VariableMap | None = None
    scripts: list[Script] = []
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `str` | *required* | Survey title. Non-empty. |
| `blocks` | `list[Question \| Block]` | `[]` | Items for a single-page survey. **Cannot be combined with `pages`.** |
| `pages` | `list[Page]` | `[]` | Pages for a multi-page survey. **Cannot be combined with `blocks`.** |
| `deadline` | `datetime \| None` | `None` | Closing date/time. |
| `variables` | `VariableMap \| None` | `None` | Explicit variable registry; inferred from questions if omitted. |
| `scripts` | `list[Script]` | `[]` | Lifecycle scripts (see [[Scripts]]). |

Use **either** `pages` **or** `blocks`, never both — passing both raises `ValueError`.
Most surveys use `pages`.

### Key methods

| Method | Purpose |
| :--- | :--- |
| `all_questions() -> list[Question]` | Flatten every page/block into one ordered list. |
| `validate(strict=False) -> None` | Structural + logical checks; raises `ValueError` on the first problem. With `strict=True`, also fails on lint errors. |
| `lint(level="basic") -> list[LintWarning]` | Heuristic warnings (`"basic"` or `"strict"`). |
| `simulate(n=100, seed=42) -> SurveyData` | Generate synthetic responses. |
| `compile(**options)` | Compile to the `SurveySchema` IR used by the frontend. |
| `deploy(backend="local", frontend="local", **options) -> DeployResult` | Provision, build, and publish. |
| `to_dict() -> dict` | Serialize the survey definition. |
| `validate_for_export(target="surveyjs") -> None` | Confirm the survey is export-compatible. |

`validate()` enforces unique page names and question ids, valid `skip_to` and
`next_if`/`default_next` navigation targets (including reachability and
cycle-detection across the page graph), expressions that reference only known
variables, and scripts that target real questions or pages.

### A complete example

```python
import siamang as sg
from siamang.core import ContentPage, DisqualificationPage, FinalPage

age = sg.Variable("age", scale="ratio", label="Age")
trust = sg.Variable("trust", scale="ordinal", label="Trust",
                   labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"})

survey = sg.Questionnaire(
    title="Political Trust — 2026",
    pages=[
        ContentPage("welcome", body="<p>Welcome.</p>"),
        sg.Page(
            name="main",
            title="About you",
            items=[
                sg.NumericInput("How old are you?", var=age, required=True),
                sg.LikertScale("How much do you trust the government?",
                               var=trust, points=5),
            ],
        ),
        DisqualificationPage("dq", body="<p>Not eligible.</p>", show_if=age.lt(18)),
        FinalPage("done", title="Thanks", body="<p>Thank you.</p>"),
    ],
)

survey.validate()                       # raises if structure/logic is wrong
print(len(survey.all_questions()))      # 2 (content/terminal pages hold no questions)
```

> **Single-page surveys.** For a quick one-screen survey you can pass `blocks=[...]`
> (questions and/or blocks) instead of `pages`; siamang renders them on a single page.

## See also

- [[Question Types|Question-Types]] — the items you place on pages.
- [[Visibility and Branching|Visibility-and-Branching]] — `show_if`, `next_if`, and page routing.
- [[Core Concepts|Core-Concepts]] — the model tree and the questionnaire root.
- [[Validation and Linting|Validation-and-Linting]] — what `validate()` and `lint()` check.
