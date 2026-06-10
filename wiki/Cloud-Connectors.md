# Cloud Connectors

Connectors let a project export (or import) its tables to external data targets —
object storage, data warehouses, Google Sheets, or a customer's own SQL database.
They are a **Pro / Corporate** feature (`FEATURE_CONNECTORS`, which also gates Git
mirrors).

In the current product connectors are **availability-only**: the catalog,
declarative config, validation, API, and UI are all built and tested, but live
data transfer is intentionally deferred. An adapter only *defines* a target and
*validates* its config — there is no transfer logic and no simulation. Real I/O
lands in the final Service Integration stage.

See also: [[Cloud Subscription Tiers|Cloud-Subscription-Tiers]] ·
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]] ·
[[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]].

---

## The connector catalog

The built-in targets are registered in `worker/app/connectors/adapters.py`. Each
adapter declares a `target` key and a `validate(spec)` that raises `ValueError` on
bad config or a missing secret.

| Target key | Connector | Required config | Secret |
| :--- | :--- | :--- | :--- |
| `s3` | Amazon S3 / Cloudflare R2 / MinIO object storage | `bucket`, `key` | optional |
| `gcs` | Google Cloud Storage | `bucket`, `key` | required (service-account JSON) |
| `azure` | Azure Blob Storage | `container`, `path` | required (connection string / SAS) |
| `database` | Bring-your-own SQL DB via DSN (Postgres/MySQL), out or in | — | required (DSN) — or a `dsn` in config |
| `sheets` | Export a table to a Google Sheet | `spreadsheet_id` | required (service-account JSON) |
| `bigquery` | Sync a table to Google BigQuery | `dataset`, `table` | required (service-account JSON) |
| `snowflake` | Sync a table to Snowflake | `database`, `schema`, `table` | required (connection params) |

Every adapter also validates the `table` identifier (`safe_identifier`, matching
`^[A-Za-z_][A-Za-z0-9_]{0,62}$`) before it would ever be used.

---

## The "availability only" model

The connector framework core (`worker/app/connectors/base.py`) is deliberately
pure — no network, no heavy SDKs, no execution. It defines:

- `ConnectorSpec` — a connector task declared in a project's `siamang.yaml`:
  `name`, `target` (registry key), `direction` (`out` | `in`), `table`,
  `secret_key`, and a free-form `config` dict.
- `ConnectorAdapter` — a `Protocol` with a `target` and a `validate(spec)` method.
  Adapters do **not** execute transfers in the prototype.
- A registry (`register` / `get_adapter` / `known_targets`).

There is no `perform` / run method anywhere in the framework. Connectors are
*available to configure*; the data transfer itself is the part wired in later.

---

## Declaring a connector

Connectors are declared as tasks of `type: connector` in the project's
`siamang.yaml` and committed with the repo. The API reads them from that file:

```yaml
tasks:
  export_to_warehouse:
    type: connector
    target: bigquery
    direction: out
    table: clean_responses
    secret: BQ_SERVICE_ACCOUNT      # a project_secrets key
    dataset: research
    # …adapter-specific config…
```

`api/app/routers/connectors.py` exposes:

```
GET /projects/{project_id}/connectors
```

It fetches `siamang.yaml` from the project's default branch (via Gitea), filters
to `type: connector` tasks, and returns each as a `ConnectorOut`
(`name`, `target`, `direction`, `table`, `secret_key`). If the project has no Git
repository it answers **409**.

---

## How secrets back connectors

Credentials are never stored in the YAML. A connector's `secret` field names a key
in **`project_secrets`** — the Fernet-encrypted, per-project secret store
(migration 006, under RLS by `org_id`). Secret values are write-only over the API
(the list endpoint returns keys only). When live transfer is implemented, the
worker will resolve the named secret, decrypt it with `FERNET_KEY`, and hand it to
the adapter — the same store that backs Git-mirror tokens and BYO-DB DSNs. See
[[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] for the encryption
details.

---

## In the web app

The **Connectors** screen is a catalog of available targets (each with a Connect
button) plus the list of connectors declared in the project. Because live transfer
is not part of the beta, the whole screen carries a **"Coming soon"** badge, and
the screen is wrapped in the `connectors` plan gate (Pro/Corporate). In mock mode,
creating a connector adds it to an in-memory list; in live mode, connectors are
declared in `siamang.yaml` and committed — the UI directs you there rather than
creating one through a form. Git mirrors (the other half of the
`FEATURE_CONNECTORS` entitlement) are configured under **Settings → Git mirrors**.
