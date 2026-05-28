"""Builder that assembles a `SurveyBundle` from a `SurveySchema` and parts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from siamang.frontend import constants
from siamang.frontend.bundle import SurveyBundle
from siamang.frontend.client.base import BackendClientTemplate, ClientEnv
from siamang.frontend.runtime.base import RuntimeAdapter, RuntimeRenderContext
from siamang.frontend.runtime.surveyjs import SurveyJSRuntime
from siamang.frontend.schema import SurveySchema
from siamang.frontend.theme.css import compile_css
from siamang.frontend.theme.ui_config import UIConfig

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire


@dataclass(frozen=True, slots=True)
class FrontendBuilder:
    """Compose a deployable bundle from a schema and pluggable parts.

    Every field is optional; sensible defaults are used.
    Swap any field to change one piece of the constructor.
    """

    runtime: RuntimeAdapter = None  # type: ignore[assignment]
    ui: UIConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime", self.runtime or SurveyJSRuntime())
        object.__setattr__(self, "ui", self.ui or UIConfig())

    def build(
        self,
        schema: SurveySchema,
        *,
        client: BackendClientTemplate,
        env: ClientEnv,
        survey: Questionnaire | None = None,
    ) -> SurveyBundle:
        """Render every artefact and return the assembled bundle.

        ``survey`` is optional; runtimes that need the live Questionnaire
        (e.g. :class:`ReactRuntime`) require it. SurveyJS-style runtimes
        ignore it and work from ``schema`` alone.
        """

        context = RuntimeRenderContext(
            schema=schema,
            ui=self.ui,
            css_href="style.css",
            env_src="env.js",
            survey_id=env.survey_id,
            survey=survey,
        )

        # Runtime can provide its own stylesheet (full design system); the
        # fallback is the minimal SurveyJS-targeted theme.
        css = self.runtime.stylesheet(context)
        if css is None:
            css = compile_css(self.ui)

        env_js = client.render_env_js(env)
        index_html = self.runtime.render_html(context)
        closed_html = self.runtime.render_closed_page(context, reason="closed")

        manifest = _build_manifest(schema, env, client, self.runtime)

        files: dict[str, str | bytes] = {
            "index.html": index_html,
            "style.css": css,
            "env.js": env_js,
            "closed.html": closed_html,
            "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        }
        for name, content in self.runtime.static_assets().items():
            files.setdefault(name, content)

        bundle = SurveyBundle(files=files, manifest=manifest)
        return bundle.with_hashed_filenames()


def _build_manifest(
    schema: SurveySchema,
    env: ClientEnv,
    client: BackendClientTemplate,
    runtime: RuntimeAdapter,
) -> dict:
    schema_payload = schema.to_dict()
    schema_hash = hashlib.sha256(
        json.dumps(schema_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "format_version": constants.BUNDLE_FORMAT_VERSION,
        "survey_id": env.survey_id,
        "title": schema.title,
        "language": schema.language,
        "runtime": runtime.name,
        "client": client.name,
        "backend": env.backend,
        "surveyjs_version": getattr(runtime, "version", None),
        "schema_hash": schema_hash,
        "built_at": datetime.now(UTC).isoformat(),
    }
