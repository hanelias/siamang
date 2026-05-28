# `siamang.deploy` — deployment pipeline reference

The `deploy` subpackage turns a `Questionnaire` into a publicly
reachable URL. It's pluggable: backends and frontends are registered
through Python entry points, and you can ship custom ones in a third-
party package.

```python
from siamang.deploy import (
    DeployPipeline, DeployResult, BackendConfig,
    BackendAdapter, FrontendAdapter,
    backend_factory, frontend_factory,
    list_backends, list_frontends,
)
```

The recommended entry point is `Questionnaire.deploy(...)`, which
takes care of compiling, provisioning, building, and publishing in one
call. Everything below is the machinery.

---

## High-level shape

```
Questionnaire.deploy(
    backend="supabase",          # name → BackendAdapter class via entry points
    frontend="vercel",           # name → FrontendAdapter class via entry points
    backend_kwargs={...},        # passed to the adapter's __init__
    frontend_kwargs={...},
    **options,                   # forwarded to compile_questionnaire
) → DeployResult
```

Internally:

```python
DeployPipeline(
    backend=BackendAdapter(...),
    frontend=FrontendAdapter(...),
    builder=FrontendBuilder(...),
).run(survey, options=options)
```

---

## `BackendAdapter` (abstract base)

```python
class BackendAdapter:
    name: str

    def provision(self, schema: SurveySchema) -> BackendConfig: ...
    def get_responses(self, survey_id: str) -> pd.DataFrame: ...
    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool: ...
```

A backend is responsible for:

- **Provisioning** storage (tables, RLS policies, quota counters) and
  returning a `BackendConfig` whose `settings` are safe to embed in the
  client bundle.
- **Reading back** accumulated responses as a `pandas.DataFrame`.
- **Quota checks** — the frontend calls this before each submission;
  returns `True` if the cell still has capacity.

Subclasses may add behaviour-specific methods (e.g. `LocalBackend.
store_response`, `LocalBackend.increment_quota`).

---

## `BackendConfig`

```python
@dataclass(frozen=True, slots=True)
class BackendConfig:
    backend: str
    survey_id: str
    settings: dict[str, Any] = {}      # frontend-safe (URLs, anon keys)
    internal: dict[str, Any] = {}      # server-only secrets
    dashboard_url: str | None = None   # optional response dashboard URL
```

The boundary between server-only secrets (`internal`) and frontend-safe
config (`settings`). Only `settings` and `dashboard_url` ever cross
into the bundle.

---

## `FrontendAdapter` (abstract base)

```python
class FrontendAdapter:
    name: str

    def publish(self, bundle: SurveyBundle, config: BackendConfig) -> str: ...
```

A frontend receives the compiled `SurveyBundle` and the
`BackendConfig`, deploys the static files somewhere reachable, and
returns the public URL.

---

## Bundled backends

### `LocalBackend`

```python
@dataclass
class LocalBackend(BackendAdapter):
    name: str = "local"
    path: str | Path = "survey.db"     # SQLite file; parent dir auto-created
```

In-process SQLite store. `provision` creates three tables —
`survey_meta`, `responses`, `quota_counters`. Used by `siamang preview`
and `survey.deploy(backend="local")`.

Extra methods on top of the abstract base:

- `store_response(survey_id, payload)` — insert a response, return its
  row id.
- `increment_quota(survey_id, variable, value)` — atomic check-and-
  increment; returns `False` when the cell is full.

### `SupabaseBackend`

```python
@dataclass
class SupabaseBackend(BackendAdapter):
    name: str = "supabase"
    url: str = ""
    anon_key: str = ""
    service_key: str = ""
    table: str = "responses"
    quota_function: str = "quota-check"
    auto_provision: bool = True
```

Credentials fall back to `SIAMANG_SUPABASE_URL`, `SIAMANG_SUPABASE_ANON_KEY`,
`SIAMANG_SUPABASE_SERVICE_KEY` if the kwargs are blank (legacy `SURVLIB_*`
names are also accepted). The constructor raises `ValueError` if any of the
three are still empty.

