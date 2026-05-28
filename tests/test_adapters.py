"""Tests for GoogleSheetsBackend and NetlifyFrontend adapters.

Uses mocks to avoid requiring real API credentials.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Test: Registry resolves new adapters ────────────────────────────────────

def test_registry_lists_gsheets_and_netlify():
    from siamang.deploy.registry import list_backends, list_frontends

    backends = list_backends()
    frontends = list_frontends()

    assert "gsheets" in backends, f"gsheets not in {backends}"
    assert "netlify" in frontends, f"netlify not in {frontends}"
    print("✓ Registry lists gsheets backend and netlify frontend")


def test_registry_factory_resolves():
    from siamang.deploy.registry import backend_factory, frontend_factory

    # These should not raise
    gsheets_cls = backend_factory("gsheets")
    netlify_cls = frontend_factory("netlify")

    assert gsheets_cls.__name__ == "GoogleSheetsBackend"
    assert netlify_cls.__name__ == "NetlifyFrontend"
    print("✓ Factory resolves GoogleSheetsBackend and NetlifyFrontend classes")


# ─── Test: GoogleSheetsBackend ───────────────────────────────────────────────

def test_gsheets_backend_init():
    """Test that GoogleSheetsBackend can be instantiated without credentials."""
    os.environ["SIAMANG_GSHEETS_CREDENTIALS_FILE"] = "/tmp/fake_creds.json"
    os.environ["SIAMANG_GSHEETS_SPREADSHEET_ID"] = "test_spreadsheet_123"

    from siamang.deploy.backends.gsheets import GoogleSheetsBackend

    backend = GoogleSheetsBackend()
    assert backend.name == "gsheets"
    assert backend.credentials_file == "/tmp/fake_creds.json"
    assert backend.spreadsheet_id == "test_spreadsheet_123"
    print("✓ GoogleSheetsBackend initializes from env vars")


def test_gsheets_provision_mock():
    """Test provision with mocked Google API."""
    from siamang.deploy.backends.gsheets import GoogleSheetsBackend

    backend = GoogleSheetsBackend(
        credentials_file="/tmp/fake.json",
        spreadsheet_id="existing_sheet_id",
    )

    # Mock the service
    mock_service = MagicMock()
    mock_service.spreadsheets().values().update().execute.return_value = {}
    mock_service.spreadsheets().values().get().execute.return_value = {"values": []}
    backend._service = mock_service
    backend._credentials = MagicMock()

    # Create a mock schema
    mock_schema = MagicMock()
    mock_schema.title = "Test Survey"
    mock_schema.max_responses = 100
    mock_schema.quotas = []
    mock_schema.to_dict.return_value = {
        "variables": [
            {"name": "age"},
            {"name": "gender"},
            {"name": "satisfaction"},
        ]
    }

    config = backend.provision(mock_schema)

    assert config.backend == "gsheets"
    assert config.survey_id  # non-empty
    assert config.settings["spreadsheet_id"] == "existing_sheet_id"
    assert "docs.google.com/spreadsheets" in config.dashboard_url
    print(f"✓ GoogleSheetsBackend.provision() returns valid config (survey_id={config.survey_id})")


def test_gsheets_store_response_mock():
    """Test store_response with mocked API."""
    from siamang.deploy.backends.gsheets import GoogleSheetsBackend

    backend = GoogleSheetsBackend(
        credentials_file="/tmp/fake.json",
        spreadsheet_id="sheet_123",
    )

    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [["_response_id", "_submitted_at", "age", "gender"]]
    }
    mock_service.spreadsheets().values().append().execute.return_value = {}
    backend._service = mock_service
    backend._credentials = MagicMock()

    response_id = backend.store_response("survey_abc", {"age": 25, "gender": 1})
    assert response_id  # non-empty UUID
    assert len(response_id) == 16
    print(f"✓ GoogleSheetsBackend.store_response() returns response_id={response_id}")


def test_gsheets_get_responses_mock():
    """Test get_responses with mocked API."""
    from siamang.deploy.backends.gsheets import GoogleSheetsBackend

    backend = GoogleSheetsBackend(
        credentials_file="/tmp/fake.json",
        spreadsheet_id="sheet_123",
    )

    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["_response_id", "_submitted_at", "age", "gender"],
            ["resp_001", "2025-01-01T00:00:00Z", "25", "1"],
            ["resp_002", "2025-01-02T00:00:00Z", "30", "2"],
        ]
    }
    backend._service = mock_service
    backend._credentials = MagicMock()

    df = backend.get_responses("survey_abc")
    assert len(df) == 2
    assert list(df.columns) == ["_response_id", "_submitted_at", "age", "gender"]
    assert df["age"].iloc[0] == 25
    assert df["gender"].iloc[1] == 2
    print(f"✓ GoogleSheetsBackend.get_responses() returns DataFrame with {len(df)} rows")


def test_gsheets_check_quota_mock():
    """Test quota checking with mocked API."""
    from siamang.deploy.backends.gsheets import GoogleSheetsBackend

    backend = GoogleSheetsBackend(
        credentials_file="/tmp/fake.json",
        spreadsheet_id="sheet_123",
    )

    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["variable", "value", "target", "current"],
            ["gender", "1", "50", "30"],
            ["gender", "2", "50", "50"],  # Full!
        ]
    }
    backend._service = mock_service
    backend._credentials = MagicMock()

    assert backend.check_quota("survey_abc", "gender", 1) is True  # 30 < 50
    assert backend.check_quota("survey_abc", "gender", 2) is False  # 50 >= 50
    print("✓ GoogleSheetsBackend.check_quota() correctly checks capacity")


# ─── Test: NetlifyFrontend ───────────────────────────────────────────────────

def test_netlify_frontend_init():
    """Test NetlifyFrontend initialization."""
    os.environ["NETLIFY_AUTH_TOKEN"] = "test_token_123"

    from siamang.deploy.frontends.netlify import NetlifyFrontend

    frontend = NetlifyFrontend()
    assert frontend.name == "netlify"
    assert frontend.token == "test_token_123"
    print("✓ NetlifyFrontend initializes from env var")


def test_netlify_build_zip():
    """Test ZIP creation from bundle files."""
    from siamang.deploy.frontends.netlify import NetlifyFrontend
    import zipfile
    import io

    frontend = NetlifyFrontend(token="fake")

    files = {
        "index.html": "<html><body>Hello</body></html>",
        "main.js": "console.log('hi');",
        "style.css": "body { margin: 0; }",
    }

    zip_data = frontend._build_zip(files)
    assert len(zip_data) > 0

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf:
        names = zf.namelist()
        assert "index.html" in names
        assert "main.js" in names
        assert "style.css" in names
        content = zf.read("index.html").decode("utf-8")
        assert "Hello" in content

    print(f"✓ NetlifyFrontend._build_zip() creates valid ZIP ({len(zip_data)} bytes, {len(names)} files)")


def test_netlify_publish_rest_mock():
    """Test publish with mocked Netlify API."""
    from siamang.deploy.frontends.netlify import NetlifyFrontend

    mock_session = MagicMock()

    # Mock create site response
    mock_create_resp = MagicMock()
    mock_create_resp.raise_for_status.return_value = None
    mock_create_resp.json.return_value = {"id": "site_abc123"}

    # Mock deploy response (ready immediately)
    mock_deploy_resp = MagicMock()
    mock_deploy_resp.raise_for_status.return_value = None
    mock_deploy_resp.json.return_value = {
        "id": "deploy_xyz",
        "state": "ready",
        "ssl_url": "https://my-survey.netlify.app",
    }

    mock_session.post.side_effect = [mock_create_resp, mock_deploy_resp]

    frontend = NetlifyFrontend(token="fake_token", session=mock_session)

    # Create mock bundle and config
    mock_bundle = MagicMock()
    mock_bundle.files = {"index.html": "<html></html>"}
    mock_bundle.manifest = {}

    mock_config = MagicMock()
    mock_config.survey_id = "survey_123"

    url = frontend.publish(mock_bundle, mock_config)
    assert url == "https://my-survey.netlify.app"
    print(f"✓ NetlifyFrontend.publish() returns URL: {url}")


def test_netlify_publish_local_fallback():
    """Test that publish falls back to local write when no token."""
    from siamang.deploy.frontends.netlify import NetlifyFrontend
    import tempfile
    import shutil

    # Clear env var to ensure no token
    os.environ.pop("NETLIFY_AUTH_TOKEN", None)
    os.environ.pop("SIAMANG_NETLIFY_TOKEN", None)

    frontend = NetlifyFrontend(token="", session=None)

    mock_bundle = MagicMock()
    mock_bundle.files = {"index.html": "<html>test</html>"}
    mock_bundle.manifest = {}

    mock_config = MagicMock()
    mock_config.survey_id = "test_survey"

    # This should write to local directory
    result = frontend.publish(mock_bundle, mock_config)
    assert "netlify_deploy" in result
    print(f"✓ NetlifyFrontend local fallback writes to: {result}")

    # Cleanup
    import shutil
    from pathlib import Path
    deploy_path = Path(result)
    if deploy_path.exists():
        shutil.rmtree(deploy_path)


# ─── Test: GoogleSheetsClientTemplate ────────────────────────────────────────

def test_gsheets_client_template():
    """Test that the client template renders valid JS."""
    from siamang.frontend.client.gsheets import GoogleSheetsClientTemplate
    from siamang.frontend.client.base import ClientEnv

    template = GoogleSheetsClientTemplate()
    env = ClientEnv(
        survey_id="survey_abc",
        backend="gsheets",
        settings={
            "spreadsheet_id": "sheet_123",
            "sheet_name": "Responses",
            "apps_script_url": "https://script.google.com/macros/s/xxx/exec",
        },
    )

    js = template.render_env_js(env)
    assert "SIAMANG_ENV" in js
    assert "gsheets" in js
    assert "sheet_123" in js
    assert "script.google.com" in js
    assert "submit" in js
    assert "checkQuota" in js
    print("✓ GoogleSheetsClientTemplate renders valid JS with all settings")


# ─── Test: Pipeline integration ──────────────────────────────────────────────

def test_pipeline_client_for_gsheets():
    """Test that pipeline resolves gsheets client template."""
    from siamang.deploy.pipeline import _client_for

    client = _client_for("gsheets")
    assert client.name == "gsheets"
    print("✓ Pipeline _client_for('gsheets') resolves correctly")


# ─── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_registry_lists_gsheets_and_netlify,
        test_registry_factory_resolves,
        test_gsheets_backend_init,
        test_gsheets_provision_mock,
        test_gsheets_store_response_mock,
        test_gsheets_get_responses_mock,
        test_gsheets_check_quota_mock,
        test_netlify_frontend_init,
        test_netlify_build_zip,
        test_netlify_publish_rest_mock,
        test_netlify_publish_local_fallback,
        test_gsheets_client_template,
        test_pipeline_client_for_gsheets,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)
    print("All tests passed! ✓")
