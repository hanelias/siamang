"""Google Sheets backend — stores survey responses as rows in a Google Sheet.

Authentication:
    - Service account JSON key (recommended for server-side use)
    - Set env var SIAMANG_GSHEETS_CREDENTIALS_FILE to the path of the JSON key file
    - Set env var SIAMANG_GSHEETS_SPREADSHEET_ID to an existing spreadsheet ID,
      or leave empty to create a new one

The service account email must have Editor access to the target spreadsheet.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

from siamang.deploy.backend_config import BackendConfig
from siamang.deploy.base import BackendAdapter

if TYPE_CHECKING:
    from siamang.frontend.schema import SurveySchema


def _get_credentials():
    """Load Google service account credentials from JSON key file."""
    try:
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise ImportError(
            "google-auth is required for the Google Sheets backend. "
            "Install with: pip install siamang[gsheets] "
            "or: pip install google-auth google-auth-httplib2 google-api-python-client"
        ) from exc

    creds_file = os.environ.get("SIAMANG_GSHEETS_CREDENTIALS_FILE", "")
    if not creds_file:
        # Legacy env var
        creds_file = os.environ.get("SURVLIB_GSHEETS_CREDENTIALS_FILE", "")
    if not creds_file:
        raise ValueError(
            "SIAMANG_GSHEETS_CREDENTIALS_FILE environment variable must point to "
            "a Google service account JSON key file."
        )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]
    return Credentials.from_service_account_file(creds_file, scopes=scopes)


def _build_sheets_service(credentials=None):
    """Build the Google Sheets API v4 service client."""
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client is required for the Google Sheets backend. "
            "Install with: pip install google-api-python-client"
        ) from exc

    if credentials is None:
        credentials = _get_credentials()
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _build_drive_service(credentials=None):
    """Build the Google Drive API v3 service client (for creating spreadsheets)."""
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client is required for the Google Sheets backend. "
            "Install with: pip install google-api-python-client"
        ) from exc

    if credentials is None:
        credentials = _get_credentials()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


@dataclass(slots=True)
class GoogleSheetsBackend(BackendAdapter):
    """Google Sheets backend — each response becomes a row in a spreadsheet.

    The first row contains variable names as headers. Subsequent rows contain
    response values. A separate ``_meta`` sheet stores survey metadata and
    quota counters.

    Configuration (via env vars or constructor args):
        - credentials_file: path to service account JSON key
        - spreadsheet_id: existing spreadsheet ID (optional; creates new if empty)
        - sheet_name: worksheet name for responses (default: "Responses")
    """

    name: str = "local"  # overridden in __post_init__
    credentials_file: str = ""
    spreadsheet_id: str = ""
    sheet_name: str = "Responses"
    _credentials: Any = field(default=None, init=False, repr=False)
    _service: Any = field(default=None, init=False, repr=False)
    _last_survey_id: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = "gsheets"
        # Resolve from env if not provided directly
        if not self.credentials_file:
            self.credentials_file = os.environ.get(
                "SIAMANG_GSHEETS_CREDENTIALS_FILE",
                os.environ.get("SURVLIB_GSHEETS_CREDENTIALS_FILE", ""),
            )
        if not self.spreadsheet_id:
            self.spreadsheet_id = os.environ.get(
                "SIAMANG_GSHEETS_SPREADSHEET_ID",
                os.environ.get("SURVLIB_GSHEETS_SPREADSHEET_ID", ""),
            )

    @property
    def credentials(self):
        if self._credentials is None:
            if self.credentials_file:
                os.environ["SIAMANG_GSHEETS_CREDENTIALS_FILE"] = self.credentials_file
            self._credentials = _get_credentials()
        return self._credentials

    @property
    def service(self):
        if self._service is None:
            self._service = _build_sheets_service(self.credentials)
        return self._service

    def _create_spreadsheet(self, title: str) -> str:
        """Create a new spreadsheet and return its ID."""
        body = {
            "properties": {"title": title},
            "sheets": [
                {"properties": {"title": self.sheet_name}},
                {"properties": {"title": "_meta"}},
                {"properties": {"title": "_quotas"}},
            ],
        }
        result = self.service.spreadsheets().create(body=body).execute()
        return result["spreadsheetId"]

    def _ensure_spreadsheet(self, title: str) -> str:
        """Return existing spreadsheet_id or create a new one."""
        if self.spreadsheet_id:
            return self.spreadsheet_id
        spreadsheet_id = self._create_spreadsheet(title)
        self.spreadsheet_id = spreadsheet_id
        return spreadsheet_id

    def provision(self, schema: "SurveySchema") -> BackendConfig:
        """Create or configure the spreadsheet for this survey.

        Sets up:
        - Header row in the Responses sheet (variable names)
        - _meta sheet with survey metadata
        - _quotas sheet with quota counters
        """
        survey_id = uuid.uuid4().hex[:12]
        title = f"siamang — {schema.title}"

        spreadsheet_id = self._ensure_spreadsheet(title)

        # Extract variable names for headers
        variables = []
        for var_dict in schema.to_dict().get("variables", []):
            variables.append(var_dict.get("name", ""))

        # Add system columns
        headers = ["_response_id", "_submitted_at"] + variables

        # Write headers to the Responses sheet
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{self.sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

        # Write survey metadata to _meta sheet
        meta_rows = [
            ["survey_id", survey_id],
            ["title", schema.title],
            ["variables", json.dumps(variables)],
            ["max_responses", schema.max_responses or ""],
            ["schema_json", json.dumps(schema.to_dict(), ensure_ascii=False)],
        ]
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="_meta!A1",
            valueInputOption="RAW",
            body={"values": meta_rows},
        ).execute()

        # Write quota counters to _quotas sheet
        quota_rows = [["variable", "value", "target", "current"]]
        for quota in schema.quotas:
            quota_rows.append([
                quota["variable"],
                json.dumps(quota["target_value"]),
                quota["limit"],
                0,
            ])
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="_quotas!A1",
            valueInputOption="RAW",
            body={"values": quota_rows},
        ).execute()

        self._last_survey_id = survey_id

        return BackendConfig(
            backend=self.name,
            survey_id=survey_id,
            settings={
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": self.sheet_name,
                "api_endpoint": f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
            },
            internal={
                "backend_ref": self,
                "credentials_file": self.credentials_file,
                "variables": variables,
            },
            dashboard_url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        )

    def store_response(self, survey_id: str, payload: dict[str, Any]) -> str:
        """Append a response row to the spreadsheet.

        Returns the response_id (UUID).
        """
        response_id = uuid.uuid4().hex[:16]

        # Read headers to know column order
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!1:1",
        ).execute()
        headers = result.get("values", [[]])[0]

        # Build row in header order
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        row = []
        for col in headers:
            if col == "_response_id":
                row.append(response_id)
            elif col == "_submitted_at":
                row.append(now)
            else:
                value = payload.get(col)
                # Convert complex values to JSON strings
                if isinstance(value, (dict, list)):
                    row.append(json.dumps(value, ensure_ascii=False))
                elif value is None:
                    row.append("")
                else:
                    row.append(value)

        # Append row
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        return response_id

    def get_responses(self, survey_id: str) -> pd.DataFrame:
        """Read all responses from the spreadsheet as a DataFrame."""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}",
        ).execute()

        values = result.get("values", [])
        if len(values) < 2:
            return pd.DataFrame()

        headers = values[0]
        rows = values[1:]

        # Pad short rows with empty strings
        max_cols = len(headers)
        padded_rows = [
            row + [""] * (max_cols - len(row)) if len(row) < max_cols else row[:max_cols]
            for row in rows
        ]

        df = pd.DataFrame(padded_rows, columns=headers)

        # Convert numeric-looking columns
        for col in df.columns:
            if col.startswith("_"):
                continue
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except (ValueError, TypeError):
                pass

        # Replace empty strings with NaN
        df = df.replace("", pd.NA)

        return df

    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Check if a quota cell still has capacity."""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range="_quotas!A:D",
        ).execute()

        values = result.get("values", [])
        if len(values) < 2:
            return True  # No quotas defined

        value_json = json.dumps(value)
        for row in values[1:]:
            if len(row) >= 4 and row[0] == variable and row[1] == value_json:
                target = int(row[2])
                current = int(row[3])
                return current < target

        return True  # Quota not found = no limit

    def increment_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Atomically check + increment a quota counter. Returns False when full.

        Note: Google Sheets doesn't support true atomic operations, so there's a
        small race condition window. For high-concurrency surveys, use Supabase instead.
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range="_quotas!A:D",
        ).execute()

        values = result.get("values", [])
        if len(values) < 2:
            return True

        value_json = json.dumps(value)
        for i, row in enumerate(values[1:], start=2):  # 1-indexed, skip header
            if len(row) >= 4 and row[0] == variable and row[1] == value_json:
                target = int(row[2])
                current = int(row[3])
                if current >= target:
                    return False
                # Increment
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"_quotas!D{i}",
                    valueInputOption="RAW",
                    body={"values": [[current + 1]]},
                ).execute()
                return True

        return True  # Quota not found = no limit

    def get_response_count(self, survey_id: str) -> int:
        """Return the number of responses collected so far."""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!A:A",
        ).execute()
        values = result.get("values", [])
        return max(0, len(values) - 1)  # Subtract header row
