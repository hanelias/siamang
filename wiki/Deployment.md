# Deployment

The `siamang.deploy` subpackage turns a `Questionnaire` into a publicly reachable
URL. It is pluggable: **backends** (where responses are stored) and **frontends**
(where the static survey is hosted) are resolved by name through Python entry
points, so third-party packages can ship their own. The recommended entry point is
`Questionnaire.deploy(...)`, which compiles, provisions, builds, and publishes in
one call.

```python
from siamang.deploy import (
    DeployPipeline, DeployResult, BackendConfig,
    BackendAdapter, FrontendAdapter,
    backend_factory, frontend_factory,
    list_backends, list_frontends,
)
```

---

## `Questionnaire.deploy(...)`

```python
result = survey.deploy(
    backend="supabase",          # name → BackendAdapter via entry points
    frontend="vercel",           # name → FrontendAdapter via entry points
    backend_kwargs={...},        # forwarded to the backend adapter's __init__
    frontend_kwargs={...},       # forwarded to the frontend adapter's __init__
    **options,                   # ui=..., quota=..., language=... → compile_questionnaire
)  # -> DeployResult
```

`backend` defaults to `"local"` and `frontend` to `"local"`, so a bare
`survey.deploy()` writes a local SQLite store and serves it from a background
FastAPI server. `**options` are forwarded to compilation — common ones are
`ui=UIConfig(...)` (see [[Frontend and Theming|Frontend-and-Theming]]),
`quota=[...]` (see [[Quotas]]), and `language=`.

```python
import siamang as sg

result = survey.deploy(
    backend="supabase", frontend="vercel",
    backend_kwargs={"url": "https://abc.supabase.co", "anon_key": "...", "service_key": "..."},
    frontend_kwargs={"token": "...", "project_name": "political-trust-2026"},
)
print(result.url, result.dashboard)
df = result.collect()   # pull accumulated responses later
```

---

## Backends

A `BackendAdapter` provisions storage, reads responses, and answers quota checks.

```python
class BackendAdapter:
    name: str
    def provision(self, schema: SurveySchema) -> BackendConfig: ...
    def get_responses(self, survey_id: str) -> pd.DataFrame: ...
    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool: ...
```

| Backend | `name` | Storage | Key kwargs |
| :--- | :--- | :--- | :--- |
| `LocalBackend` | `local` | SQLite file | `path="survey.db"` |
| `SupabaseBackend` | `supabase` | Postgres + RLS | `url`, `anon_key`, `service_key`, `auto_provision=True` |
| `GoogleSheetsBackend` | `gsheets` | Google Spreadsheet | `credentials_file`, `spreadsheet_id`, `apps_script_url` |

### Capabilities

| Capability | local | supabase | gsheets |
| :--- | :---: | :---: | :---: |
| Zero external setup | ✅ | ❌ | ❌ |
| Public web submissions | ❌ (preview only) | ✅ | ⚠️ (needs Apps Script proxy) |
| Atomic quota counters | ✅ | ✅ | ⚠️ (small race window) |
| High concurrency | ❌ | ✅ | ❌ (~100 req/100s) |
| Response dashboard | ❌ | ✅ | ✅ (the spreadsheet) |

- **`LocalBackend`** creates three tables — `survey_meta`, `responses`,
  `quota_counters` — and adds `store_response(...)` and `increment_quota(...)`.
  It backs `siamang preview`.
- **`SupabaseBackend`** uses a single shared `responses` table keyed by
  `survey_id`. Credentials fall back to `SIAMANG_SUPABASE_URL` /
  `SIAMANG_SUPABASE_ANON_KEY` / `SIAMANG_SUPABASE_SERVICE_KEY` (legacy `SURVLIB_*`
  also accepted); the constructor raises `ValueError` if any are still empty. With
  `auto_provision=True` it creates tables via an `exec_sql` RPC you set up once;
  otherwise generate SQL with
  `siamang.deploy.backends.supabase.generate_migration_sql()`.
