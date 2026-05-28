"""Built-in UIConfig presets.

The ``default`` preset uses a calm research-grade serif look intended for
academic studies. Other presets cover dark mode, a sans-serif Inter pair for
public-facing surveys, and a maximum-contrast accessible variant.

Font presets (``font_preset``):
    - ``"academic"`` — Source Serif 4 body + Inter UI
    - ``"modern"`` — Inter everywhere, clean geometric sans
    - ``"humanist"`` — Nunito, friendly rounded sans-serif
"""

from __future__ import annotations

from siamang.frontend.theme.ui_config import UIConfig

THEME_PRESETS: dict[str, UIConfig] = {
    # research-grade serif (the new default)
    "default": UIConfig(),
    # alias for clarity in user code
    "academic": UIConfig(
        institution_name=None,
        font_preset="academic",
        font_pair="serif",
        primary_color="#2c5f8a",
        density="comfortable",
        width="680px",
    ),
    # academic, dark
    "dark": UIConfig(
        primary_color="#7aa8d6",
        accent_color="#9ec5e8",
        background_color="#10131a",
        surface_color="#171b24",
        text_color="#e7e9ee",
        muted_text_color="#9aa1ad",
        border_color="#262b36",
        font_preset="academic",
        font_pair="serif",
    ),
    # modern sans-serif, suitable for public-facing surveys
    "modern": UIConfig(
        primary_color="#1f5fd6",
        accent_color="#1f5fd6",
        background_color="#ffffff",
        surface_color="#ffffff",
        text_color="#101418",
        muted_text_color="#5a6370",
        border_color="#dfe3ea",
        font_preset="modern",
        font_pair="sans",
        font_size="16px",
        line_height="1.6",
        radius="8px",
        density="spacious",
        width="720px",
    ),
    # Friendly / humanist — good for public-facing or UX research
    "humanist": UIConfig(
        primary_color="#3a7d5c",
        accent_color="#3a7d5c",
        background_color="#fafcfa",
        surface_color="#ffffff",
        text_color="#1a2e1a",
        muted_text_color="#4a6a4a",
        border_color="#d8e8d8",
        font_preset="humanist",
        font_pair="sans",
        font_size="16px",
        line_height="1.65",
        radius="10px",
        density="spacious",
        width="720px",
    ),
    # WCAG AAA-leaning, maximum contrast
    "high_contrast": UIConfig(
        primary_color="#000000",
        accent_color="#0044cc",
        background_color="#ffffff",
        surface_color="#ffffff",
        text_color="#000000",
        muted_text_color="#222222",
        border_color="#000000",
        font_preset="modern",
        font_pair="sans",
        font_size="18px",
        line_height="1.7",
        radius="2px",
        density="spacious",
    ),
}


def get_preset(name: str) -> UIConfig:
    if name not in THEME_PRESETS:
        available = ", ".join(sorted(THEME_PRESETS))
        raise KeyError(f"Unknown theme preset '{name}'. Available: {available}.")
    return THEME_PRESETS[name]
