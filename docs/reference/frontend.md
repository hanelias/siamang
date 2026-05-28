# `siamang.frontend` — bundle builder and runtimes reference

The `frontend` subpackage compiles a `Questionnaire` into a deployable
static bundle (HTML + JS + CSS + env). End users normally just call
`survey.deploy(...)`; this page documents the pipeline that lives
behind that call.

```python
from siamang.frontend import (
    FrontendBuilder, UIConfig,
    SurveySchema, SurveyBundle,
    ReactRuntime, SurveyJSRuntime, RuntimeAdapter, RuntimeRenderContext,
    BackendClientTemplate, LocalClientTemplate, SupabaseClientTemplate, ClientEnv,
    compile_questionnaire, compile_expression, expression_variables,
    THEME_PRESETS, compile_css, get_preset,
)
```

---

## `SurveySchema` — the intermediate representation

```python
@dataclass(frozen=True, slots=True)
class SurveySchema:
    title: str
    pages: list[dict[str, Any]]
    variables: dict[str, dict[str, Any]]
    language: str = "en"
    description: str | None = None
    completion_text: str = "Thank you for your participation!"
    show_progress: bool = True
    allow_back: bool = True
    one_question_per_page: bool = False
    deadline: datetime | None = None
    max_responses: int | None = None
    quotas: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
```

Produced by `compile_questionnaire(...)`. Immutable; safe to embed in
the deployed bundle.

Methods:

- `to_surveyjs() -> dict` — render to a SurveyJS-compatible JSON shape
  (used by `SurveyJSRuntime`).
- `to_dict() -> dict` — full serialisation (includes `format_version=1`
  and ISO-formatted `deadline`).

---

## `SurveyBundle`

```python
@dataclass(frozen=True, slots=True)
class SurveyBundle:
    files: dict[str, str | bytes] = {}     # {relative_path: content}
    manifest: dict[str, Any] = {}          # {"format_version", "survey_id", "title", "runtime", ...}
```

Methods:

| Method | Returns |
|--------|---------|
| `write_to(target: str \| Path)` | `Path` — write every file to the directory (creating parents). |
| `to_zip() -> bytes` | Deflate-compressed ZIP archive of the whole bundle. |
| `manifest_json() -> str` | Pretty-printed JSON of the manifest. |
| `compute_digest() -> str` | 16-char SHA-256 prefix over all file contents. |
| `with_hashed_filenames() -> SurveyBundle` | New bundle where every `.js` and `.css` has a content-hashed filename (e.g. `app.js → app.a1b2c3d4.js`); HTML references are rewritten automatically. |

---

## `FrontendBuilder`

```python
@dataclass(frozen=True, slots=True)
class FrontendBuilder:
    runtime: RuntimeAdapter = SurveyJSRuntime()
    ui: UIConfig = UIConfig()

    def build(
        self,
        schema: SurveySchema,
        *,
        client: BackendClientTemplate,
        env: ClientEnv,
        survey: Questionnaire | None = None,
    ) -> SurveyBundle: ...
```

Orchestrates runtime + theme + client into a `SurveyBundle`. The
returned bundle:

- has `index.html`, `closed.html`, `style.css`, `env.js`,
  `manifest.json`;
- contains any extra files the runtime contributes via
  `RuntimeAdapter.static_assets()`;
- has every filename content-hashed for cache busting.

`survey=` is required when `runtime` is `ReactRuntime` (the React
templates compile direct from the live `Questionnaire`); for
`SurveyJSRuntime` only `schema` is needed.

---

## `UIConfig`

```python
@dataclass(frozen=True, slots=True)
class UIConfig: ...
```

All branding, theme, and copy settings live here. Every field has a
sensible default; only fill in what you want to customise.

### Palette

| Field | Default | Notes |
|-------|---------|-------|
| `primary_color` | `"#2c5f8a"` | Main brand colour. |
| `accent_color` | `None` | Falls back to `primary_color`. |
| `background_color` | `"#fbfbfb"` | Page background. |
| `surface_color` | `"#ffffff"` | Card / panel background. |
| `text_color` | `"#1a1a1a"` | Body text. |
| `muted_text_color` | `"#5a5a5a"` | Hint / secondary text. |
| `border_color` | `"#e6e4df"` | Dividers and input borders. |
| `error_color` | `"#b3261e"` | Error state. |
| `error_soft_color` | `"#fdf1f0"` | Error background tint. |
| `warn_color` | `"#9a6a1a"` | Warning state. |

