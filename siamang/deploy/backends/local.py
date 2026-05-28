"""Local SQLite backend — same interface as cloud backends, no network."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from siamang.deploy.backend_config import BackendConfig
from siamang.deploy.base import BackendAdapter

if TYPE_CHECKING:
    from siamang.frontend.schema import SurveySchema


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS survey_meta (
    survey_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    max_responses INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT NOT NULL REFERENCES survey_meta(survey_id),
    payload_json TEXT NOT NULL,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_responses_survey ON responses(survey_id);

CREATE TABLE IF NOT EXISTS quota_counters (
    survey_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    value TEXT NOT NULL,
    target INTEGER NOT NULL,
    current INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (survey_id, variable, value)
);
"""


@dataclass(slots=True)
class LocalBackend(BackendAdapter):
    """SQLite-backed storage for the local deployment path.

    Resolves to ``./survey.db`` by default. Pass ``path`` to override.
    """

    name: str = "local"
    path: str | Path = "survey.db"
    _last_survey_id: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._init_schema()

    @property
    def url(self) -> str:
        return f"sqlite:///{self.path}"

    def _init_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()

    def provision(self, schema: SurveySchema) -> BackendConfig:
        survey_id = uuid.uuid4().hex[:12]
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute(
                "INSERT INTO survey_meta (survey_id, title, schema_json, max_responses) VALUES (?, ?, ?, ?)",
                (
                    survey_id,
                    schema.title,
                    json.dumps(schema.to_dict(), ensure_ascii=False),
                    schema.max_responses,
                ),
            )
            for quota in schema.quotas:
                conn.execute(
                    "INSERT INTO quota_counters (survey_id, variable, value, target) VALUES (?, ?, ?, ?)",
                    (
                        survey_id,
                        quota["variable"],
                        json.dumps(quota["target_value"]),
                        quota["limit"],
                    ),
                )
            conn.commit()
        self._last_survey_id = survey_id
        return BackendConfig(
            backend=self.name,
            survey_id=survey_id,
            settings={"endpoint": "/responses", "quota_endpoint": "/quota-check"},
            internal={"backend_ref": self, "db_path": str(self.path)},
            dashboard_url=f"sqlite:///{self.path}",
        )

    def store_response(self, survey_id: str, payload: dict[str, Any]) -> int:
        with closing(sqlite3.connect(self.path)) as conn:
            cur = conn.execute(
                "INSERT INTO responses (survey_id, payload_json) VALUES (?, ?)",
                (survey_id, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute(
                "SELECT target, current FROM quota_counters WHERE survey_id=? AND variable=? AND value=?",
                (survey_id, variable, json.dumps(value)),
            ).fetchone()
            if row is None:
                return True
            target, current = row
            return current < target

    def increment_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Atomically check + increment a quota counter. Returns False when full."""

        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT target, current FROM quota_counters WHERE survey_id=? AND variable=? AND value=?",
                    (survey_id, variable, json.dumps(value)),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return True
                target, current = row
                if current >= target:
                    conn.commit()
                    return False
                conn.execute(
                    "UPDATE quota_counters SET current = current + 1 WHERE survey_id=? AND variable=? AND value=?",
                    (survey_id, variable, json.dumps(value)),
                )
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    def get_responses(self, survey_id: str) -> pd.DataFrame:
        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT id, payload_json, submitted_at FROM responses WHERE survey_id=? ORDER BY id",
                (survey_id,),
            ).fetchall()
        if not rows:
            return pd.DataFrame()
        records = []
        for row_id, payload_json, submitted_at in rows:
            data = json.loads(payload_json)
            data["_response_id"] = row_id
            data["_submitted_at"] = submitted_at
            records.append(data)
        return pd.DataFrame(records)
