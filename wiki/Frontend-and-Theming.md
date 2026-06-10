# Frontend and Theming

The `siamang.frontend` subpackage compiles a `Questionnaire` into a deployable
static bundle — HTML, CSS, JavaScript, and runtime config. Most of the time you
never touch it directly: `survey.deploy(...)` and `siamang preview` drive it for
you. This page documents the machinery so you can build bundles by hand, swap
runtimes, and fully control the visual design with `UIConfig` and theme presets.

```python
from siamang.frontend import (
    FrontendBuilder, UIConfig, get_preset, compile_css, compile_questionnaire,
    SurveySchema, SurveyBundle,
    SurveyJSRuntime, ReactRuntime,
    LocalClientTemplate, SupabaseClientTemplate, ClientEnv,
)
```

The pipeline is a small composition: **compile** a questionnaire to a
`SurveySchema`, hand that to a `FrontendBuilder` (which carries a `RuntimeAdapter`
and a `UIConfig`), and `build(...)` it with a backend `client` and a `ClientEnv`
into a `SurveyBundle`.

---

## `SurveySchema` — the intermediate representation

```python
from siamang.frontend import SurveySchema, compile_questionnaire

schema = compile_questionnaire(survey, options={"language": "en"})
```

`SurveySchema` is a frozen, platform-agnostic snapshot of a survey. It is produced
by `compile_questionnaire(survey, options=...)`; backends, runtimes, and themes all
consume it. Fields include `title`, `pages`, `variables`, `language`,
`description`, `completion_text`, `show_progress`, `allow_back`,
`one_question_per_page`, `deadline`, `max_responses`, `quotas`, and `metadata`.

Two render methods:

```python
schema.to_surveyjs()   # dict — SurveyJS-compatible payload (title/locale/pages/...)
schema.to_dict()       # dict — full JSON serialisation (format_version=1, ISO deadlines)
```

`to_surveyjs()` maps siamang concepts onto the SurveyJS dialect — e.g.
`show_progress` becomes `showProgressBar: "top"`, and `one_question_per_page`
becomes `questionsOnPageMode: "questionPerPage"`. Internal keys (`_quota_variable`,
`_meta`) are stripped from each page first.

---

## `FrontendBuilder` — the orchestrator

```python
from siamang.frontend import FrontendBuilder, SurveyJSRuntime, UIConfig

builder = FrontendBuilder(runtime=SurveyJSRuntime(), ui=UIConfig())

def build(
    self,
    schema: SurveySchema,
    *,
    client: BackendClientTemplate,
    env: ClientEnv,
    survey: Questionnaire | None = None,
) -> SurveyBundle: ...
```

Both constructor fields are optional and default to `SurveyJSRuntime()` and
`UIConfig()`. `build(...)` renders every artefact and returns an assembled bundle
whose filenames are content-hashed. `survey` is only needed by runtimes that
require the live `Questionnaire` (`ReactRuntime`); `SurveyJSRuntime` works from
`schema` alone.

The returned bundle contains:

| File | Purpose |
| :--- | :--- |
| `index.html` | The survey entry point. |
| `closed.html` | Shown when the survey has expired, hit `max_responses`, or quotas are full. |
| `style.css` | The compiled theme (from the runtime, or `compile_css(ui)` as a fallback). |
| `env.js` | Runtime config emitted by the backend client template. |
| `manifest.json` | Metadata: runtime, client, backend, `survey_id`, `schema_hash`, build time. |

### End-to-end example

```python
import siamang as sg
from siamang.frontend import (
    FrontendBuilder, UIConfig, LocalClientTemplate, ClientEnv, compile_questionnaire,
)

survey = sg.Questionnaire(title="Demo", pages=[...])

schema = compile_questionnaire(survey, options={"language": "en"})
builder = FrontendBuilder(ui=UIConfig(primary_color="#2c5f8a"))
env = ClientEnv(survey_id="abc123", backend="local", settings={})

bundle = builder.build(schema, client=LocalClientTemplate(), env=env)
bundle.write_to("./dist")          # writes index.html, style.css, env.js, ...
```

---

## `SurveyBundle`

