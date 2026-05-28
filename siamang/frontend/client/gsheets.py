"""Google Sheets backend client — POSTs responses via Google Sheets API or Apps Script proxy."""

from __future__ import annotations

import json

from siamang.frontend.client.base import BackendClientTemplate, ClientEnv


class GoogleSheetsClientTemplate(BackendClientTemplate):
    """Client-side transport for Google Sheets backend.

    Uses a Google Apps Script Web App as a proxy to append rows to the sheet.
    This avoids exposing service account credentials in the browser.

    The Apps Script URL is provided via settings["apps_script_url"] during deploy.
    If not available, falls back to a direct Sheets API call (requires OAuth token
    in the browser, suitable for internal/testing use only).
    """

    name = "gsheets"

    def render_env_js(self, env: ClientEnv) -> str:
        env_payload = {
            "transport": "gsheets",
            "survey_id": env.survey_id,
            "spreadsheet_id": env.settings.get("spreadsheet_id", ""),
            "sheet_name": env.settings.get("sheet_name", "Responses"),
            "apps_script_url": env.settings.get("apps_script_url", ""),
            "api_endpoint": env.settings.get("api_endpoint", ""),
        }
        return _TEMPLATE.replace("__ENV__", json.dumps(env_payload, ensure_ascii=False))


_TEMPLATE = """\
window.SIAMANG_ENV = __ENV__;
window.SIAMANG_TRANSPORTS = window.SIAMANG_TRANSPORTS || {};
window.SIAMANG_TRANSPORTS.gsheets = {
  async submit(responses) {
    const env = window.SIAMANG_ENV;

    // Prefer Apps Script proxy (no auth needed from browser)
    if (env.apps_script_url) {
      const res = await fetch(env.apps_script_url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "submit",
          survey_id: env.survey_id,
          spreadsheet_id: env.spreadsheet_id,
          sheet_name: env.sheet_name,
          data: responses,
        }),
      });
      if (!res.ok) {
        throw new Error("gsheets submit failed: " + res.status);
      }
      return await res.json();
    }

    // Fallback: direct Sheets API (requires token — for testing/internal use)
    const url = "https://sheets.googleapis.com/v4/spreadsheets/" +
      env.spreadsheet_id + "/values/" +
      encodeURIComponent(env.sheet_name + "!A:A") + ":append" +
      "?valueInputOption=RAW&insertDataOption=INSERT_ROWS";

    const row = Object.values(responses);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: [row] }),
    });
    if (!res.ok) {
      throw new Error("gsheets direct submit failed: " + res.status);
    }
    return { ok: true };
  },

  async checkQuota(variable, value) {
    const env = window.SIAMANG_ENV;
    if (!env.apps_script_url) return { ok: true, allowed: true };

    const res = await fetch(env.apps_script_url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "checkQuota",
        survey_id: env.survey_id,
        spreadsheet_id: env.spreadsheet_id,
        variable: variable,
        value: value,
      }),
    });
    if (!res.ok) return { ok: false };
    return await res.json();
  }
};
"""
