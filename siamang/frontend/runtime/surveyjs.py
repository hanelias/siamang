"""SurveyJS-based runtime adapter (CDN-loaded engine)."""

from __future__ import annotations

import html
import json
from importlib import resources
from string import Template

from siamang.frontend import constants
from siamang.frontend.runtime.base import RuntimeAdapter, RuntimeRenderContext

_CLOSED_REASONS = {
    "deadline": (
        "Survey closed",
        "Thank you for your interest. This survey is no longer accepting responses.",
    ),
    "quota_full": (
        "Thank you",
        "We have already reached our target sample for participants like you.",
    ),
    "closed": ("Survey closed", "This survey is no longer accepting responses."),
}


def _load_template(filename: str) -> Template:
    pkg = "siamang.frontend.templates"
    text = resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")
    return Template(text)


class SurveyJSRuntime(RuntimeAdapter):
    """Renders the bundle around the SurveyJS engine loaded from CDN."""

    name = "surveyjs"

    def __init__(self, version: str = constants.SURVEYJS_VERSION) -> None:
        self.version = version
        self._index_template = _load_template("index.html.tpl")
        self._closed_template = _load_template("closed.html.tpl")

    def render_html(self, context: RuntimeRenderContext) -> str:
        schema_json = json.dumps(context.schema.to_surveyjs(), ensure_ascii=False)
        return self._index_template.substitute(
            language=html.escape(context.schema.language),
            title=html.escape(context.schema.title),
            surveyjs_js=constants.surveyjs_js_url(self.version),
            surveyjs_ui=constants.surveyjs_ui_url(self.version),
            surveyjs_css=constants.surveyjs_css_url(self.version),
            css_href=context.css_href,
            env_src=context.env_src,
            schema_json=schema_json,
            header_html=_header_html(context),
            progress_html=_progress_html(context),
            footer_html=_footer_html(context),
        )

    def render_closed_page(self, context: RuntimeRenderContext, reason: str) -> str:
        heading, message = _CLOSED_REASONS.get(reason, _CLOSED_REASONS["closed"])
        return self._closed_template.substitute(
            language=html.escape(context.schema.language),
            title=html.escape(context.schema.title),
            css_href=context.css_href,
            heading=html.escape(heading),
            message=html.escape(message),
        )


def _header_html(context: RuntimeRenderContext) -> str:
    ui = context.ui
    schema = context.schema
    show_logo = bool(ui.logo_url)
    show_title = bool(ui.show_title)
    show_institution = bool(ui.institution_name)
    show_subtitle = bool(ui.study_subtitle or schema.description)

    if not (show_logo or show_title or show_institution or show_subtitle):
        return ""

    parts: list[str] = [f'<header class="siamang-header {html.escape(ui.logo_position)}">']
    if show_logo:
        parts.append(
            f'<img class="siamang-header__logo" src="{html.escape(ui.logo_url or "")}" '
            'alt="" role="presentation">'
        )
    parts.append('<div class="siamang-header__text">')
    if show_title:
        parts.append(f'<h1 class="siamang-header__title">{html.escape(schema.title)}</h1>')
    if show_institution:
        parts.append(
            f'<p class="siamang-header__institution">{html.escape(ui.institution_name or "")}</p>'
        )
    if show_subtitle:
        subtitle = ui.study_subtitle or (schema.description or "")
        parts.append(f'<p class="siamang-header__subtitle">{html.escape(subtitle)}</p>')
    parts.append("</div></header>")
    return "".join(parts)


def _progress_html(context: RuntimeRenderContext) -> str:
    if not context.schema.show_progress:
        return ""
    show_text = bool(context.ui.show_progress_text)
    text_block = (
        '<span id="siamang-progress-text" class="siamang-progress__text"></span>'
        if show_text
        else ""
    )
    return (
        '<div class="siamang-progress" role="status" aria-live="polite">'
        '<span class="siamang-progress__bar" aria-hidden="true">'
        '<span id="siamang-progress-fill" class="siamang-progress__fill"></span>'
        "</span>"
        f"{text_block}"
        "</div>"
    )


def _footer_html(context: RuntimeRenderContext) -> str:
    ui = context.ui
    fragments: list[str] = []

    if ui.ethics_statement:
        fragments.append(
            f'<p class="siamang-footer__ethics">{html.escape(ui.ethics_statement)}</p>'
        )

    links: list[str] = []
    if ui.institution_name:
        links.append(f"<span>{html.escape(ui.institution_name)}</span>")
    if ui.privacy_url:
        links.append(
            f'<a href="{html.escape(ui.privacy_url)}" rel="noopener" target="_blank">Privacy</a>'
        )
    if ui.contact_email:
        links.append(f'<a href="mailto:{html.escape(ui.contact_email)}">Contact</a>')
    if links:
        fragments.extend(links)

    if not fragments:
        return ""
    return '<footer class="siamang-footer">' + "".join(fragments) + "</footer>"