```python
@dataclass(frozen=True, slots=True)
class SurveyBundle:
    files: dict[str, str | bytes]   # {relative_path: content}
    manifest: dict[str, Any]
```

Immutable container of the compiled files plus a manifest. Useful methods:

| Method | Returns | Description |
| :--- | :--- | :--- |
| `write_to(target)` | `Path` | Write every file under `target`, creating parents. |
| `to_zip()` | `bytes` | Deflate-compressed ZIP of all files. |
| `manifest_json()` | `str` | Pretty-printed manifest JSON. |
| `compute_digest()` | `str` | 16-char SHA-256 prefix over all contents. |
| `with_hashed_filenames()` | `SurveyBundle` | Renames `.js`/`.css` to include a content hash (HTML references updated). |

`FrontendBuilder.build(...)` already calls `with_hashed_filenames()` for you.

---

## Runtimes

A `RuntimeAdapter` turns a compiled schema into HTML pages and the client-side
behaviour. Two are bundled:

### `SurveyJSRuntime` (default)

A lightweight, non-React runtime built on the **SurveyJS** core library. It is the
default because it is highly compatible and needs zero build tooling. This is what
the full-pipeline example uses to produce a standalone `.html` file.

### `ReactRuntime`

Compiles the questionnaire into a standalone **React 18** application with a
bundled design-system stylesheet.
Required for advanced interactive features (custom charts, custom widgets, complex
animations). Because it needs the live questionnaire, pass `survey=` to `build(...)`.
`siamang preview` uses the React runtime locally.

