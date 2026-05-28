"""Deployment result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from siamang.deploy.base import BackendAdapter, FrontendAdapter


@dataclass(frozen=True, slots=True)
class DeployResult:
    """Outcome of ``Questionnaire.deploy()``.

    ``backend_ref`` and ``frontend_ref`` are kept so the caller can later
    invoke ``collect()`` without re-resolving adapters.
    """

    url: str
    backend: str
    frontend: str
    survey_id: str = ""
    dashboard: str | None = None
    deployed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    backend_ref: BackendAdapter | None = None
    frontend_ref: FrontendAdapter | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def collect(self) -> pd.DataFrame:
        if self.backend_ref is None:
            raise RuntimeError("DeployResult has no backend adapter; cannot collect().")
        return self.backend_ref.get_responses(self.survey_id)
