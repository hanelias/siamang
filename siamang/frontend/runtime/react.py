"""ReactRuntime — renders survey questions client-side with React 18 from CDN.

Unlike SurveyJSRuntime, this adapter does not delegate question rendering
to a third-party engine. It ships pre-compiled JS components and a full
design-system stylesheet.

JSX is pre-compiled to JS at bundle-build time so @babel/standalone is NOT
needed in the browser.
"""

from __future__ import annotations

import hashlib
import html
import json
from importlib import resources
from string import Template
from typing import Any

from siamang.frontend.compiler.react import compile_react_payload
from siamang.frontend.runtime.base import RuntimeAdapter, RuntimeRenderContext

_CLOSED_REASONS = {
    "deadline": (
        "Survey closed",
        "Thank you. This survey is no longer accepting responses.",
    ),
    "quota_full": (
        "Thank you",
        "We have already reached our target sample for participants like you.",
    ),
    "closed": ("Survey closed", "This survey is no longer accepting responses."),
}

# SRI integrity hashes for known CDN versions
# Generated with: openssl dgst -sha384 -binary <file> | openssl base64 -A
_REACT_INTEGRITY = {
    "18.3.1": {
        "react": "sha384-DGyLxAyjq0f9SPpVevD6IgztCFlnMF6oW/XQGmfe+IsZ8TqEiDrcHkMLKI6fiB/Z",
        "react-dom": "sha384-gTGxhz21lVGYNMcdJOyq01Edg0jhn/c22nsx0kyqP0TxaV5WVdsSH1fSDUf5YJj1",
    }
}

# Template for Vercel Analytics snippet (only injected on Vercel deploys)
_VERCEL_ANALYTICS_SCRIPT = """
<script defer src="/_vercel/insights/script.js"></script>
"""


def _load_template(filename: str) -> Template:
    pkg = "siamang.frontend.templates.react"
    text = resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")
    return Template(text)


def _load_asset(filename: str) -> str:
    pkg = "siamang.frontend.templates.react"
    return resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")


def _load_prebuilt_bundle() -> str | None:
    """Load precompiled runtime bundle shipped in the wheel, if present."""
    pkg = "siamang.frontend.templates.react"
    path = resources.files(pkg).joinpath("dist/bundle.js")
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _compute_sri_hash(content: str | bytes, algorithm: str = "sha384") -> str:
    """Compute Subresource Integrity hash for given content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    h = hashlib.new(algorithm, content)
    return f"{algorithm}-{h.digest()}"


class ReactRuntime(RuntimeAdapter):
    """Self-contained React runtime — no SurveyJS dependency, no Babel in browser."""

    name = "react"

    def __init__(self, precompile: bool = True) -> None:
        self._index_template = _load_template("index.html.tpl")
        self._style_template = _load_template("style.css.tpl")
        self._closed_template = _load_template("closed.html.tpl")
        # Backward-compat arg retained for API stability; runtime always
        # serves packaged prebuilt bundle.js.
        _ = precompile
        # Cache: bundled source + whether already JS.
        self._bundle_src: str | None = None
        self._compiled_ok: bool | None = None  # None = not yet attempted

    def _get_or_compile(self) -> tuple[str, bool]:
        """Return ``(bundle_source, compiled_to_js)`` from packaged assets."""
        if self._compiled_ok is not None:
            assert self._bundle_src is not None
            return self._bundle_src, self._compiled_ok

        prebuilt = _load_prebuilt_bundle()
        if prebuilt:
            self._bundle_src = prebuilt
            self._compiled_ok = True
            return prebuilt, True
        raise RuntimeError(
            "React runtime bundle is missing (expected templates/react/dist/bundle.js). "
            "Reinstall siamang or rebuild the package so the prebuilt bundle is included."
        )

    def render_html(self, context: RuntimeRenderContext) -> str:
        if context.survey is None:
            raise ValueError(
                "ReactRuntime needs the live Questionnaire object on the render "
                "context. Pass `survey=` to FrontendBuilder.build()."
            )

        payload = compile_react_payload(
            context.survey,
            ui=context.ui,
            options={
                "language": context.schema.language,
                "description": context.schema.description,
                "show_progress": context.schema.show_progress,
                "completion_text": context.schema.completion_text,
            },
        )

        # Get SRI hashes for the CDN version
        version_integrity = _REACT_INTEGRITY.get("18.3.1", {})
        react_integrity = version_integrity.get("react", "")
        react_dom_integrity = version_integrity.get("react-dom", "")

        # Determine default theme
        theme = getattr(context.ui, "default_theme", "light")
        if theme == "system":
            theme = ""  # Let CSS prefers-color-scheme handle it

        # Add analytics for Vercel deploys
        analytics_script = ""
        if getattr(context.ui, "enable_analytics", False):
            analytics_script = _VERCEL_ANALYTICS_SCRIPT

        self._get_or_compile()
        scripts_block = '<script src="bundle.js" defer></script>'

        return self._index_template.substitute(
            language=html.escape(context.schema.language),
            title=html.escape(context.schema.title),
            density=html.escape(context.ui.density),
            qstyle=html.escape(context.ui.question_style),
            theme=html.escape(theme),
            react_integrity=html.escape(react_integrity),
            react_dom_integrity=html.escape(react_dom_integrity),
            survey_json=json.dumps(payload["SURVEY"], ensure_ascii=False),
            pages_json=json.dumps(payload["PAGES"], ensure_ascii=False),
            analytics_script=analytics_script,
            scripts_block=scripts_block,
            google_fonts_url=html.escape(context.ui.effective_google_fonts_url),
        )

    def render_closed_page(self, context: RuntimeRenderContext, reason: str) -> str:
        heading, message = _CLOSED_REASONS.get(reason, _CLOSED_REASONS["closed"])
        return self._closed_template.substitute(
            language=html.escape(context.schema.language),
            title=html.escape(context.schema.title),
            heading=html.escape(heading),
            message=html.escape(message),
        )

    def stylesheet(self, context: RuntimeRenderContext) -> str:
        ui = context.ui
        tokens: dict[str, Any] = {
            "primary": ui.primary_color,
            "accent": ui.effective_accent,
            "bg": ui.background_color,
            "surface": ui.surface_color,
            "text": ui.text_color,
            "muted": ui.muted_text_color,
            "border": ui.border_color,
            "font": ui.effective_body_font,
            "heading_font": ui.effective_heading_font,
            "ui_font": ui.effective_ui_font,
            "mono": ui.mono_font_family,
            "font_size": ui.font_size,
            "line_height": ui.line_height,
            "width": ui.width,
            "radius": ui.radius,
            "error": ui.error_color,
            "error_soft": ui.error_soft_color,
            "warn": ui.warn_color,
        }
        css = self._style_template.substitute(tokens)
        if ui.custom_css:
            css = css + "\n/* user overrides */\n" + ui.custom_css
        return css

    def static_assets(self) -> dict[str, str | bytes]:
        bundle_src, compiled_ok = self._get_or_compile()
        assets: dict[str, str | bytes] = {
            # React UMD vendored locally — no unpkg.com round-trip on
            # first paint. Loaded from `vendor/` by index.html.tpl.
            "vendor/react.production.min.js": _load_asset("vendor/react.production.min.js"),
            "vendor/react-dom.production.min.js": _load_asset("vendor/react-dom.production.min.js"),
        }
        if compiled_ok:
            assets["bundle.js"] = bundle_src
        return assets
