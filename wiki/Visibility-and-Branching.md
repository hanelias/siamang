# Visibility and Branching

Conditional visibility and routing are expressed with a small typed DSL. You build an
`Expression` tree from `Variable` helpers and the `AND` / `OR` / `NOT` combinators,
then attach it to a `show_if`, `hide_if`, `skip_to`, or `next_if` field. The same
expression can be evaluated in Python (for `simulate()` and `validate()`) and
compiled to a SurveyJS string for the frontend.

```python
from siamang.core import Expression, VarRef, compare, AND, OR, NOT, FilterRule
```

## Building expressions

The most ergonomic way is the `Variable` comparison helpers and Python operators:

```python
age >= 18                       # Expression(">=", VarRef("age"), 18)
age.ge(18) & gender.eq(2)       # Expression("and", ..., ...)
~age.isin([18, 19])             # NOT(...)
AND(age.ge(18), gender.eq(2), region.isin([1, 2]))
```

| Helper | Operator | Example | SurveyJS form |
| :--- | :--- | :--- | :--- |
| `var.eq(v)` | `=` | `gender.eq(1)` | `{gender} = 1` |
| `var.ne(v)` | `!=` | `gender.ne(1)` | `{gender} != 1` |
| `var.gt(v)` | `>` | `age.gt(18)` | `{age} > 18` |
| `var.ge(v)` | `>=` | `age.ge(18)` | `{age} >= 18` |
| `var.lt(v)` | `<` | `age.lt(65)` | `{age} < 65` |
| `var.le(v)` | `<=` | `age.le(65)` | `{age} <= 65` |
| `var.isin(vs)` | `in` | `region.isin([1, 2])` | `{region} in [1, 2]` |
| `var.notin(vs)` | `not in` | `region.notin([99])` | `{region} not in [99]` |

`>`, `>=`, `<`, `<=` are overloaded on `Variable`, so `age >= 18` works directly.
Equality is **not** overloaded (Python reserves `==` for dataclass identity), so use
`var.eq(value)`.

### `compare`

A free function that builds a comparison from a **variable name** (string) rather than
a `Variable` instance — handy when you only have the name:

```python
def compare(var_name: str, op: str, value: Any) -> Expression
```

```python
from siamang.core import compare
compare("age", ">=", 18)        # Expression(">=", VarRef("age"), 18)
```

Valid `op` values: `"="`, `"!="`, `">"`, `">="`, `"<"`, `"<="`, `"in"`, `"not in"`.

## Combinators: `AND`, `OR`, `NOT`

```python
def AND(*expressions: Expression) -> Expression    # >= 2 args
def OR(*expressions: Expression) -> Expression      # >= 2 args
def NOT(expression: Expression) -> Expression
```

`AND` and `OR` accept two or more expressions (fewer raises `ValueError`) and fold
them left-to-right. They are equivalent to the `&`, `|`, and `~` operators on
`Expression`:

```python
gate = AND(age.ge(18), OR(region.eq(1), region.eq(2)), NOT(party.eq(99)))
# same as:
gate = age.ge(18) & (region.eq(1) | region.eq(2)) & ~party.eq(99)
```

## `Expression`

```python
@dataclass(frozen=True, slots=True)
class Expression:
    op: str
    left: Any = None
    right: Any = None
```

