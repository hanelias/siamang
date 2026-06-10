# CLI Reference

`siamang` ships a single executable, `siamang`, that wraps the public Python API.
Every subcommand loads the questionnaire from a `.py` file, looking for a
module-level attribute named `survey` by default (override with `--attribute`).

```bash
siamang --help
siamang <subcommand> --help
```

You can also run it as a module:

```bash
python -m siamang validate my_survey.py
```

Subcommands: [`validate`](#validate), [`preview`](#preview), [`deploy`](#deploy),
[`init`](#init).

> **The survey file.** Each command imports your `.py` file and reads the attribute
> named by `--attribute` (default `survey`). If the attribute is missing you get an
> `AttributeError` telling you to set `survey = sg.Questionnaire(...)` or pass
> `--attribute NAME`.

---

## `validate`

```bash
siamang validate PATH [--attribute ATTR] [--strict]
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `PATH` | (required) | Path to a Python file exposing a `Questionnaire`. |
| `--attribute` | `survey` | Module-level attribute name to load. |
| `--strict` | off | Pass `strict=True` to `validate()` (also fails on strict-level lint errors). |

Runs `survey.validate(strict=...)` then `survey.lint()` and prints each warning as
`[severity] [code] message (location)`.

**Exit codes:**

| Code | Meaning |
| :--- | :--- |
| 0 | Valid, no `error`-severity lint warnings. |
| 1 | A lint warning had `error` severity. |
| 2 | `validate()` raised a `ValueError` (structural problem). |

```bash
$ siamang validate my_survey.py
OK — no warnings.

$ siamang validate draft_survey.py
[warning] [EMPTY_PAGE] Page 'consent' has no items. (consent)

$ siamang validate draft_survey.py --strict
validation error: Strict questionnaire validation failed: EMPTY_PAGE, CATEGORICAL_WITHOUT_LABELS

$ siamang validate broken_survey.py   # show_if references a typo'd variable
validation error: Page 'demographics' show_if references unknown variables: regon
```

Structural problems — including expressions that reference unknown variables —
surface as a `validation error: …` line with exit code 2, not as lint output.

---

## `preview`

```bash
siamang preview PATH [--attribute ATTR] [--port PORT] [--open] [--db DB]
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `PATH` | (required) | Path to the questionnaire `.py` file. |
| `--attribute` | `survey` | Module-level attribute name. |
| `--port` | `8000` | Bind port for the local server. |
| `--open` | off | Open the survey in the default browser on startup. |
| `--db` | `survey.db` | SQLite file used by the local backend. |

Spins up a local FastAPI server with the React frontend and the SQLite backend
(`LocalBackend` + `LocalFrontend`). The survey is reachable at
`http://127.0.0.1:<port>`; responses land in `--db`. Press Ctrl+C to stop. The
command also prints a one-line diagnostic about the React compile path (sucrase +
esbuild fast path, vs. in-browser `@babel/standalone`).

```bash
$ siamang preview my_survey.py --port 8000 --open
Preview ready at http://127.0.0.1:8000
  survey_id: 42a1c0e9
  dashboard: None
  [react] sucrase + esbuild minify available — fast path
Press Ctrl+C to stop.
```

Read the collected responses from Python afterwards:

```python
from siamang.deploy.backends.local import LocalBackend

df = LocalBackend(path="survey.db").get_responses(survey_id="42a1c0e9")
```

---

## `deploy`

```bash
siamang deploy PATH [--attribute ATTR]
                    [--backend NAME] [--frontend NAME]
                    [--profile PROFILE] [--config PATH]
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `PATH` | (required) | Path to the questionnaire `.py` file. |
| `--attribute` | `survey` | Module-level attribute name. |
| `--backend` | from config | Backend name (see `list_backends()`). |
| `--frontend` | from config | Frontend name (see `list_frontends()`). |
| `--profile` | (current config) | Selects a `[profiles.<name>]` block. |
| `--config` | `~/.siamang.toml` (already loaded) | Override the config path. |

Resolution order: load `--config` if given (else use the already-active config);
apply `--profile` if given; then pick the backend/frontend from `--backend` /
`--frontend`, falling back to the profile's defaults (`local`/`local` if unset).
Adapter kwargs come from the matching `[backends.<name>]` / `[frontends.<name>]`
config blocks (the `local` backend/frontend take no kwargs). See [[Configuration]]
for the file format and environment overrides.

```bash
$ siamang deploy my_survey.py --profile production
Deployed: https://political-trust-2026.vercel.app
  survey_id: 42a1c0e9
  backend:   supabase
  frontend:  vercel
  dashboard: https://app.supabase.com/project/abcdef
```

You can override the configured backend/frontend on the command line:

```bash
siamang deploy my_survey.py --backend supabase --frontend netlify
```

---

## `init`

```bash
siamang init [--path PATH] [--non-interactive]
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--path` | `~/.siamang.toml` | Where to write the config. |
| `--non-interactive` | off | Write defaults (`backend="local"`, `frontend="local"`) and skip prompts. |

Interactive walkthrough that asks for the default backend/frontend and, when you
pick `supabase` / `vercel`, their credentials (secrets are read with `getpass`).
The config is written and `chmod 600` is applied.

```bash
$ siamang init
siamang init — interactive setup
Target: /home/you/.siamang.toml
Default backend (local/supabase) [local]: supabase
Default frontend (local/vercel) [local]: vercel
Supabase URL: https://abcdef.supabase.co
Supabase anon_key:
Supabase service_key:
Vercel token:
Vercel team_id (optional):

Wrote /home/you/.siamang.toml (chmod 600 applied).
```

Non-interactive (handy for CI / scaffolding):

```bash
$ siamang init --non-interactive
Wrote /home/you/.siamang.toml (defaults: local/local).
```

---

See also: [[Configuration]] · [[Deployment]] ·
[[Validation and Linting|Validation-and-Linting]] ·
[[Frontend and Theming|Frontend-and-Theming]] ·
[[API Reference Index|API-Reference-Index]]
