"""Adapter interfaces for deployment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from siamang.deploy.backend_config import BackendConfig
    from siamang.frontend.bundle import SurveyBundle
    from siamang.frontend.schema import SurveySchema


class BackendAdapter(ABC):
    """Storage backend (SQLite, Supabase, Sheets, ...).

    Implementations create the data store, accept responses, enforce quotas,
    and return collected responses as a pandas DataFrame.
    """

    name: str

    @abstractmethod
    def provision(self, schema: SurveySchema) -> BackendConfig:
        """Create data-store structures and return a frontend-safe config."""

    @abstractmethod
    def get_responses(self, survey_id: str) -> pd.DataFrame:
        """Fetch accumulated responses as a DataFrame."""

    @abstractmethod
    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Return True if the quota cell still has capacity."""


class FrontendAdapter(ABC):
    """Hosting target (local FastAPI, Vercel, Netlify, ...)."""

    name: str

    @abstractmethod
    def publish(self, bundle: SurveyBundle, config: BackendConfig) -> str:
        """Upload/serve the bundle and return its public URL."""
