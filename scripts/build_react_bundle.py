#!/usr/bin/env python3
"""Rebuild the React-runtime bundle shipped inside the wheel.

Reads:
    siamang/frontend/templates/react/store.jsx
    siamang/frontend/templates/react/visibility.jsx
    siamang/frontend/templates/react/hooks.jsx
    siamang/frontend/templates/react/questions.jsx
    siamang/frontend/templates/react/app.jsx

Writes:
    siamang/frontend/templates/react/dist/bundle.js

Pipeline:
    1. Concatenate the source files in dependency order (stripping each
       file's own `const { useState, … } = React;` destructure and
       emitting a single shared one at the top).
    2. Pipe through `sucrase --transforms jsx --production` to convert
       JSX → JS without devtool annotations.
    3. Pipe through `esbuild --minify --target=es2020` to drop the
       file size and improve browser parse/execute time.

Requires Node ≥ 18 with `sucrase` and `esbuild` available via `npx`
(installed once with `npm install -g sucrase esbuild`).

Run this whenever you edit any of the JSX source files. The resulting
`dist/bundle.js` is committed to the repo and shipped in the wheel;
the React runtime at survey-render time just reads it verbatim — no
Node needed at runtime.

Usage:
    python scripts/build_react_bundle.py            # build + write
    python scripts/build_react_bundle.py --check    # build, fail if
                                                    # bundle is stale
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSX_DIR = ROOT / "siamang" / "frontend" / "templates" / "react"
OUT = JSX_DIR / "dist" / "bundle.js"

_DESTRUCTURE_RE = re.compile(r"^\s*const\s*\{[^}]+\}\s*=\s*React\s*;\s*\n", re.MULTILINE)

_PREAMBLE = (
    "/* siamang bundled runtime — produced by scripts/build_react_bundle.py.\n"
    "   Source order: store.jsx → visibility.jsx → hooks.jsx → questions.jsx → app.jsx */\n"
    "const { useState, useRef, useEffect, useMemo, useCallback } = React;\n\n"
)

# Source files in dependency order
_SOURCE_FILES = [
    "store.jsx",
    "visibility.jsx",
    "hooks.jsx",
    "questions.jsx",
    "app.jsx",
]


def _concat_jsx() -> str:
    parts = []
    for filename in _SOURCE_FILES:
        src = (JSX_DIR / filename).read_text(encoding="utf-8")
        src = _DESTRUCTURE_RE.sub("", src, count=1)
        parts.append(f"\n/* ─── {filename} ─── */\n\n{src}")
    return _PREAMBLE + "\n".join(parts)


def _run(cmd: list[str], *, input_text: str | None = None, cwd: Path | None = None) -> str:
    """Run a subprocess, return stdout, raise with a useful message on failure."""
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=cwd,
            env={**os.environ, "NODE_PATH": ""},
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"\n[build] {cmd[0]!r} not found on PATH. Install Node and run\n"
            f"        npm install -g sucrase esbuild\n"
            f"        before retrying.\nOriginal error: {exc}"
        ) from exc
    if result.returncode != 0:
        raise SystemExit(
            f"\n[build] {' '.join(cmd)} failed (exit {result.returncode}).\n"
            f"--- stderr ---\n{result.stderr}\n--- stdout ---\n{result.stdout}\n"
        )
    return result.stdout


def _transpile_with_sucrase(combined: str) -> str:
    """Convert JSX → JS. Sucrase needs a directory, so we make a temp one."""
    with (
        tempfile.TemporaryDirectory(prefix="sm-jsx-src-") as src_dir,
        tempfile.TemporaryDirectory(prefix="sm-jsx-out-") as out_dir,
    ):
        jsx_path = Path(src_dir) / "bundle.jsx"
        jsx_path.write_text(combined, encoding="utf-8")
        _run(
            [
                "npx",
                "--yes",
                "sucrase",
                src_dir,
                "--transforms",
                "jsx",
                "--production",
                "--out-dir",
                out_dir,
            ]
        )
        return (Path(out_dir) / "bundle.js").read_text(encoding="utf-8")


def _minify_with_esbuild(js: str) -> str:
    """Minify the transpiled JS. esbuild reads from stdin with --loader=js."""
    return _run(
        [
            "npx",
            "--yes",
            "esbuild",
            "--minify",
            "--target=es2020",
            "--loader=js",
        ],
        input_text=js,
    )


def build() -> str:
    combined = _concat_jsx()
    transpiled = _transpile_with_sucrase(combined)
    minified = _minify_with_esbuild(transpiled)
    if not minified.strip():
        raise SystemExit("[build] esbuild produced empty output, refusing to write.")
    return minified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="build but don't write; fail with exit code 2 if the existing "
        "dist/bundle.js differs (CI-friendly drift detection).",
    )
    args = parser.parse_args(argv)

    if not shutil.which("npx"):
        raise SystemExit(
            "[build] `npx` not found on PATH. Install Node (>= 18) and run\n"
            "        npm install -g sucrase esbuild\n"
            "        before retrying."
        )

    new_bundle = build()

    if args.check:
        if not OUT.exists():
            print("[build] dist/bundle.js is missing.", file=sys.stderr)
            return 2
        existing = OUT.read_text(encoding="utf-8")
        if existing.strip() != new_bundle.strip():
            print(
                "[build] dist/bundle.js is stale — re-run "
                "`python scripts/build_react_bundle.py` and commit the result.",
                file=sys.stderr,
            )
            return 2
        print(f"[build] dist/bundle.js is up to date ({len(existing)} bytes).")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new_bundle, encoding="utf-8")
    print(f"[build] wrote {OUT.relative_to(ROOT)} ({len(new_bundle)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
