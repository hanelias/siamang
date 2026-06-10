# Core Concepts

This page explains the ideas behind siamang: the *research-as-code* philosophy, the
five-layer data model, the variable registry (`VariableMap`), and an overview of the
typed expression DSL that powers conditional logic.

## Research-as-code

A siamang questionnaire is a **plain Python module**, not a row in a proprietary
database. That has concrete consequences:

- it lives in version control alongside the rest of your code;
- it can be reviewed, diffed, branched, and rolled back like any source file;
- it can be tested with standard tooling (`pytest`, type checkers, linters);
- it can be imported and inspected from a notebook or pipeline.

The *same* module flows through every stage of the survey lifecycle — validation,
preview, deployment, data collection, and analysis:

```
my_survey.py
    ├── siamang validate    →  schema + logic validation
    ├── siamang preview     →  local React frontend (SQLite backend)
    ├── siamang deploy      →  Vercel + Supabase (production)
    ├── survey.simulate(n=) →  synthetic dataset for testing analysis
    ├── SurveyData.export() →  CSV / Excel / SPSS / Stata / R round-trip
    └── SurveyData.report   →  declarative tables, charts, banner tables
```

## The five-layer data model

siamang separates concerns into five layers, each with a strict responsibility.

| Layer | Module | Responsibility |
| :--- | :--- | :--- |
| 1. Model | `siamang.core` | The questionnaire as a tree of immutable dataclasses. |
| 2. Frontend | `siamang.frontend` | Compile the model to a schema and a self-contained bundle. |
| 3. Deploy | `siamang.deploy` | Provision a backend, publish the bundle, return a URL. |
| 4. Data | `siamang.data` | Wrap a pandas `DataFrame` + `VariableMap` with analysis accessors. |
| 5. I/O | `siamang.io` | Round-trip data and metadata with CSV/Excel/SPSS/Stata/R. |

This page focuses on **layer 1**, the model — the part you author by hand. The other
layers are covered in [[Deployment]], [[Working with Data|Working-with-Data]], and
[[Data Import and Export|Data-Import-and-Export]].

### The model tree

A questionnaire is a tree of frozen dataclasses:

```
Questionnaire
├── pages: list[Page]
│       ├── items: list[Question | Block]
│       └── show_if / hide_if : Expression | str | None
└── variables: VariableMap
```

| Object | Role |
| :--- | :--- |
| `Variable` | An atomic measurement unit (`name`, `scale`, `labels`, `missing_values`, …). |
| `Question` and its subclasses | Bind a prompt to one variable (or many, for `Matrix` and wide `MultiChoice`). |
| `Option` | A single answer choice with its own `show_if`/`hide_if` and optional `Media`. |
| `Media` | An `image`, `video`, or `audio` attachment to a question or option. |
| `Page` | One screen in the survey, with its own visibility gate and a `kind`. |
| `Block` | A named container of questions/blocks inside a page; randomisable; hideable. |
| `Expression` | The typed DSL for visibility conditions (`age.ge(18) & gender.eq(2)`). |
| `Quota` | A respondent target per cell (variable / value / limit). |
| `Script` | A JavaScript snippet hooked into a survey lifecycle event. |
| `Questionnaire` | The aggregate root; owns pages or blocks and provides `validate()`, `compile()`, `simulate()`, `deploy()`. |

Every core dataclass is `frozen=True, slots=True`: once you construct a
questionnaire, no other code can mutate it. This keeps survey definitions
side-effect free, thread-safe, and deterministic across compilation, simulation,
and analysis.

A minimal end-to-end example:

```python
import siamang as sg

trust = sg.Variable(
    "trust", scale="ordinal", label="Trust in government",
    labels={1: "No trust", 2: "Low", 3: "Medium", 4: "High", 5: "Full trust"},
)

survey = sg.Questionnaire(
    title="Trust Study",
    pages=[sg.Page("main", items=[
        sg.LikertScale("How much do you trust the government?", var=trust, points=5),
    ])],
)
survey.validate()
```

## Variables vs. answers

A `Variable` carries the **definition** — `name`, `scale`, `labels`,
`missing_values`, `valid_range`, `role`, and codebook fields. An **answer** is a row
in the collected `DataFrame`, keyed by `variable.name`.

When you simulate or deploy a survey, siamang derives the dataset schema from the
variable registry. If you pass an explicit
`Questionnaire(variables=VariableMap([...]))`, that registry is the source of truth;
otherwise siamang **auto-builds** one by walking every question. See
[[Variables and Measurement|Variables-and-Measurement]] for the full `Variable` and
`VariableMap` reference.

## The VariableMap registry

`VariableMap` is a `dict[str, Variable]` subclass indexed by variable name. It is the
centralized registry for a survey and the bridge between the model and the collected
data:

```python
from siamang.core import VariableMap, Variable

vm = VariableMap()
vm.add_many([
    Variable("age", scale="ratio", label="Age"),
    Variable("gender", scale="nominal", label="Gender", labels={1: "M", 2: "F"}),
])

vm.require("age")          # lookup; raises KeyError if absent
vm.by_scale("nominal")     # [Variable('gender', ...)]
issues = vm.validate_frame(data.frame)   # validate a DataFrame against the schema
```

Because it derives labels, value labels, and missing-value conventions, the same
`VariableMap` produces an SPSS `.sav` that opens identically in SPSS, and reads such
a file back into siamang with metadata intact.

## The expression DSL (overview)

Visibility and branching conditions are written as typed `Expression` trees, built
from `Variable` helpers and the `AND` / `OR` / `NOT` combinators:

```python
age >= 18                       # Expression(">=", VarRef("age"), 18)
age.ge(18) & gender.eq(2)       # Expression("and", ..., ...)
~age.isin([18, 19])             # NOT
sg.AND(age.ge(18), gender.eq(2), region.isin([1, 2]))
```

The typed form is preferred because it is **type-checked** at construction, can be
**evaluated in Python** (which backs `simulate()` and `validate()`; the React
runtime evaluates the same serialized expression tree client-side, in JavaScript),
and serializes losslessly to JSON. A
visibility gate (`show_if` / `hide_if`) can attach to a `Page`, `Block`, `Question`,
or `Option`; questions additionally support `skip_to`, and pages support `next_if`
routing. A `str` in the SurveyJS dialect (`"age >= 18"`) is also accepted and
preserved verbatim, but cannot be evaluated in Python.

The full operator set, evaluation, serialization, and routing semantics are covered
in [[Visibility and Branching|Visibility-and-Branching]].

## Lifecycle scripts (overview)

`Script` injects a sandboxed JavaScript snippet that runs in the respondent's
browser at one of seven trigger points (`onInit`, `onPageEnter`, `onPageExit`,
`onQuestionShow`, `onAnswer`, `onSubmit`, `onRandomize`). Inside the snippet you have
`answers`, `utils`, `api`, and `context`. Built-in factories cover the common cases
(randomizing options/pages, matched-field validation, timed questions). See
[[Scripts]].

## See also

- [[Variables and Measurement|Variables-and-Measurement]] — the `Variable` and `VariableMap` reference.
- [[Question Types|Question-Types]] — all seven question types.
- [[Visibility and Branching|Visibility-and-Branching]] — the Expression DSL in depth.
- [[Pages Blocks and Structure|Pages-Blocks-and-Structure]] — pages, blocks, and the questionnaire root.
