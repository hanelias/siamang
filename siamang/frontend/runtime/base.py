"""Abstract runtime adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from siamang.frontend.schema import SurveySchema
from siamang.frontend.theme.ui_config import UIConfig

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire


@dataclass(frozen=True, slots=True)
class RuntimeRenderContext:
    """Inputs required by every runtime adapter to produce HTML.

    ``survey`` is optional; only runtimes that emit the questionnaire on the
    client side (the React runtime) need direct access to the live
    :class:`Questionnaire` objects. SurveyJS-style runtimes work from the
    already-compiled :class:`SurveySchema` alone.
    """

    schema: SurveySchema
    ui: UIConfig
    css_href: str = "style.css"
    env_src: str = "env.js"
    survey_id: str | None = None
    survey: Questionnaire | None = None


class RuntimeAdapter(ABC):
    """A pluggable rendering engine (SurveyJS, React, custom JS, etc.)."""

    name: str

    @abstractmethod
    def render_html(self, context: RuntimeRenderContext) -> str:
        """Return the contents of ``index.html`` for the bundle."""

    @abstractmethod
    def render_closed_page(self, context: RuntimeRenderContext, reason: str) -> str:
        """Return the contents of ``closed.html`` (quota full / deadline / closed)."""

    def static_assets(self) -> dict[str, str | bytes]:
        """Return any additional files (default: none)."""

        return {}

    def stylesheet(self, context: RuntimeRenderContext) -> str | None:
        """Return CSS for the bundle, or ``None`` to use the default theme.

        Runtimes that ship their own design system (the React runtime)
        override this and return a full stylesheet. The builder will write
        whatever this returns to ``style.css`` instead of
        :func:`siamang.frontend.theme.css.compile_css`.
        """

        return None
