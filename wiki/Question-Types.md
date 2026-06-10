# Question Types

A `Question` binds a respondent-facing prompt to one variable (or many, for `Matrix`
and wide `MultiChoice`). siamang ships **seven** concrete question types, all frozen
dataclasses inheriting the shared `Question` fields. This page documents the base
class, every type, and the `Option` and `Media` helpers that enrich answer choices.

```python
from siamang.core import (
    SingleChoice, MultiChoice, LikertScale, NumericInput,
    OpenText, Matrix, Ranking, Option, Media,
)
```

## The `Question` base class

`Question` is the shared base; you instantiate its subclasses, not `Question`
itself. Every type accepts these fields.

```python
@dataclass(frozen=True, slots=True)
class Question:
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
    metadata: dict[str, Any] = {}
```

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `text` | `str` | *required* | The prompt shown to the respondent. Must be non-empty. |
| `var` | `Variable \| list[Variable]` | *required* | The bound variable(s); answers are stored under their names. |
| `required` | `bool` | `False` | Respondent must answer before advancing. |
| `hint` | `str \| None` | `None` | Helper text shown beneath the prompt. |
| `show_if` | `Expression \| str \| None` | `None` | Render only when this evaluates true. |
| `hide_if` | `Expression \| str \| None` | `None` | Hide when this evaluates true. |
| `skip_to` | `str \| None` | `None` | Jump to a target page/question id after answering. |
| `randomize` | `bool` | `False` | Shuffle the answer choices. |
| `other_specify` | `bool` | `False` | Add an "Other (please specify)" free-text choice. |
| `tag` | `str \| list[str] \| None` | `None` | Tag(s) for categorization/filtering. |
| `id` | `str \| None` | `None` | Explicit question id; defaults to the variable name — except for `Matrix` and wide-mode `MultiChoice`, where the fallback is `matrix_<first var>` / `multi_<first var>`. |
| `name` | `str \| None` | `None` | Output column name; defaults to the id. |
| `media` | `Media \| list[Media] \| None` | `None` | Image/video/audio attached to the prompt. |
| `metadata` | `dict[str, Any]` | `{}` | Free-form extra parameters. |

