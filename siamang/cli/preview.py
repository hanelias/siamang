"""`siamang preview` — boot the local React preview server."""

from __future__ import annotations

import shutil
import subprocess

from siamang.cli.loader import load_survey


def _report_build_path() -> None:
    """One-line diagnostic so the user can tell whether the fast
    (sucrase + esbuild minify) or the slow (@babel/standalone in
    browser) compile route is in use."""
    has_node = shutil.which("npx") is not None
    if not has_node:
        print(
            "  [react] no `npx` on PATH — bundle falls back to "
            "@babel/standalone in browser (slow first paint)"
        )
        return

    def _probe(cmd: list[str]) -> bool:
        try:
            return subprocess.run(cmd, capture_output=True, timeout=5).returncode == 0
        except Exception:
            return False

    has_sucrase = _probe(["npx", "sucrase", "--help"])
    has_esbuild = _probe(["npx", "esbuild", "--version"])

    if has_sucrase and has_esbuild:
        print("  [react] sucrase + esbuild minify available — fast path")
    elif has_sucrase:
        print(
            "  [react] sucrase available, esbuild not — `npm install -g esbuild` "
            "shrinks the bundle ~40%"
        )
    else:
        print(
            "  [react] sucrase not found — `npm install -g sucrase esbuild` "
            "for the fast compile path (current path: @babel/standalone in browser)"
        )


def run(
    path: str,
    attribute: str = "survey",
    port: int = 8000,
    open_browser: bool = False,
    db_path: str = "survey.db",
) -> int:
    survey = load_survey(path, attribute=attribute)
    result = survey.deploy(
        backend_kwargs={"path": db_path},
        frontend_kwargs={"port": port, "open_browser": open_browser},
    )
    print(f"Preview ready at {result.url}")
    print(f"  survey_id: {result.survey_id}")
    print(f"  dashboard: {result.dashboard}")
    _report_build_path()
    print("Press Ctrl+C to stop.")
    try:
        if result.frontend_ref is not None and hasattr(result.frontend_ref, "_server"):
            server = result.frontend_ref._server
            if server is not None:
                server.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if result.frontend_ref is not None and hasattr(result.frontend_ref, "stop"):
            result.frontend_ref.stop()
    return 0