Both inherit the `RuntimeAdapter` interface (`render_html`, `render_closed_page`,
`stylesheet`, `static_assets`) — see
[`docs/reference/frontend.md`](https://github.com/hanelias/siamang/blob/main/docs/reference/frontend.md).

---

## Backend client templates

A `BackendClientTemplate` emits the `env.js` snippet that wires the in-browser
client to a backend. It registers a transport on `window.SIAMANG_TRANSPORTS` keyed
by `ClientEnv.backend` and sets `window.SIAMANG_ENV`.

```python
from siamang.frontend import ClientEnv, LocalClientTemplate, SupabaseClientTemplate
from siamang.frontend.client import GoogleSheetsClientTemplate

env = ClientEnv(survey_id="abc", backend="supabase", settings={"url": "...", "anon_key": "..."})
```

| Template | `backend` name | Notes |
| :--- | :--- | :--- |
| `LocalClientTemplate` | `local` | POSTs to the local FastAPI server (`/responses`, `/quota-check`). |
| `SupabaseClientTemplate` | `supabase` | POSTs `{survey_id, data}` to the shared `responses` table. |
| `GoogleSheetsClientTemplate` | `gsheets` | Submits via `values.append` or an Apps Script proxy URL. |

`ClientEnv` carries only **frontend-safe** values (URLs, anon keys). Secrets such as
service keys never reach the bundle. The `DeployPipeline` selects the matching
template for you based on the backend name (see [[Deployment]]).

---

## `UIConfig` — the design system

`UIConfig` is a frozen dataclass (~66 fields) that controls the entire look of the
deployed survey. The defaults aim for a calm, research-grade aesthetic: a serif body
font, a narrow line measure, a single accent colour, and comfortable spacing. Pass
it to deployment via `survey.deploy(..., ui=UIConfig(...))` or to a
`FrontendBuilder`. The fields group into seven areas.

### Palette

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `primary_color` | `"#2c5f8a"` | Brand colour for primary buttons and active states. |
| `accent_color` | `None` | Optional accent; falls back to `primary_color`. |
| `background_color` | `"#fbfbfb"` | Page background. |
| `surface_color` | `"#ffffff"` | Card / panel / input background. |
| `text_color` | `"#1a1a1a"` | Body text. |
| `muted_text_color` | `"#5a5a5a"` | Secondary text. |
| `border_color` | `"#e6e4df"` | Dividers and input borders. |
| `error_color` / `error_soft_color` | `"#b3261e"` / `"#fdf1f0"` | Validation error text and tint. |
| `warn_color` | `"#9a6a1a"` | Warning states. |

### Typography

`font_preset` is the high-level knob: `"academic"` (Source Serif 4 body + Inter UI,
the default), `"modern"` (Inter everywhere), or `"humanist"` (Nunito). Each preset
ships its own Google Fonts URL. Fine-grained overrides: `font_family`,
`heading_font_family`, `ui_font_family`, `mono_font_family`, `font_size`
(`"15.5px"`), `line_height` (`"1.6"`), and `font_pair` (`"serif"` | `"sans"` |
`"mixed"`).

### Layout

`width` (`"700px"` — kept under ~750px for a 60–75 character measure), `radius`
(`"4px"`), `density` (`"compact"` | `"comfortable"` | `"spacious"`), and
`question_style` (`"plain"` | `"divided"` | `"carded"` | `"accent"`).

### Branding / header

`logo_url`, `logo_text` (auto-derived from `institution_name` initials if unset),
`logo_position`, `show_title`, `institution_name`, `study_subtitle`,
`show_section_numbers`, `show_progress_text`, and `estimated_minutes`.

### Footer

`privacy_url`, `contact_email`, and `ethics_statement` (e.g. an IRB reference).

### I18n UI strings

Twenty optional override fields translate the built-in chrome, all defaulting to
English: `next_button_text`, `prev_button_text`, `submit_button_text`,
`submitting_text`, `required_text`, `saving_text`, `select_placeholder`, `of_text`,
`selected_text`, `resume_title`, `resume_action`, `restart_action`, `page_text`,
`of_total_text`, `retry_title`, `retry_body`, `retry_action`, `save_local_action`,
`completion_title`, and `completion_body`.

### Advanced (navigation, access, analytics)

`progress_style` (`"bar"` | `"dots"` | `"both"`), `default_theme` (`"light"` |
`"dark"` | `"system"`), `redirect_url`, `allow_back`, `enable_analytics` (injects
Vercel Analytics when `frontend="vercel"`), and an access gate:
`require_access_code`, `access_codes`, `access_title`, `access_body`,
`access_placeholder`, `access_button`. `custom_css` is a raw escape hatch appended
to the compiled stylesheet.

> `UIConfig.__post_init__` validates `logo_position`, `density`, `font_pair`,
> `question_style`, and `font_preset`; an unknown value raises `ValueError`.

---

## Theme presets

`get_preset(name)` returns a fully configured `UIConfig`. Six presets ship in
`THEME_PRESETS`:

```python
from siamang.frontend import get_preset

ui = get_preset("dark")
```

| Name | Typography | Look | Best for |
| :--- | :--- | :--- | :--- |
| `default` | academic | Serif, light grey background. | Standard academic studies. |
| `academic` | academic | Explicit academic styling (680px width). | Alias of `default`. |
| `dark` | academic | Dark slate (`#10131a`), blue accents. | Night reading, tech studies. |
| `modern` | modern | White, indigo accents, spacious, 16px. | Public-facing / consumer surveys. |
| `humanist` | humanist | Warm off-white, green accents, rounded. | Community / non-profit research. |
| `high_contrast` | modern | Black/white, bold borders, 18px text. | WCAG AAA accessibility. |

An unknown name raises `KeyError` listing the valid options.

### Example: start from a preset and customise

```python
import dataclasses
from siamang.frontend import get_preset

ui = dataclasses.replace(
    get_preset("modern"),
    institution_name="Independent Polling Lab",
    primary_color="#a8324b",
    estimated_minutes=8,
    # translate the navigation chrome to French
    next_button_text="Suivant",
    prev_button_text="Précédent",
    submit_button_text="Envoyer",
)

survey.deploy(backend="supabase", frontend="vercel", ui=ui)
```

`UIConfig` is frozen, so use `dataclasses.replace(...)` to derive a variant from a
preset.

---

## `compile_css`

```python
from siamang.frontend import compile_css

css: str = compile_css(ui)
```

Compiles a `UIConfig` into a CSS stylesheet string using CSS custom properties. This
is the fallback `style.css` when a runtime does not supply its own (the React
runtime ships a full design system). Useful for inspecting the generated theme or
embedding it elsewhere.

---

See also: [[Deployment]] · [[CLI Reference|CLI-Reference]] · [[Cookbook]] ·
[[API Reference Index|API-Reference-Index]]