**Data model:**

- A single shared `responses` table with a `survey_id` column.
- A `survey_meta` table tracking each deployed survey's schema.
- RLS policies: anon can `INSERT`, authenticated can `SELECT`/`DELETE`.
- Quota counters live in `quota_counters`, updated by an Edge Function.

**Provisioning modes:**

1. **Auto** (default, `auto_provision=True`): creates tables via an
   `exec_sql` RPC function. You must create this function once:

   ```sql
   -- Run once in Supabase Dashboard → SQL Editor:
   CREATE OR REPLACE FUNCTION exec_sql(query TEXT)
   RETURNS VOID AS $$
   BEGIN EXECUTE query; END;
   $$ LANGUAGE plpgsql SECURITY DEFINER;
   ```

   If the function is missing, `provision()` raises
   `SupabaseProvisionError` with clear instructions.

2. **Manual** (`auto_provision=False`): skips table creation entirely.
   Generate and run the SQL yourself:

   ```python
   from siamang.deploy.backends.supabase import generate_migration_sql
   print(generate_migration_sql())
   # Copy output → Supabase Dashboard → SQL Editor → Run
   ```

3. **Migration file**: pass `migration_dir="./migrations"` to `provision()`
   to save a timestamped `.sql` file (works with both modes).

Extra method: `get_all_responses(survey_id, page_size=1000)` —
auto-paginates through all responses.

### `GoogleSheetsBackend`

```python
@dataclass(slots=True)
class GoogleSheetsBackend(BackendAdapter):
    name: str = "gsheets"
    credentials_file: str = ""     # path to service account JSON key
    spreadsheet_id: str = ""       # existing spreadsheet (creates new if empty)
    sheet_name: str = "Responses"  # worksheet name for response rows
```

Google Sheets backend — each response becomes a row in a Google Spreadsheet.
Ideal for small-to-medium surveys where you want instant access to data in a
familiar spreadsheet interface, shareable with collaborators without any
infrastructure.

> [!WARNING]
> **Experimental / Security Notice for Browser Deployment:**
> Direct browser-to-Sheets writes require credentials that cannot be safely exposed to the public internet. By default, the `GoogleSheetsClientTemplate` uses a direct `values.append` API call with **no authorization headers**, which only works if the spreadsheet is configured to be publicly writable by anyone (not recommended for production).
>
> For secure public deployments (e.g. Netlify), you **must use an Google Apps Script proxy URL** to act as a secure intermediary. Setting up the Apps Script proxy:
> 1. In your Google Sheet, go to *Extensions* → *Apps Script*.
> 2. Paste a script that receives POST requests and appends them to the sheet.
> 3. Deploy it as a *Web App* configured to execute as "Me" and accessible by "Anyone".
> 4. Pass this URL to your client settings or environment configuration as `apps_script_url`.
>
> Without this proxy, public users will not be able to submit responses unless the spreadsheet is fully public. Thus, the Google Sheets backend is currently considered **experimental** for public web deployments.

**Prerequisites:**

1. Create a Google Cloud project and enable the **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account** and download the JSON key file.
3. (If using an existing spreadsheet) Share the spreadsheet with the service account email (Editor access).

**Environment variables:**

| Variable | Purpose |
| :--- | :--- |
| `SIAMANG_GSHEETS_CREDENTIALS_FILE` | Path to service account JSON key file (required) |
| `SIAMANG_GSHEETS_SPREADSHEET_ID` | Existing spreadsheet ID (optional — creates new if empty) |

Legacy `SURVLIB_GSHEETS_*` prefixes are also accepted.

**Required Python packages:**

```bash
pip install google-auth google-auth-httplib2 google-api-python-client
```

**Data model:**

- **Responses sheet** (`sheet_name`, default "Responses"): first row = headers (variable names), subsequent rows = responses. System columns `_response_id` and `_submitted_at` are prepended automatically.
- **`_meta` sheet**: stores survey metadata (schema JSON, survey_id, deployed_at).
- **`_quotas` sheet**: quota counters with columns `variable`, `value`, `target`, `current`.