### Typography

| Field | Default | Notes |
|-------|---------|-------|
| `font_family` | Source Serif 4 stack | Body font. |
| `heading_font_family` | `None` | Inherits from `font_family`. |
| `ui_font_family` | Inter stack | Form controls and UI text. |
| `mono_font_family` | JetBrains Mono stack | Code / preformatted. |
| `font_size` | `"15.5px"` | Base size. |
| `line_height` | `"1.6"` | Body line spacing. |
| `font_pair` | `"serif"` | `"serif"` / `"sans"` / `"mixed"` preset for the heading↔body pairing. |

### Layout

| Field | Default | Notes |
|-------|---------|-------|
| `width` | `"700px"` | Max container width. |
| `radius` | `"4px"` | Border radius (cards, buttons, inputs). |
| `density` | `"comfortable"` | One of `"compact"`, `"comfortable"`, `"spacious"`. |
| `question_style` | `"plain"` | One of `"plain"`, `"divided"`, `"carded"`, `"accent"`. |

### Header & footer

| Field | Default | Notes |
|-------|---------|-------|
| `logo_url` | `None` | If set, rendered as `<img>` in the header. |
| `logo_text` | `None` | Text fallback when `logo_url` is unset. Auto-derived from `institution_name` initials. |
| `logo_position` | `"left"` | `"left"` / `"right"` / `"center"`. |
| `show_title` | `True` | Show the questionnaire title in the header. |
| `institution_name` | `None` | Shown below the title; also feeds `effective_logo_text`. |
| `study_subtitle` | `None` | Subtitle text below the institution name. |
| `show_section_numbers` | `True` | Display page numbers in the progress indicator. |
| `show_progress_text` | `True` | "Page X of Y" text in the progress bar. |
| `estimated_minutes` | `None` | Surfaced in the welcome page meta. |
| `privacy_url` | `None` | Footer link. |
| `contact_email` | `None` | Footer `mailto:` link. |
| `ethics_statement` | `None` | Footer text block. |

### Localisation

All these default to English strings if unset. Override per language:

```
next_button_text, prev_button_text, submit_button_text, submitting_text,
required_text, saving_text, select_placeholder, of_text, selected_text,
resume_title, resume_action, restart_action, page_text, of_total_text,
retry_title, retry_body, retry_action, save_local_action,
completion_title, completion_body
```

### Progress & themes

| Field | Default | Notes |
|-------|---------|-------|
| `progress_style` | `"bar"` | `"bar"` / `"dots"` / `"both"`. |
| `default_theme` | `"light"` | `"light"` / `"dark"` / `"system"`. |
| `redirect_url` | `None` | Auto-redirect after completion (5 s timer). |

### Navigation

| Field | Default | Notes |
|-------|---------|-------|
| `allow_back` | `True` | When `False`, hides the "Previous" button on every page, disables the Escape shortcut, swipe-right gesture, and backward jumps via the progress dots. Useful for fixed-order surveys where editing past answers would break branching. |

### Access control

```python
UIConfig(
    require_access_code=True,
    access_codes=["wave1-001", "wave1-002"],
    access_title="Enter your invite code",
    access_body="Your code arrived in the recruitment email.",
)
```

### Analytics

`enable_analytics: bool = False` — when truthy *and* the deploy target
is Vercel, injects the Vercel Analytics script.

### Custom CSS

`custom_css: str | None = None` — raw CSS appended to the compiled
stylesheet (overrides everything).

### Typography Presets

- `font_preset: str = "academic"` — Selects one of the built-in typography configurations:
  - `"academic"` — Source Serif 4 body + Inter UI (default).
  - `"modern"` — Inter everywhere, clean geometric sans-serif.
  - `"humanist"` — Nunito everywhere, friendly rounded sans-serif.

### Computed properties

- `effective_accent` → `accent_color or primary_color`.
- `effective_body_font` → `font_family` if explicitly modified, otherwise resolved from `font_preset`.
- `effective_ui_font` → `ui_font_family` if explicitly modified, otherwise resolved from `font_preset`.
- `effective_heading_font` → `heading_font_family` if set, otherwise resolved from `font_preset`.
- `effective_google_fonts_url` → Google Fonts CDN link matching the active `font_preset`.
- `effective_logo_text` → `logo_text` if set, otherwise initials from
  `institution_name`, otherwise `""`.

### Presets

