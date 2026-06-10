# Contributing

Thanks for helping improve siamang. This page covers the development setup, the
test and lint commands, the project layout, and where to record changes. siamang
targets **Python ≥ 3.11** and is MIT licensed.

---

## Clone and install

Install in editable mode with the `dev` extra, which pulls in the test, lint, and
type-checking tools (and the `charts` extra it depends on):

```bash
git clone https://github.com/hanelias/siamang.git
cd siamang
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

The `dev` extra resolves to `ruff`, `mypy`, `pytest`, and `siamang[charts]`
(matplotlib + seaborn). Optional extras you may also want:

| Extra | Adds | For |
| :--- | :--- | :--- |
| `charts` | matplotlib, seaborn | `data.plot.*` visualisations |
| `gsheets` | google-auth, google-api-python-client | the Google Sheets backend |

```bash
pip install -e ".[dev,gsheets]"     # everything for full development
```

The core dependencies (pandas, fastapi, uvicorn, openpyxl, pyreadstat, scipy,
supabase, requests, tabulate, markdown) are installed unconditionally, so SPSS/Stata
I/O and the local preview server work out of the box.

---

## Run the checks

The CI gate is four commands. Run them before opening a pull request:

```bash
pytest                       # test suite (configured to discover ./tests)
ruff check .                 # lint
ruff format --check .        # formatting (no changes applied)
mypy siamang                 # static type checking
```

To auto-fix formatting and lint issues locally:

```bash
ruff format .                # apply formatting
ruff check . --fix           # apply safe lint fixes
```

### Tooling configuration (`pyproject.toml`)

The behaviour of these tools is pinned in `[tool.*]` blocks:

- **`[tool.ruff]`** — `target-version = "py311"`, `line-length = 100`.
- **`[tool.ruff.lint]`** — rule sets `E, F, W, I, UP, B, SIM`; ignores `E501`
  (line length, handled by the formatter), `B008` (function calls in dataclass
  defaults), and `SIM108` (ternaries). First-party imports are `siamang`.
- **`[tool.mypy]`** — `python_version = "3.11"`, `warn_return_any`,
  `warn_unused_configs`, `ignore_missing_imports`. Typing is **gradual**
  (`disallow_untyped_defs = false`), so untyped functions are tolerated for now but
  new code should be typed.
- **`[tool.pytest.ini_options]`** — `testpaths = ["tests"]`, test files match
  `test_*.py`.

siamang ships a `py.typed` marker, so it is a typed package for downstream users —
keep public signatures annotated.

---

## Project layout

```
siamang/
├── siamang/                 # the package
│   ├── __init__.py          # the public API surface (see API Reference Index)
│   ├── __main__.py          # enables `python -m siamang`
│   ├── local_simulator.py   # synthetic-respondent generator
│   ├── core/                # variables, questions, pages, expressions, validation
│   ├── data/                # SurveyData, banner & summary tables
│   ├── reporting/           # declarative tables, charts, Report document
│   ├── frontend/            # compile → schema → bundle; runtimes, theme, clients
│   ├── deploy/              # pipeline, registry, backends/, frontends/
│   ├── io/                  # CSV/Excel/SPSS/Stata/R readers & writers
│   ├── cli/                 # argparse entry point + subcommands
│   └── config/              # ~/.siamang.toml loader, profiles, secret hardening
├── tests/                   # pytest suite
├── examples/full_pipeline/  # the worked end-to-end example (notebook + assets)
├── docs/                    # reference docs and cookbook (source for parts of this wiki)
├── wiki/                    # this GitHub Wiki (source of truth)
├── pyproject.toml           # build config + tool settings + entry points
├── MANUAL.md                # the narrative manual with examples
└── CHANGELOG.md             # release notes
```

The layered structure mirrors the [[API Reference Index|API-Reference-Index]]:
core → data → reporting → frontend → deploy → io → config.

---

## How the test suite is organised

Tests live under `tests/` and are discovered by `pytest` via `testpaths`. Each file
groups related behaviour:

| File | Covers |
| :--- | :--- |
| `tests/test_pages.py` | Page structure, navigation, and visibility. |
| `tests/test_report.py` · `tests/test_reporting.py` | Declarative tables and charts. |
| `tests/test_adapters.py` | Deploy registry, backends, and frontends (using mocks). |

Tests use `unittest.mock` to avoid hitting real APIs — e.g. `test_adapters.py` mocks
the Google Sheets and Netlify clients so the suite needs no credentials. Follow that
pattern when adding tests for network-bound code. Files are also runnable directly
(`python tests/test_adapters.py`) for a quick standalone check.

Add new tests in a `test_*.py` file matching the area you are changing, and keep them
deterministic (`simulate(..., seed=...)` for data-dependent assertions).

---

## Backends, frontends, and the entry-point registry

Deploy adapters are registered as entry points in `pyproject.toml`:

```toml
[project.entry-points."siamang.backends"]
local    = "siamang.deploy.backends.local:LocalBackend"
supabase = "siamang.deploy.backends.supabase:SupabaseBackend"
gsheets  = "siamang.deploy.backends.gsheets:GoogleSheetsBackend"

[project.entry-points."siamang.frontends"]
local   = "siamang.deploy.frontends.local:LocalFrontend"
vercel  = "siamang.deploy.frontends.vercel:VercelFrontend"
netlify = "siamang.deploy.frontends.netlify:NetlifyFrontend"
```

A new built-in adapter implements the abstract base in `siamang/deploy/base.py` and
adds an entry point here. Third-party plugins do the same from their own package —
see [[Deployment]] for the full contract.

---

## Pull requests

- Branch off the default branch; do not commit directly to it.
- Keep changes focused, with tests for new behaviour.
- Ensure `pytest`, `ruff check .`, `ruff format --check .`, and `mypy siamang` all
  pass.
- Record user-facing changes in `CHANGELOG.md` under an *Unreleased* heading — the
  project follows [Keep a Changelog](https://keepachangelog.com/) and Semantic
  Versioning (the current release is `0.5.0`).

---

See also: [[API Reference Index|API-Reference-Index]] · [[CLI Reference|CLI-Reference]] ·
[[Deployment]] · [[Installation]]