**Usage example:**

```python
# Deploy with Google Sheets backend
result = survey.deploy(
    backend="gsheets",
    frontend="netlify",
    backend_kwargs={
        "credentials_file": "./my-project-key.json",
        # spreadsheet_id omitted → creates a new spreadsheet
    },
)
print(result.url)        # https://my-survey.netlify.app
print(result.dashboard)  # https://docs.google.com/spreadsheets/d/...

# Collect responses later
df = result.collect()
data = SurveyData(frame=df, variables=survey.variables)
```

**Methods:**

| Method | Returns | Description |
| :--- | :--- | :--- |
| `provision(schema)` | `BackendConfig` | Creates/configures spreadsheet, writes headers, sets up `_meta` and `_quotas` sheets |
| `store_response(survey_id, payload)` | `str` (response_id) | Appends a response row via `values.append()` |
| `get_responses(survey_id)` | `pd.DataFrame` | Reads all rows, auto-converts numeric columns, replaces empty strings with NaN |
| `check_quota(survey_id, variable, value)` | `bool` | Returns `True` if quota cell has capacity |
| `increment_quota(survey_id, variable, value)` | `bool` | Check + increment; returns `False` when full |
| `get_response_count(survey_id)` | `int` | Number of responses collected |

**Limitations:**

- Google Sheets API has a rate limit of ~100 requests/100 seconds per user. For surveys expecting >50 simultaneous respondents, use Supabase.
- Quota increments are not truly atomic (small race condition window). For strict quota enforcement under high concurrency, use Supabase.
- Maximum 10 million cells per spreadsheet (Google Sheets limit). For surveys with many variables and thousands of respondents, consider Supabase.

---

## Bundled frontends

### `LocalFrontend`

```python
@dataclass
class LocalFrontend(FrontendAdapter):
    name: str = "local"
    host: str = "127.0.0.1"
    port: int = 0                  # 0 → pick a free port
    open_browser: bool = False
```

FastAPI + uvicorn come pre-installed. `publish(...)` starts a background
FastAPI server that serves the bundle and forwards
`POST /responses` and `POST /quota-check` to the backend. The thread
stays alive until you call `local_frontend.stop()` (the CLI's
`siamang preview` blocks the main thread until Ctrl+C and then stops).

### `VercelFrontend`

```python
@dataclass
class VercelFrontend(FrontendAdapter):
    name: str = "vercel"
    token: str = ""                # falls back to VERCEL_TOKEN env var
    team_id: str | None = None
    project_name: str = "siamang-survey"
```

`publish(...)` strategy:

1. If `token` is set, use the Vercel REST API to deploy.
2. Otherwise, if `npx vercel` is available, fall back to the CLI.
3. Otherwise, write the bundle to `.vercel_deploy_<survey_id>/` for
   manual deployment and return that local path.

In all branches it injects a strict `vercel.json`:

- `Content-Security-Policy`,
- `X-Frame-Options: DENY`,
- cache-control headers for hashed assets,
- analytics route when `UIConfig.enable_analytics=True`.

### `NetlifyFrontend`

```python
@dataclass(slots=True)
class NetlifyFrontend(FrontendAdapter):
    name: str = "netlify"
    token: str = ""                # falls back to NETLIFY_AUTH_TOKEN env var
    site_id: str = ""              # existing site ID (creates new if empty)
    site_name: str = "siamang-survey"  # name for new site
```

Netlify frontend adapter — deploys static survey bundles to Netlify's global CDN. Provides instant HTTPS, automatic SSL, and worldwide edge distribution.

**Environment variables:**

| Variable | Purpose |
| :--- | :--- |
| `NETLIFY_AUTH_TOKEN` | Netlify personal access token (required for API deploy) |
| `SIAMANG_NETLIFY_TOKEN` | Legacy alias for the above |

**Deployment modes (automatic fallback):**