`show_if` / `hide_if` / `skip_to` are detailed in
[[Visibility and Branching|Visibility-and-Branching]]; `media` is covered under
[Media](#media) below.

---

## `SingleChoice`

One mutually-exclusive answer from a set of options.

```python
@dataclass(frozen=True, slots=True)
class SingleChoice(Question):
    display: str = "radio"            # "radio" | "dropdown" | "buttons"
    none_of_above: bool = False
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `display` | `"radio"` | UI style: `"radio"`, `"dropdown"`, or `"buttons"` (segmented). |
| `none_of_above` | `False` | Append a "None of the above" option that deselects others. |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from the variable's `labels`. |

`var` must be a single `Variable`. When `choices` is omitted, the options come from
`var.labels`.

```python
import siamang as sg

gender = sg.Variable("gender", scale="nominal", label="Gender",
                     labels={1: "Male", 2: "Female", 3: "Other"})

q_gender = sg.SingleChoice(
    "What is your gender?", var=gender,
    display="buttons", required=True,
)
```

---

## `MultiChoice`

Select one or more options. Supports two storage layouts — **array** (one column
holding a list of selected codes) and **wide** (one binary column per option).

```python
class MultiChoice(Question):
    min_answers: int = 1
    max_answers: int | None = None
    exclusive: list[int] = []
    mode: str = "array"               # "array" | "wide"
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `min_answers` | `1` | Minimum selections (enforced when `required`). |
| `max_answers` | `None` | Maximum selections; in wide mode cannot exceed the number of variables. |
| `exclusive` | `[]` | Codes that clear all other selections when chosen (e.g. "None"). |
| `mode` | `"array"` | `"array"` stores a list in one column; `"wide"` spreads binary flags across columns. |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from `labels`. |

Pass **`var=`** (a single `Variable`) for array mode, or the keyword-only **`vars=`**
(a non-empty list of `Variable`) to switch to wide mode automatically. Passing both
`var` and `vars` raises `ValueError`.

```python
# Array mode — one column, list of selected codes
hobbies = sg.Variable("hobbies", scale="nominal",
                     labels={1: "Music", 2: "Sport", 3: "Reading", 99: "None"})
q_hobbies = sg.MultiChoice(
    "Which hobbies do you have?", var=hobbies,
    min_answers=1, max_answers=3,
    exclusive=[99],            # picking "None" clears the others
)

# Wide mode — one binary column per source
sources = [sg.Variable(f"src_{n}", scale="nominal", labels={0: "No", 1: "Yes"},
                       label=f"Source {n}") for n in ("tv", "radio", "web")]
q_sources = sg.MultiChoice("Where do you get news from?", vars=sources)
```

---

## `LikertScale`

A symmetric ordinal rating scale.

```python
@dataclass(frozen=True, slots=True)
class LikertScale(Question):
    points: int = 5                   # must be >= 2
    left_label: str | None = None
    right_label: str | None = None
    na_option: bool | str = False
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `points` | `5` | Number of scale points. Must be `>= 2`. |
| `left_label` | `None` | Anchor label on the far left (e.g. `"Strongly disagree"`). |
| `right_label` | `None` | Anchor label on the far right (e.g. `"Strongly agree"`). |
| `na_option` | `False` | `True` adds a "Not applicable" choice; a string sets its label. |

`var` must be a single `Variable` (ideally `ordinal`).

```python
trust = sg.Variable("trust", scale="ordinal", label="Trust in government",
                   labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"})

q_trust = sg.LikertScale(
    "How much do you trust the government?", var=trust, points=5,
    left_label="No trust", right_label="Full trust",
    na_option=True,
)
```

---

## `NumericInput`

A continuous numeric value.

```python
@dataclass(frozen=True, slots=True)
class NumericInput(Question):
    display: str = "input"            # "input" | "slider"
    unit: str | None = None
    step: int | float = 1             # must be > 0
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `display` | `"input"` | `"input"` (number box) or `"slider"`. |
| `unit` | `None` | Unit shown next to the field (e.g. `"years"`, `"%"`). |
| `step` | `1` | Increment for sliders/number inputs. Must be `> 0`. |

`var` must be a single `Variable`. If the variable has `valid_range=(min, max)`, the
React runtime forwards it as the input's `min`/`max`.

```python
age = sg.Variable("age", scale="ratio", label="Age", valid_range=(18, 99))

q_age = sg.NumericInput(
    "How old are you?", var=age,
    display="input", step=1, unit="years", required=True,
)
```

---

## `OpenText`

Free-form text.

```python
@dataclass(frozen=True, slots=True)
class OpenText(Question):
    multiline: bool = False
    max_chars: int | None = None      # must be > 0 when set
    placeholder: str | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `multiline` | `False` | Render a multiline `<textarea>` instead of a single line. |
| `max_chars` | `None` | Character limit. Must be `> 0` when set. |
| `placeholder` | `None` | Ghost text shown while the field is empty. |

```python
comments = sg.Variable("comments", scale="nominal")

q_open = sg.OpenText(
    "Anything else you would like to add?", var=comments,
    multiline=True, max_chars=500, placeholder="Optional comments…",
)
```

---

## `Matrix`

A grid of subquestions (rows) sharing a common column scale. Efficient for batteries
of Likert items.

```python
@dataclass(frozen=True, slots=True)
class Matrix(Question):
    var: list[Variable]               # one variable per row; required, non-empty
    subquestions: list[str] | None = None
    column_labels: list[str] | None = None
    na_option: bool | str = False
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `var` | *required* | Non-empty list of `Variable` — one per row. |
| `subquestions` | `None` | Row labels; default to each variable's `label`. |
| `column_labels` | `None` | Column headers; default to the variables' value `labels`. |
| `na_option` | `False` | `True` adds a "Not applicable" column; a string sets its header. |

```python
def trust_dim(name, label):
    return sg.Variable(name, scale="ordinal", label=label,
                      labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full"})

q_trust_matrix = sg.Matrix(
    "How much do you trust each of the following?",
    var=[
        trust_dim("trust_govt",   "The government"),
        trust_dim("trust_courts", "The courts"),
        trust_dim("trust_media",  "The press"),
    ],
)
```

---

## `Ranking`

Sort options into an order of preference (drag-and-drop).

```python
@dataclass(frozen=True, slots=True)
class Ranking(Question):
    max_ranked: int | None = None     # must be > 0 when set
    choices: list[Option] | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `max_ranked` | `None` | How many items must be ranked (e.g. "rank your top 3"). Must be `> 0`. |
| `choices` | `None` | Explicit `Option` list; if `None`, derived from `labels`. |

`var` must be a single `Variable`.

```python
brands = sg.Variable("brand_rank", scale="ordinal",
                    labels={1: "Acme", 2: "Globex", 3: "Initech"})

q_rank = sg.Ranking("Rank these brands from best to worst", var=brands, max_ranked=3)
```

---

## `Option`

Use `Option` instead of a plain `{code: label}` mapping when a choice needs
conditional visibility or a media attachment. `Option` is accepted by the `choices=`
field of `SingleChoice`, `MultiChoice`, and `Ranking`.

```python
@dataclass(frozen=True, slots=True)
class Option:
    code: Any
    label: str
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    media: Media | None = None
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `code` | *required* | The stored code if chosen. Must match the type used in `Variable.labels`. |
| `label` | *required* | Displayed text; overrides the variable's registered label. Non-empty. |
| `show_if` / `hide_if` | `None` | Per-option visibility condition. |
| `media` | `None` | A single `Media` attachment for this option. |

Option codes within a `choices` list must be unique; duplicates raise `ValueError`.

```python
from siamang.core import Option, Media

q_color = sg.SingleChoice(
    "Pick a colour", var=fav,
    choices=[
        Option(1, "Red",   media=Media("https://cdn.example.com/red.png")),
        Option(2, "Blue",  media=Media("https://cdn.example.com/blue.png")),
        Option(3, "Pink",  hide_if=gender.eq(1)),
        Option(4, "Green", show_if=age.ge(18)),
    ],
)
```

## `Media`

An image, video, or audio attachment for a question (`media=`) or option.

```python
@dataclass(frozen=True, slots=True)
class Media:
    url: str
    kind: str | None = None           # "image" | "video" | "audio"
    alt: str | None = None
    caption: str | None = None
    autoplay: bool = False
    loop: bool = False
    controls: bool = True
```

| Field | Default | Description |
| :--- | :--- | :--- |
| `url` | *required* | URL to the media file. Non-empty. |
| `kind` | `None` | `"image"`/`"video"`/`"audio"`; inferred from the URL extension if omitted. |
| `alt` | `None` | Accessibility text (HTML `alt`). |
| `caption` | `None` | Caption shown beneath the media. |
| `autoplay` | `False` | Auto-play video/audio when visible. |
| `loop` | `False` | Loop playback. |
| `controls` | `True` | Show playback controls. |

`kind` is inferred from the file extension (`png`/`jpg`/… → image, `mp4`/`webm`/… →
video, `mp3`/`wav`/… → audio). A URL **without a recognisable extension** requires
`kind` to be passed explicitly, otherwise construction raises `ValueError`.

```python
from siamang.core import Media

q_clip = sg.SingleChoice(
    "Did you find the clip persuasive?", var=persuasion,
    media=Media("https://cdn.example.com/intro.mp4", caption="Watch before answering."),
)

# Extensionless URL: kind is required
logo = Media("https://cdn.example.com/asset?id=42", kind="image", alt="Brand logo")
```

## See also

- [[Variables and Measurement|Variables-and-Measurement]] — the variables questions bind to.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — placing questions on pages and in blocks.
- [[Visibility and Branching|Visibility-and-Branching]] — `show_if`, `hide_if`, and `skip_to`.
- [[Quotas]] — capping responses per category.