- **`GoogleSheetsBackend`** writes one row per response. It needs the optional
  `gsheets` extra (`pip install "siamang[gsheets]"`). For public deployments you
  **must** route submissions through an Apps Script proxy (`apps_script_url`) — see
  the security note in
  [`docs/reference/deploy.md`](https://github.com/hanelias/siamang/blob/main/docs/reference/deploy.md).

---

## `BackendConfig`

```python
@dataclass(frozen=True, slots=True)
class BackendConfig:
    backend: str
    survey_id: str
    settings: dict[str, Any] = {}      # frontend-safe (URLs, anon keys)
    internal: dict[str, Any] = {}      # server-only secrets
    dashboard_url: str | None = None
```

Returned by `provision()`. It draws the boundary between server-only secrets
(`internal`) and frontend-safe values (`settings`). Only `settings` and
`dashboard_url` ever cross into the deployed bundle.

---

## Frontends

A `FrontendAdapter` receives the compiled bundle and the `BackendConfig`, hosts the
static files, and returns the public URL.

```python
class FrontendAdapter:
    name: str
    def publish(self, bundle: SurveyBundle, config: BackendConfig) -> str: ...
```

| Frontend | `name` | Host | Key kwargs |
| :--- | :--- | :--- | :--- |
| `LocalFrontend` | `local` | Background FastAPI server | `host`, `port=0`, `open_browser` |
| `VercelFrontend` | `vercel` | Vercel | `token`, `team_id`, `project_name` |
| `NetlifyFrontend` | `netlify` | Netlify CDN | `token`, `site_id`, `site_name` |

- **`LocalFrontend`** serves the bundle and forwards `POST /responses` and
  `POST /quota-check` to the backend. Stop it with `local_frontend.stop()`;
  `siamang preview` blocks until Ctrl+C.
- **`VercelFrontend`** deploys via the Vercel REST API when `token` is set (falls
  back to `VERCEL_TOKEN`), else `npx vercel`, else writes
  `.vercel_deploy_<survey_id>/` for manual upload. It injects a strict `vercel.json`
  (CSP, `X-Frame-Options: DENY`, asset caching, analytics route when
  `UIConfig.enable_analytics=True`).
- **`NetlifyFrontend`** ZIP-uploads via the REST API when `token` is set (falls
  back to `NETLIFY_AUTH_TOKEN`, then `npx netlify deploy --prod`, then a local
  write). It injects security headers via `_headers` and SPA routing via
  `_redirects`. Extra methods: `get_deploy_status(deploy_id)`, `list_deploys()`.

### Recommended combinations

| Use case | Backend | Frontend |
| :--- | :--- | :--- |
| Local development / testing | `local` | `local` |
| Small survey, shared with a team | `gsheets` | `netlify` |
| Production, high concurrency | `supabase` | `vercel` or `netlify` |
| Offline / air-gapped (HTML bundle) | `local` | `local` |

---

## `DeployResult`

```python
@dataclass(frozen=True, slots=True)
class DeployResult:
    url: str
    backend: str
    frontend: str
    survey_id: str = ""
    dashboard: str | None = None
    deployed_at: datetime = ...
    backend_ref: BackendAdapter | None = None
    frontend_ref: FrontendAdapter | None = None
    extras: dict[str, Any] = {}

    def collect(self) -> pd.DataFrame: ...
```

What `survey.deploy(...)` returns. `collect()` reuses the cached `backend_ref` to
fetch accumulated responses as a DataFrame; it raises `RuntimeError` if the
reference is missing (which only happens for a hand-built `DeployResult`).

```python
responses = result.collect()
data = sg.SurveyData(frame=responses, variables=survey.variables, questionnaire=survey)
print(data.report.freq("trust").to_markdown())
```

---

## Registry and factories

```python
from siamang.deploy import list_backends, list_frontends, backend_factory, frontend_factory

list_backends()    # ['gsheets', 'local', 'supabase']
list_frontends()   # ['local', 'netlify', 'vercel']

backend_factory("supabase")   # <class 'SupabaseBackend'>
frontend_factory("netlify")   # <class 'NetlifyFrontend'>
```

`backend_factory`/`frontend_factory` look up names in the `siamang.backends` /
`siamang.frontends` entry-point groups first (so plugins win), then fall back to the
built-in registry. From `tests/test_adapters.py`, backends/frontends initialise
straight from environment variables:

```python
import os
os.environ["SIAMANG_GSHEETS_CREDENTIALS_FILE"] = "/path/creds.json"
os.environ["SIAMANG_GSHEETS_SPREADSHEET_ID"] = "sheet_123"

backend = backend_factory("gsheets")()       # picks up both env vars
assert backend.credentials_file == "/path/creds.json"

os.environ["NETLIFY_AUTH_TOKEN"] = "nfp_..."
frontend = frontend_factory("netlify")()
assert frontend.token == "nfp_..."
```

---

## `DeployPipeline` — the orchestrator

```python
@dataclass(frozen=True, slots=True)
class DeployPipeline:
    backend: BackendAdapter
    frontend: FrontendAdapter
    builder: FrontendBuilder

    def run(self, survey: Questionnaire, *, options: dict | None = None) -> DeployResult: ...
```

`Questionnaire.deploy(...)` builds this for you, but you can wire it directly. `run()`:

1. compiles the questionnaire to a `SurveySchema`;
2. `backend.provision(schema)` → `BackendConfig`;
3. selects the matching client template (`LocalClientTemplate`,
   `SupabaseClientTemplate`, or `GoogleSheetsClientTemplate`); an unknown backend
   name raises `NotImplementedError`;
4. `builder.build(schema, client=..., env=..., survey=...)` → `SurveyBundle`;
5. `frontend.publish(bundle, config)` → URL;
6. returns a populated `DeployResult`.

```python
from siamang.deploy import DeployPipeline
from siamang.deploy.backends.local import LocalBackend
from siamang.deploy.frontends.local import LocalFrontend
from siamang.frontend import FrontendBuilder

pipeline = DeployPipeline(
    backend=LocalBackend(path="survey.db"),
    frontend=LocalFrontend(port=8000),
    builder=FrontendBuilder(),
)
result = pipeline.run(survey)
```

---

## Writing a custom adapter

Both adapter groups are entry points, so a plugin only declares them and implements
the abstract base. Custom backend:

```python
# my_pkg/backend.py
import pandas as pd
from siamang.deploy import BackendAdapter, BackendConfig

class MyBackend(BackendAdapter):
    name = "mybackend"

    def __init__(self, token: str = ""):
        self.token = token

    def provision(self, schema) -> BackendConfig:
        survey_id = ...  # create remote storage, return an id
        return BackendConfig(
            backend=self.name, survey_id=survey_id,
            settings={"ingest_url": "https://api.example.com/ingest"},  # frontend-safe
            internal={"token": self.token},                              # never bundled
            dashboard_url="https://app.example.com/dashboards/...",
        )

    def get_responses(self, survey_id: str) -> pd.DataFrame: ...
    def check_quota(self, survey_id: str, variable, value) -> bool: ...
```

Custom frontend:

```python
# my_pkg/frontend.py
from siamang.deploy import FrontendAdapter

class MyCDNFrontend(FrontendAdapter):
    name = "mycdn"
    def publish(self, bundle, config) -> str:
        bundle.write_to("/tmp/out")          # or bundle.to_zip()
        return "https://surveys.example.com/abc"
```

Register them, then deploy by name:

```toml
# my-siamang-plugin/pyproject.toml
[project.entry-points."siamang.backends"]
mybackend = "my_pkg.backend:MyBackend"

[project.entry-points."siamang.frontends"]
mycdn = "my_pkg.frontend:MyCDNFrontend"
```

```python
survey.deploy(backend="mybackend", frontend="mycdn",
              backend_kwargs={"token": "..."})
```

> Note: the bundled `DeployPipeline` resolves client templates for the three
> built-in backend names only. A fully custom backend additionally needs a matching
> `BackendClientTemplate` so the frontend knows how to submit; see
> [[Frontend and Theming|Frontend-and-Theming]].

---

See also: [[Configuration]] · [[CLI Reference|CLI-Reference]] ·
[[Frontend and Theming|Frontend-and-Theming]] · [[Quotas]] ·
[[API Reference Index|API-Reference-Index]]
