"""Deployment pipeline: compile -> provision -> build bundle -> publish."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from siamang.deploy.base import BackendAdapter, FrontendAdapter
from siamang.deploy.result import DeployResult
from siamang.frontend.builder import FrontendBuilder
from siamang.frontend.client import (
    BackendClientTemplate,
    ClientEnv,
    GoogleSheetsClientTemplate,
    LocalClientTemplate,
    SupabaseClientTemplate,
)
from siamang.frontend.compiler import compile_questionnaire

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire


_CLIENT_TEMPLATES: dict[str, type[BackendClientTemplate]] = {
    "local": LocalClientTemplate,
    "supabase": SupabaseClientTemplate,
    "gsheets": GoogleSheetsClientTemplate,
}


def _client_for(backend_name: str) -> BackendClientTemplate:
    template = _CLIENT_TEMPLATES.get(backend_name)
    if template is None:
        available = ", ".join(sorted(_CLIENT_TEMPLATES))
        raise NotImplementedError(
            f"No frontend client template for backend '{backend_name}'. Available: {available}."
        )
    return template()


@dataclass(slots=True)
class DeployPipeline:
    """Wires a Questionnaire -> backend.provision -> builder.build -> frontend.publish."""

    backend: BackendAdapter
    frontend: FrontendAdapter
    builder: FrontendBuilder

    def run(
        self,
        survey: "Questionnaire",
        *,
        options: dict[str, Any] | None = None,
    ) -> DeployResult:
        schema = compile_questionnaire(survey, options=options)
        backend_config = self.backend.provision(schema)
        client = _client_for(self.backend.name)
        env = ClientEnv(
            survey_id=backend_config.survey_id,
            backend=self.backend.name,
            settings=dict(backend_config.settings),
        )
        bundle = self.builder.build(schema, client=client, env=env, survey=survey)

        # When deploying to Vercel, analytics can be enabled via UIConfig.enable_analytics
        # The ReactRuntime will inject the Vercel Analytics script automatically.

        url = self.frontend.publish(bundle, backend_config)
        return DeployResult(
            url=url,
            backend=self.backend.name,
            frontend=self.frontend.name,
            survey_id=backend_config.survey_id,
            dashboard=backend_config.dashboard_url,
            deployed_at=datetime.now(timezone.utc),
            backend_ref=self.backend,
            frontend_ref=self.frontend,
        )