```python
from siamang.frontend import THEME_PRESETS, get_preset
print(THEME_PRESETS.keys())                   # available preset names
ui = get_preset("dark")                       # returns a UIConfig
```

`compile_css(ui: UIConfig) -> str` — render the design-system
stylesheet without going through a runtime (useful for static asset
pipelines).

---

## Runtimes

### `RuntimeAdapter` (abstract base)

```python
class RuntimeAdapter:
    name: str

    def render_html(self, context: RuntimeRenderContext) -> str: ...
    def render_closed_page(self, context: RuntimeRenderContext, reason: str) -> str: ...
    def stylesheet(self, context: RuntimeRenderContext) -> str | None: ...
    def static_assets(self) -> dict[str, str | bytes]: ...
```

A runtime turns a `RuntimeRenderContext` (schema + UI + survey id +
optional live `Questionnaire`) into the HTML pages and any extra
assets the bundle ships with.

### `RuntimeRenderContext`

```python
@dataclass(frozen=True, slots=True)
class RuntimeRenderContext:
    schema: SurveySchema
    ui: UIConfig
    css_href: str = "style.css"
    env_src: str = "env.js"
    survey_id: str | None = None
    survey: Questionnaire | None = None
```

### `SurveyJSRuntime`

```python
SurveyJSRuntime(version: str = constants.SURVEYJS_VERSION)
```

The original render path. Pulls SurveyJS from a CDN, embeds
`schema.to_surveyjs()` as JSON, and lets SurveyJS handle rendering.
Works from a `SurveySchema` alone (does not need the live
`Questionnaire`).

### `ReactRuntime`

```python
ReactRuntime(precompile: bool = True)
```

The default runtime. Self-contained: ships a pre-built React 18 bundle
(`dist/bundle.js`) that includes all question components, the answers
store, visibility engine, and navigation hooks. No JSX compilation
happens at deploy time — the bundle is built once during development
via `scripts/build_react_bundle.py` (uses sucrase for JSX→JS).

Required context: `survey` must be set. `render_html` raises
`ValueError` otherwise.

`ReactRuntime` is what powers `survey.deploy(frontend="local")` and
`survey.deploy(frontend="vercel")`.

---

## Client templates

Each backend uses a small JavaScript snippet on the frontend that
registers a transport on `window.SIAMANG_TRANSPORTS` for response
submission and quota checking (legacy `SURVLIB_TRANSPORTS` also supported).

### `ClientEnv`

```python
@dataclass(frozen=True, slots=True)
class ClientEnv:
    survey_id: str
    backend: str
    settings: dict[str, Any]    # frontend-safe (URLs, anon keys, table names)
```

### `BackendClientTemplate`

```python
class BackendClientTemplate:
    name: str
    def render_env_js(self, env: ClientEnv) -> str: ...
```

### `LocalClientTemplate`

Renders `env.js` that POSTs to `/responses` and `/quota-check` on the
local FastAPI server.

### `SupabaseClientTemplate`

Renders `env.js` that:

- POSTs each submission to `responses_{survey_id}` via the Supabase REST
  endpoint using the anon key;
- calls the `quota-check` Edge Function before submission.

---

## Compilation helpers

### `compile_questionnaire(survey, *, options=None) -> SurveySchema`

The function called by `Questionnaire.compile(**options)`.

`options` keys recognised: `language`, `description`, `completion_text`,
`show_progress`, `allow_back`, `one_question_per_page`,
`max_responses`, `quota` (list of `Quota`), `metadata`.

### `compile_expression(expr) -> str | None`

Converts a `None | str | Expression | VarRef` to its SurveyJS string
form. `None` → `None`; `str` is returned unchanged; structured nodes
get `.to_surveyjs()`. Anything else raises `TypeError`.

### `expression_variables(expr) -> set[str]`

Variables referenced by `expr`. Returns an empty set for `None` or
`str`.

### `compile_react_payload(survey, *, ui=None, options=None) -> dict`

Builds the `{ "SURVEY": {...}, "PAGES": [...] }` payload consumed by
the React runtime. Preserves type-specific fields the React components
need (`display`, `points`, `leftLabel`, …) and compiles every
`show_if` / `hide_if` expression into a `{ "deps": [...], "fn": "..." }`
payload. This allows the React runtime to execute the condition as a native
JavaScript function instead of interpreting a JSON AST.

`compile_quota(q: Quota) -> dict` — `{variable, target_value, limit}`,
embedded in the schema.