| Field | Description |
| :--- | :--- |
| `op` | Operator: a comparison (`=`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not in`), a logical op (`and`, `or`, `not`), or `raw`. |
| `left` | Left operand — usually a `VarRef` or a nested `Expression`. |
| `right` | Right operand — a literal, a list/set, or a nested `Expression`. |

You rarely construct `Expression` directly; prefer the helpers above. The operators
`&`, `|`, `~` build `and`/`or`/`not` nodes.

### Methods

- **`evaluate(answers: dict) -> bool`** — evaluate against an answers dict; returns a
  bool. Raises `ValueError` for `raw` expressions (they cannot be evaluated safely).
- **`variables() -> set[str]`** — all variable names referenced in the tree.
- **`validate(variables) -> None`** — ensure every referenced variable is in the
  provided set/mapping and the operator tree is well-formed; raises `ValueError`
  otherwise. (Also rejects `raw`.)
- **`to_surveyjs() -> str`** — compile to a SurveyJS expression string.
- **`to_dict() -> dict`** / **`from_dict(payload)`** — lossless JSON serialization.
- **`Expression.raw(text)`** *(classmethod)* — wrap a verbatim SurveyJS string as an
  escape hatch (`op="raw"`). Raw expressions are passed through to the frontend but
  cannot be evaluated or validated in Python.

```python
expr = AND(age.ge(18), gender.eq(2))

expr.evaluate({"age": 30, "gender": 2})    # True
expr.evaluate({"age": 16, "gender": 2})    # False
expr.variables()                            # {"age", "gender"}
expr.validate({"age", "gender"})            # OK
expr.to_surveyjs()                          # "({age} >= 18) and ({gender} = 2)"
expr.to_dict()                              # nested dict, round-trips via from_dict
```

## `VarRef`

```python
@dataclass(frozen=True, slots=True)
class VarRef:
    name: str
```

A reference to a variable name inside an expression; the comparison helpers wrap your
variable name in a `VarRef` automatically. Its `evaluate(answers)` returns
`answers.get(name)` (so an unanswered variable evaluates to `None`), `variables()`
returns `{name}`, and `to_dict()` serializes it. Its `str()` form is `{name}` — the
token used in the SurveyJS dialect.

## Where expressions plug in

A visibility gate or routing rule can attach at several levels. An element is rendered
**iff** `show_if` is true (or absent) **and** `hide_if` is not true (or absent).

| Level | Fields |
| :--- | :--- |
| `Page` | `show_if`, `hide_if`, plus `next_if` / `default_next` routing |
| `Block` | `show_if`, `hide_if` |
| `Question` | `show_if`, `hide_if`, `skip_to` |
| `Option` | `show_if`, `hide_if` |

```python
import siamang as sg

# Question-level visibility
q_kids = sg.NumericInput(
    "How many children do you have?", var=num_children,
    show_if=has_children.eq(1),
    hide_if=age.lt(18),
)

# Page-level gate (typed or operator form)
sg.Page("political", items=[...], show_if=AND(age.ge(18), region.isin([1, 2])))
sg.Page("adults",    items=[...], show_if=age >= 18)

# Block-level gate
sg.Block(title="Adults only", items=[...], show_if=age.ge(18))

# Option-level visibility (see Question Types)
sg.Option(4, "Green", show_if=age.ge(18))
```

### `skip_to`

`Question.skip_to` jumps to a target page or question id after the question is
answered. The target must exist; `Questionnaire.validate()` raises if `skip_to`
references an unknown id.

```python
q_screen = sg.SingleChoice(
    "Do you currently live in the country?", var=resident,
    skip_to="dq",            # jump to a disqualification page when answered out
)
```

### `next_if` — page routing

`Page.next_if` is a list of `(condition, target_page_name)` rules evaluated in order;
the first match wins, otherwise `default_next` (or the next page in sequence) is used.

```python
sg.Page(
    name="screener",
    items=[q_age],
    next_if=[("{age} < 18", "dq")],   # SurveyJS-string condition + target page
    default_next="main",
)
```

> Routing conditions in `next_if` are stored as `(condition, target)` string pairs.
> Use `Expression.to_surveyjs()` if you want to build them from typed expressions.
> Page-level `show_if`/`hide_if` accept either a typed `Expression` or a string.

### String form

Any gate also accepts a string in the SurveyJS dialect. Strings are preserved
verbatim and sent to the frontend, but are **not** evaluated in Python:

```python
sg.Page("adults", items=[...], show_if="age >= 18")
```

`Questionnaire.validate()` still checks that `{name}` tokens in a string gate
reference known variables — bare names (like the `age` above) are not extracted
or checked.

## Evaluation and serialization

Typed expressions are the recommended form because they:

- are **type-checked** at construction;
- can be **evaluated in Python** — `Expression.evaluate` backs `simulate()` and
  `validate()`; the React runtime evaluates the *same* serialized expression tree
  client-side (in JavaScript);
- **serialize losslessly** to JSON via `to_dict()` / `from_dict()` and compile to a
  SurveyJS string via `to_surveyjs()`.

```python
from siamang.core import Expression

payload = AND(age.ge(18), gender.eq(2)).to_dict()
restored = Expression.from_dict(payload)
restored.to_surveyjs()        # "({age} >= 18) and ({gender} = 2)"
```

## `FilterRule`

For visibility logic that is easier to express as arbitrary Python rather than the
DSL, `FilterRule` wraps a predicate over an answers dict.

```python
@dataclass(frozen=True, slots=True)
class FilterRule:
    predicate: Callable[[dict[str, Any]], bool]
    description: str | None = None
```

- **`evaluate(answers) -> bool`** — call the predicate and coerce to bool.

```python
from siamang.core import FilterRule

adult_in_capital = FilterRule(
    predicate=lambda a: a.get("age", 0) >= 18 and a.get("region") == 1,
    description="Adults living in the capital",
)
adult_in_capital.evaluate({"age": 30, "region": 1})    # True
```

`FilterRule` is a Python-side predicate; unlike `Expression` it does not compile to a
SurveyJS string, so use it for analysis-time filtering and simulation logic rather
than frontend gating.

## See also

- [[Question Types|Question-Types]] — where `show_if`/`hide_if`/`skip_to` live on questions and options.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — page `next_if` routing and block gates.
- [[Variables and Measurement|Variables-and-Measurement]] — the comparison helpers on `Variable`.
- [[Scripts]] — JavaScript hooks for behavior the DSL cannot express.
