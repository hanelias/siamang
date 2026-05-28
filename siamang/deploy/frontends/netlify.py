"""Netlify frontend adapter — publishes survey bundles to Netlify via REST API or CLI.

Authentication:
    - Personal access token (PAT) via env var NETLIFY_AUTH_TOKEN
    - Or pass token directly to the constructor

Deployment methods:
    1. ZIP upload via REST API (default, no CLI needed)
    2. CLI fallback (npx netlify deploy --prod)
    3. Local fallback (writes files to disk for manual deploy)
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from siamang.deploy.base import FrontendAdapter

if TYPE_CHECKING:
    from siamang.deploy.backend_config import BackendConfig
    from siamang.frontend.bundle import SurveyBundle


_NETLIFY_API = "https://api.netlify.com/api/v1"

_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://unpkg.com; "
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self' https://*.supabase.co https://sheets.googleapis.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


@dataclass(slots=True)
class NetlifyFrontend(FrontendAdapter):
    """Netlify frontend adapter — deploys static survey bundles to Netlify CDN.

    Supports three deployment paths:
    1. REST API with ZIP upload (recommended, no CLI needed)
    2. Netlify CLI fallback
    3. Local write for manual deploy

    Configuration:
        - token: Netlify personal access token (or NETLIFY_AUTH_TOKEN env var)
        - site_id: existing Netlify site ID (optional; creates new if empty)
        - site_name: name for new site (used only when creating)
    """

    name: str = "netlify"
    token: str = ""
    site_id: str = ""
    site_name: str = "siamang-survey"
    session: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.token = self.token or os.environ.get("NETLIFY_AUTH_TOKEN", "")
        if not self.token:
            # Legacy env var
            self.token = os.environ.get("SIAMANG_NETLIFY_TOKEN", "")
        if self.session is None:
            self.session = _default_session()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "siamang-deploy/1.0",
        }

    def _create_site(self) -> str:
        """Create a new Netlify site and return its site_id."""
        response = self.session.post(
            f"{_NETLIFY_API}/sites",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"name": self.site_name},
        )
        response.raise_for_status()
        body = response.json()
        self.site_id = body["id"]
        return self.site_id

    def _build_zip(self, files: dict[str, str | bytes]) -> bytes:
        """Create an in-memory ZIP archive from bundle files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for relative_path, content in files.items():
                if isinstance(content, str):
                    zf.writestr(relative_path, content.encode("utf-8"))
                else:
                    zf.writestr(relative_path, content)
        return buf.getvalue()

    def _build_headers_file(self) -> str:
        """Generate Netlify _headers file with security headers."""
        lines = [
            "/*",
            f"  Content-Security-Policy: {_DEFAULT_CSP}",
            "  X-Content-Type-Options: nosniff",
            "  X-Frame-Options: DENY",
            "  Referrer-Policy: strict-origin-when-cross-origin",
            "  Permissions-Policy: camera=(), microphone=(), geolocation=()",
            "",
            "/*.js",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
            "/*.css",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
            "/index.html",
            "  Cache-Control: public, max-age=0, must-revalidate",
        ]
        return "\n".join(lines)

    def _build_redirects_file(self) -> str:
        """Generate Netlify _redirects for SPA routing."""
        return "/*    /index.html   200\n"

    def publish(self, bundle: SurveyBundle, config: BackendConfig) -> str:
        """Deploy the survey bundle to Netlify.

        Returns the public URL of the deployed site.
        """
        # Prepare files with Netlify-specific config
        files = dict(bundle.files)
        files["_headers"] = self._build_headers_file()
        files["_redirects"] = self._build_redirects_file()

        # Check deployment path
        if not self.token:
            # No token — local fallback: write to disk for manual deploy
            deploy_dir = Path(f".netlify_deploy_{config.survey_id}")
            from siamang.frontend.bundle import SurveyBundle

            SurveyBundle(files=files, manifest=bundle.manifest).write_to(str(deploy_dir))
            return str(deploy_dir)

        if self.session is not None and type(self.session).__module__ != "requests":
            # Non-requests session (test mock) — use REST
            return self._publish_rest(files, config)

        if self.session:
            return self._publish_rest(files, config)

        return self._publish_cli(files, config)

    def _publish_rest(self, files: dict[str, str | bytes], config: BackendConfig) -> str:
        """Deploy via Netlify REST API using ZIP upload method."""
        # Ensure we have a site
        if not self.site_id:
            self._create_site()

        # Build ZIP
        zip_data = self._build_zip(files)

        # Create deploy via ZIP upload
        response = self.session.post(
            f"{_NETLIFY_API}/sites/{self.site_id}/deploys",
            headers={
                **self._headers(),
                "Content-Type": "application/zip",
            },
            data=zip_data,
        )
        response.raise_for_status()
        body = response.json()

        # Poll for deploy state if needed
        deploy_id = body.get("id")
        state = body.get("state", "")

        if state not in ("ready", "uploaded"):
            # Poll until ready (max 60 seconds)
            import time

            for _ in range(30):
                time.sleep(2)
                poll_resp = self.session.get(
                    f"{_NETLIFY_API}/deploys/{deploy_id}",
                    headers=self._headers(),
                )
                poll_resp.raise_for_status()
                poll_body = poll_resp.json()
                state = poll_body.get("state", "")
                if state == "ready":
                    body = poll_body
                    break
                if state == "error":
                    raise RuntimeError(
                        f"Netlify deploy failed: {poll_body.get('error_message', 'unknown error')}"
                    )
            else:
                raise RuntimeError(f"Netlify deploy timed out (last state: {state})")

        # Extract URL
        url = body.get("ssl_url") or body.get("url") or body.get("deploy_ssl_url")
        if not url:
            # Construct from site name
            site_name = body.get("name", self.site_name)
            url = f"https://{site_name}.netlify.app"

        return url

    def _publish_cli(self, files: dict[str, str | bytes], config: BackendConfig) -> str:
        """Deploy via Netlify CLI as fallback."""
        from siamang.frontend.bundle import SurveyBundle

        with tempfile.TemporaryDirectory() as tmp:
            SurveyBundle(files=files, manifest={}).write_to(tmp)

            import subprocess

            cmd = ["npx", "netlify", "deploy", "--prod", "--dir", tmp]
            if self.site_id:
                cmd.extend(["--site", self.site_id])

            env = os.environ.copy()
            env["NETLIFY_AUTH_TOKEN"] = self.token

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            if result.returncode == 0:
                # Parse URL from CLI output
                for line in result.stdout.splitlines():
                    if "Website URL:" in line or "https://" in line:
                        url = line.split("https://")[-1].strip()
                        return f"https://{url}"
                return result.stdout.strip()
            raise RuntimeError(f"Netlify deploy failed: {result.stderr}")

    def get_deploy_status(self, deploy_id: str) -> dict[str, Any]:
        """Check the status of a specific deploy."""
        response = self.session.get(
            f"{_NETLIFY_API}/deploys/{deploy_id}",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def list_deploys(self) -> list[dict[str, Any]]:
        """List all deploys for the current site."""
        if not self.site_id:
            return []
        response = self.session.get(
            f"{_NETLIFY_API}/sites/{self.site_id}/deploys",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()


def _default_session() -> Any:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "requests is required for the Netlify frontend. "
            "Install with: pip install siamang[netlify] or: pip install requests"
        ) from exc
    return requests.Session()
