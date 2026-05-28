"""Local FastAPI frontend — serves the bundle on localhost."""

import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from siamang.deploy.base import FrontendAdapter

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import (
        HTMLResponse,
        JSONResponse,
        PlainTextResponse,
        Response,
    )

    _FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]
    HTMLResponse = JSONResponse = PlainTextResponse = Response = None  # type: ignore[assignment]
    _FASTAPI_AVAILABLE = False

if TYPE_CHECKING:
    from siamang.deploy.backend_config import BackendConfig
    from siamang.deploy.backends.local import LocalBackend
    from siamang.frontend.bundle import SurveyBundle


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _find_hashed(bundle: "SurveyBundle", basename: str) -> str | None:
    """Find a file in the bundle by basename, accounting for content hashes.

    E.g. _find_hashed(bundle, "style.css") → "style.a1b2c3d4.css"
    Returns the full key if found, or None.
    """
    if basename in bundle.files:
        return basename
    import re

    name, _, ext = basename.rpartition(".")
    if name and ext:
        pattern = re.compile(rf"^{re.escape(name)}\.[a-f0-9]+\.{re.escape(ext)}$")
        for key in bundle.files:
            if pattern.match(key):
                return key
    return None


def build_app(bundle: "SurveyBundle", backend: "LocalBackend", survey_id: str):
    """Construct a FastAPI app that serves the bundle and accepts responses."""

    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "fastapi is required for the local frontend. Install with 'pip install siamang[server]'."
        )

    app = FastAPI(title="siamang-local")

    _style_key = _find_hashed(bundle, "style.css") or "style.css"
    _env_key = _find_hashed(bundle, "env.js") or "env.js"
    _closed_key = _find_hashed(bundle, "closed.html") or "closed.html"
    _manifest_key = _find_hashed(bundle, "manifest.json") or "manifest.json"

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        return HTMLResponse(bundle.files["index.html"])

    @app.get("/style.css")
    def style() -> Any:
        return PlainTextResponse(bundle.files[_style_key], media_type="text/css")

    @app.get("/env.js")
    def env_js() -> Any:
        return PlainTextResponse(bundle.files[_env_key], media_type="application/javascript")

    @app.get("/closed.html", response_class=HTMLResponse)
    def closed() -> Any:
        return HTMLResponse(bundle.files[_closed_key])

    @app.get("/manifest.json")
    def manifest() -> Any:
        return Response(content=bundle.files[_manifest_key], media_type="application/json")

    # Generic fallback for any other static asset in the bundle (e.g. JSX files
    # shipped by ReactRuntime). Resolved by filename match; mime type is
    # inferred from the extension. Path traversal is prevented because we
    # only ever look up by exact filename in bundle.files.
    _MEDIA = {
        ".jsx": "application/javascript",
        ".js": "application/javascript",
        ".css": "text/css",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".map": "application/json",
    }

    @app.get("/favicon.ico")
    def favicon() -> Any:
        # Browsers auto-request this on every page load. The bundle
        # doesn't ship one, so a quiet 204 keeps the dev console clean.
        return Response(status_code=204)

    @app.get("/{name:path}")
    def static_asset(name: str) -> Any:
        # Allow nested paths (e.g. ``vendor/react.production.min.js``)
        # but reject absolute paths or ``..`` traversal attempts.
        if (
            name
            and name in bundle.files
            and not name.startswith("/")
            and ".." not in name.split("/")
        ):
            content = bundle.files[name]
            ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
            mime = _MEDIA.get(ext, "application/octet-stream")
            if isinstance(content, bytes):
                return Response(content=content, media_type=mime)
            return Response(content=content, media_type=mime)
        raise HTTPException(status_code=404, detail="Not Found")

    @app.post("/responses")
    async def responses(request: Request) -> Any:
        body = await request.json()
        payload = body.get("responses") or {}
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="responses must be an object")
        response_id = backend.store_response(survey_id, payload)
        return JSONResponse({"ok": True, "response_id": response_id})

    @app.post("/quota-check")
    async def quota_check(request: Request) -> Any:
        body = await request.json()
        ok = backend.increment_quota(
            survey_id=survey_id,
            variable=body.get("variable", ""),
            value=body.get("value"),
        )
        return JSONResponse({"ok": ok})

    return app


@dataclass(slots=True)
class LocalServer:
    """Background thread that runs uvicorn on a chosen port."""

    app: Any
    host: str = "0.0.0.0"
    port: int = 0
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _server: Any = field(default=None, init=False, repr=False)

    def start(self, ready_timeout: float = 5.0) -> str:
        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "uvicorn is required for the local frontend. Install with 'pip install siamang[server]'."
            ) from exc

        if self.port == 0:
            self.port = _pick_free_port()

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        self._wait_until_ready(ready_timeout)
        return f"http://{self.host}:{self.port}"

    def _wait_until_ready(self, timeout: float) -> None:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                try:
                    sock.connect((self.host, self.port))
                    return
                except OSError:
                    time.sleep(0.05)
        raise RuntimeError(
            f"Server did not become ready on {self.host}:{self.port} within {timeout}s."
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)

    def wait(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)


@dataclass(slots=True)
class LocalFrontend(FrontendAdapter):
    name: str = "local"
    host: str = "0.0.0.0"
    port: int = 0
    open_browser: bool = False
    _server: LocalServer | None = field(default=None, init=False, repr=False)

    def publish(self, bundle: "SurveyBundle", config: "BackendConfig") -> str:
        from siamang.deploy.backends.local import LocalBackend

        backend = config.internal.get("backend_ref")
        if backend is None:
            backend = LocalBackend(path=Path(config.internal.get("db_path", "survey.db")))
        app = build_app(bundle, backend, config.survey_id)
        server = LocalServer(app=app, host=self.host, port=self.port)
        url = server.start()
        self._server = server
        if self.open_browser:
            import webbrowser

            webbrowser.open(url)
        return url

    def stop(self) -> None:
        if self._server is not None:
            self._server.stop()
