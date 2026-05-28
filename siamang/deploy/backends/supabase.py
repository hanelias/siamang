"""Supabase backend adapter — provisions response storage with RLS and migration support."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from siamang.deploy.backend_config import BackendConfig
from siamang.deploy.base import BackendAdapter

if TYPE_CHECKING:
    import pandas as pd

    from siamang.frontend.schema import SurveySchema


# --------------------------------------------------------------------------
# Schema: single shared table `responses` with survey_id column.
# This mirrors the local SQLite backend model for consistency.
# --------------------------------------------------------------------------

_RESPONSES_TABLE = """
CREATE TABLE IF NOT EXISTS responses (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT NOT NULL,
    data JSONB NOT NULL,
    respondent_id UUID DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_RLS_POLICIES = """
ALTER TABLE responses ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'anon_insert_responses'
    ) THEN
        CREATE POLICY "anon_insert_responses" ON responses
            FOR INSERT TO anon WITH CHECK (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'auth_select_responses'
    ) THEN
        CREATE POLICY "auth_select_responses" ON responses
            FOR SELECT TO authenticated USING (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'auth_delete_responses'
    ) THEN
        CREATE POLICY "auth_delete_responses" ON responses
            FOR DELETE TO authenticated USING (true);
    END IF;
END $$;
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_responses_survey_id
    ON responses (survey_id);
CREATE INDEX IF NOT EXISTS idx_responses_created
    ON responses (survey_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_responses_respondent
    ON responses (respondent_id);
"""

_SURVEY_META_TABLE = """
CREATE TABLE IF NOT EXISTS survey_meta (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT UNIQUE NOT NULL,
    title TEXT,
    schema_json JSONB,
    max_responses INTEGER,
    schema_hash TEXT,
    variables_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_QUOTA_TABLE = """
CREATE TABLE IF NOT EXISTS quota_counters (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    value TEXT NOT NULL,
    target INTEGER NOT NULL,
    current INTEGER NOT NULL DEFAULT 0,
    UNIQUE (survey_id, variable, value)
);
"""


class SupabaseProvisionError(RuntimeError):
    """Raised when Supabase provisioning fails (e.g. missing exec_sql RPC)."""


def _compute_schema_hash(survey_id: str, variables: list[dict[str, Any]]) -> str:
    """Compute a hash of the variable schema for migration tracking."""
    payload = json.dumps(variables, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _default_session() -> Any:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "requests is required for the Supabase backend. Install with: pip install requests"
        ) from exc
    return requests.Session()


def _get_env(new_name: str, legacy_name: str, default: str = "") -> str:
    """Read env var with fallback to legacy SURVLIB_* name."""
    return os.environ.get(new_name, os.environ.get(legacy_name, default))


def generate_migration_sql(
    survey_id: str | None = None,
    title: str = "Untitled Survey",
) -> str:
    """Generate the full migration SQL for manual execution in Supabase SQL Editor.

    This is useful when the ``exec_sql`` RPC function is not available.
    Copy the output and run it in the Supabase Dashboard → SQL Editor.

    Parameters
    ----------
    survey_id : str, optional
        If provided, includes a survey_meta INSERT for this specific survey.
    title : str
        Survey title for the meta record.

    Returns
    -------
    str
        Complete SQL migration script.
    """
    parts = [
        "-- Siamang: Supabase migration script",
        f"-- Generated: {datetime.now(UTC).isoformat()}",
        "-- Run this in Supabase Dashboard → SQL Editor",
        "",
        "-- 1. Responses table",
        _RESPONSES_TABLE.strip(),
        "",
        "-- 2. Survey metadata table",
        _SURVEY_META_TABLE.strip(),
        "",
        "-- 3. Quota counters table",
        _QUOTA_TABLE.strip(),
        "",
        "-- 4. Row-Level Security policies",
        _RLS_POLICIES.strip(),
        "",
        "-- 5. Indexes",
        _INDEXES.strip(),
    ]

    if survey_id:
        # Escape single quotes for safe SQL string literals
        safe_id = survey_id.replace("'", "''")
        safe_title = title.replace("'", "''")
        parts.extend(
            [
                "",
                "-- 6. Register this survey",
                f"INSERT INTO survey_meta (survey_id, title) "
                f"VALUES ('{safe_id}', '{safe_title}') ON CONFLICT (survey_id) DO NOTHING;",
            ]
        )

    parts.append("")
    return "\n".join(parts)


@dataclass(slots=True)
class SupabaseBackend(BackendAdapter):
    """Supabase storage backend with RLS policies and migration tracking.

    Uses a single shared ``responses`` table with a ``survey_id`` column,
    mirroring the local SQLite backend model for consistency.

    Environment variables (with legacy fallback):
        SIAMANG_SUPABASE_URL (fallback: SURVLIB_SUPABASE_URL)
        SIAMANG_SUPABASE_ANON_KEY (fallback: SURVLIB_SUPABASE_ANON_KEY)
        SIAMANG_SUPABASE_SERVICE_KEY (fallback: SURVLIB_SUPABASE_SERVICE_KEY)

    Provisioning modes:
        1. **Auto** (default): calls ``exec_sql`` RPC to create tables.
           Requires a Postgres function ``exec_sql(query TEXT)`` in your
           Supabase project. See docs for setup instructions.
        2. **Manual**: pass ``auto_provision=False`` and run the SQL from
           ``generate_migration_sql()`` in the Supabase SQL Editor yourself.
    """

    name: str = "supabase"
    url: str = ""
    anon_key: str = ""
    service_key: str = ""
    table: str = "responses"
    quota_function: str = "quota-check"
    auto_provision: bool = True
    session: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.url = self.url or _get_env("SIAMANG_SUPABASE_URL", "SURVLIB_SUPABASE_URL")
        self.anon_key = self.anon_key or _get_env(
            "SIAMANG_SUPABASE_ANON_KEY", "SURVLIB_SUPABASE_ANON_KEY"
        )
        self.service_key = self.service_key or _get_env(
            "SIAMANG_SUPABASE_SERVICE_KEY", "SURVLIB_SUPABASE_SERVICE_KEY"
        )
        if not self.url:
            raise ValueError(
                "SupabaseBackend requires 'url' "
                "(or env SIAMANG_SUPABASE_URL / SURVLIB_SUPABASE_URL)."
            )
        if not self.anon_key:
            raise ValueError(
                "SupabaseBackend requires 'anon_key' "
                "(or env SIAMANG_SUPABASE_ANON_KEY / SURVLIB_SUPABASE_ANON_KEY)."
            )
        if not self.service_key:
            raise ValueError(
                "SupabaseBackend requires 'service_key' "
                "(or env SIAMANG_SUPABASE_SERVICE_KEY / SURVLIB_SUPABASE_SERVICE_KEY)."
            )
        if self.session is None:
            self.session = _default_session()

    def _admin_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }

    def _table_url(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1/{self.table}"

    def _exec_sql(self, query: str, *, required: bool = True) -> bool:
        """Execute raw SQL via Supabase REST API (requires exec_sql RPC function).

        Parameters
        ----------
        query : str
            SQL to execute.
        required : bool
            If True (default), raises SupabaseProvisionError on failure.
            If False, returns False silently.

        Returns
        -------
        bool
            True if the query executed successfully.

        Raises
        ------
        SupabaseProvisionError
            If required=True and the RPC call fails.
        """
        rpc_url = f"{self.url.rstrip('/')}/rest/v1/rpc/exec_sql"
        try:
            response = self.session.post(
                rpc_url,
                headers=self._admin_headers(),
                data=json.dumps({"query": query}),
                timeout=30,
            )
        except Exception as exc:
            if required:
                raise SupabaseProvisionError(
                    f"Failed to connect to Supabase exec_sql RPC: {exc}\n\n"
                    "To fix this, either:\n"
                    "  1. Create the exec_sql RPC function in your Supabase project:\n"
                    "     CREATE OR REPLACE FUNCTION exec_sql(query TEXT)\n"
                    "     RETURNS VOID AS $$ BEGIN EXECUTE query; END; $$ LANGUAGE plpgsql;\n\n"
                    "  2. Or run the migration manually:\n"
                    "     from siamang.deploy.backends.supabase import generate_migration_sql\n"
                    "     print(generate_migration_sql())\n"
                    "     # Copy output → Supabase Dashboard → SQL Editor → Run\n\n"
                    "  3. Or set auto_provision=False:\n"
                    "     SupabaseBackend(auto_provision=False, ...)"
                ) from exc
            return False

        if response.status_code not in (200, 201, 204):
            if required:
                # Detect common failure: RPC function doesn't exist (404)
                if response.status_code == 404:
                    raise SupabaseProvisionError(
                        "The exec_sql RPC function was not found in your Supabase project.\n\n"
                        "To fix this, either:\n"
                        "  1. Create it in Supabase Dashboard → SQL Editor:\n\n"
                        "     CREATE OR REPLACE FUNCTION exec_sql(query TEXT)\n"
                        "     RETURNS VOID AS $$\n"
                        "     BEGIN EXECUTE query; END;\n"
                        "     $$ LANGUAGE plpgsql SECURITY DEFINER;\n\n"
                        "  2. Or run the migration SQL manually:\n"
                        "     from siamang.deploy.backends.supabase import generate_migration_sql\n"
                        "     print(generate_migration_sql())\n"
                        "     # Copy output → Supabase Dashboard → SQL Editor → Run\n\n"
                        "  3. Or set auto_provision=False:\n"
                        "     SupabaseBackend(auto_provision=False, ...)"
                    )
                raise SupabaseProvisionError(
                    f"exec_sql RPC returned HTTP {response.status_code}: "
                    f"{response.text[:300]}\n\n"
                    "If you cannot resolve this, run the migration manually:\n"
                    "  from siamang.deploy.backends.supabase import generate_migration_sql\n"
                    "  print(generate_migration_sql())"
                )
            return False

        return True

    def _extract_variables(self, schema: SurveySchema) -> list[dict[str, Any]]:
        """Extract variable definitions from survey schema for migration tracking."""
        data = schema.to_dict()
        return data.get("variables", [])

    def provision(self, schema: SurveySchema, migration_dir: str | None = None) -> BackendConfig:
        """Create/update Supabase tables with migration tracking and RLS.

        Creates a shared ``responses`` table (if not exists), registers the
        survey in ``survey_meta``, and sets up quota counters.

        If ``auto_provision`` is False, skips table creation (assumes tables
        already exist from a manual migration).

        Parameters
        ----------
        schema : SurveySchema
            The compiled survey schema.
        migration_dir : str, optional
            If provided, writes a .sql migration file to this directory
            regardless of auto_provision setting.

        Raises
        ------
        SupabaseProvisionError
            If auto_provision is True and exec_sql RPC is unavailable.
        """
        survey_id = uuid.uuid4().hex[:12]
        variables = self._extract_variables(schema)
        schema_hash = _compute_schema_hash(survey_id, variables)

        dashboard_url = f"{self.url.rstrip('/')}/project/_/editor"

        # Always export migration SQL if requested (useful even with auto_provision)
        if migration_dir:
            from pathlib import Path

            migrations = Path(migration_dir)
            migrations.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            migration_sql = generate_migration_sql(
                survey_id=survey_id, title=schema.title or "Untitled"
            )
            (migrations / f"{timestamp}_provision_{survey_id}.sql").write_text(migration_sql)

        # Auto-provision: create tables via exec_sql RPC
        if self.auto_provision:
            self._exec_sql(_SURVEY_META_TABLE, required=True)
            self._exec_sql(_RESPONSES_TABLE, required=True)
            self._exec_sql(_RLS_POLICIES, required=True)
            self._exec_sql(_INDEXES, required=True)
            self._exec_sql(_QUOTA_TABLE, required=True)

        # Register survey in survey_meta (via REST API, not exec_sql)
        meta_url = f"{self.url.rstrip('/')}/rest/v1/survey_meta"
        meta_payload = {
            "survey_id": survey_id,
            "title": schema.title,
            "schema_json": json.dumps(schema.to_dict(), ensure_ascii=False),
            "max_responses": schema.max_responses,
            "schema_hash": schema_hash,
            "variables_json": json.dumps(variables, ensure_ascii=False),
        }
        response = self.session.post(
            meta_url,
            headers=self._admin_headers() | {"Prefer": "return=minimal"},
            data=json.dumps(meta_payload),
        )
        response.raise_for_status()

        # Create quota_counters if needed
        if schema.quotas:
            quota_url = f"{self.url.rstrip('/')}/rest/v1/quota_counters"
            quota_rows = [
                {
                    "survey_id": survey_id,
                    "variable": quota["variable"],
                    "value": json.dumps(quota["target_value"]),
                    "target": quota["limit"],
                    "current": 0,
                }
                for quota in schema.quotas
            ]
            response = self.session.post(
                quota_url,
                headers=self._admin_headers() | {"Prefer": "return=minimal"},
                data=json.dumps(quota_rows),
            )
            response.raise_for_status()

        return BackendConfig(
            backend=self.name,
            survey_id=survey_id,
            settings={
                "url": self.url,
                "anon_key": self.anon_key,
                "table": self.table,
                "quota_function": self.quota_function,
                "schema_hash": schema_hash,
            },
            dashboard_url=dashboard_url,
        )

    def get_responses(
        self,
        survey_id: str,
        *,
        limit: int = 1000,
        offset: int = 0,
    ) -> pd.DataFrame:
        """Fetch responses for a specific survey from the shared table."""
        import pandas as pd

        params = {
            "survey_id": f"eq.{survey_id}",
            "select": "*",
            "limit": str(limit),
            "offset": str(offset),
            "order": "created_at.desc",
        }
        response = self.session.get(self._table_url(), headers=self._admin_headers(), params=params)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return pd.DataFrame()

        processed = []
        for r in rows:
            row = r.get("data", r)
            if isinstance(row, dict):
                row["_response_id"] = r.get("id")
                row["_respondent_id"] = r.get("respondent_id")
                row["_submitted_at"] = r.get("created_at")
            processed.append(row)

        return pd.json_normalize(processed)

    def get_all_responses(self, survey_id: str, page_size: int = 1000) -> pd.DataFrame:
        """Fetch all responses with pagination."""
        import pandas as pd

        all_frames = []
        offset = 0
        while True:
            df = self.get_responses(survey_id, limit=page_size, offset=offset)
            if df.empty:
                break
            all_frames.append(df)
            offset += page_size
            if len(df) < page_size:
                break

        if not all_frames:
            return pd.DataFrame()
        return pd.concat(all_frames, ignore_index=True)

    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Check if a quota is still open for the given variable/value."""
        quota_url = f"{self.url.rstrip('/')}/rest/v1/quota_counters"
        params = {
            "survey_id": f"eq.{survey_id}",
            "variable": f"eq.{variable}",
            "value": f"eq.{json.dumps(value)}",
            "select": "target,current",
        }
        response = self.session.get(quota_url, headers=self._admin_headers(), params=params)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return True
        row = rows[0]
        return int(row["current"]) < int(row["target"])