1. **REST API** (recommended): ZIP upload to `/api/v1/sites/{id}/deploys` with automatic polling until ready. Requires `token`.
2. **CLI fallback**: uses `npx netlify deploy --prod` when the REST path is unavailable.
3. **Local fallback**: when no token is set, writes the bundle to `.netlify_deploy_<survey_id>/` for manual deployment via Netlify Drop or CLI.

**Security headers** (injected automatically via `_headers` file):

```
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' https://unpkg.com; ...
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

SPA routing is handled via `_redirects` (`/* /index.html 200`).

**Usage example:**

```python
# Deploy to Netlify + Google Sheets
result = survey.deploy(
    backend="gsheets",
    frontend="netlify",
    backend_kwargs={"credentials_file": "./key.json"},
    frontend_kwargs={"token": "nfp_...", "site_name": "my-research-survey"},
)
print(result.url)  # https://my-research-survey.netlify.app
```

**Methods:**

| Method | Returns | Description |
| :--- | :--- | :--- |
| `publish(bundle, config)` | `str` (URL) | Deploy bundle and return public URL |
| `get_deploy_status(deploy_id)` | `dict` | Check status of a specific deploy |
| `list_deploys()` | `list[dict]` | List all deploys for the site |

---

## `DeployPipeline`

```python
@dataclass(frozen=True, slots=True)
class DeployPipeline:
    backend: BackendAdapter
    frontend: FrontendAdapter
    builder: FrontendBuilder

    def run(
        self,
        survey: Questionnaire,
        *,
        options: dict[str, Any] | None = None,
    ) -> DeployResult: ...
```

The orchestrator. `run()`:

1. compiles the questionnaire to a `SurveySchema`;
2. calls `backend.provision(schema)` → `BackendConfig`;
3. selects the matching `BackendClientTemplate` (`LocalClientTemplate`,
   `SupabaseClientTemplate`, or `GoogleSheetsClientTemplate`); raises
   `NotImplementedError` for unknown backend names;
4. calls `builder.build(schema, client=..., env=..., survey=...)` →
   `SurveyBundle`;
5. calls `frontend.publish(bundle, config)` → URL;
6. returns a populated `DeployResult`.

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
    deployed_at: datetime = datetime.now(timezone.utc)
    backend_ref: BackendAdapter | None = None
    frontend_ref: FrontendAdapter | None = None
    extras: dict[str, Any] = {}

    def collect(self) -> pd.DataFrame: ...
```

What you get back from `survey.deploy(...)`. `collect()` re-uses the
cached `backend_ref` to fetch accumulated responses as a DataFrame;
raises `RuntimeError` if the reference is missing (which only happens
when you construct a `DeployResult` by hand).

Typical use:

```python
result = survey.deploy(backend="supabase", frontend="vercel",
                       backend_kwargs={...}, frontend_kwargs={...})
print(result.url, result.dashboard)

# later — the cached backend_ref lets you collect without re-wiring
responses = result.collect()
data = sg.SurveyData(frame=responses, variables=survey.variables,
                     questionnaire=survey)
```

---

## Registry & entry points

```python
list_backends()   → ["local", "supabase", ...]
list_frontends()  → ["local", "vercel", ...]

cls = backend_factory("supabase")        # SupabaseBackend
cls = frontend_factory("vercel")         # VercelFrontend
```

Both functions look up names first in the `siamang.backends` /
`siamang.frontends` Python entry points (so third-party packages can
contribute adapters), then fall back to siamang's built-in registry.

Built-in adapters:

```python
list_backends()   → ["local", "supabase", "gsheets"]
list_frontends()  → ["local", "vercel", "netlify"]
```

**Recommended combinations:**

| Use case | Backend | Frontend |
| :--- | :--- | :--- |
| Local development / testing | `local` | `local` |
| Small survey, shared with team | `gsheets` | `netlify` |
| Production, high concurrency | `supabase` | `vercel` or `netlify` |
| Offline / air-gapped | `local` | `local` (HTML bundle) |

To ship a custom backend, register an entry point under the same
group from your own package and implement `BackendAdapter`. Same for
frontends.
