"""UIConfig — visual settings for the deployed survey."""

from __future__ import annotations

from dataclasses import dataclass

_DENSITY_VALUES = {"compact", "comfortable", "spacious"}
_FONT_PAIR_VALUES = {"serif", "sans", "mixed"}
_LOGO_POSITIONS = {"left", "right", "center"}
_QUESTION_STYLES = {"plain", "divided", "carded", "accent"}
_FONT_PRESET_VALUES = {"academic", "modern", "humanist"}


# ─── Font preset definitions ─────────────────────────────────────────────────
# Each preset defines body, heading, and UI font stacks plus a Google Fonts URL.

FONT_PRESETS: dict[str, dict[str, str]] = {
    "academic": {
        "body": '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif',
        "heading": '"Source Serif 4", "Charter", Georgia, serif',
        "ui": '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap",
    },
    "modern": {
        "body": '"Inter", "Helvetica Neue", system-ui, -apple-system, sans-serif',
        "heading": '"Inter", "Helvetica Neue", system-ui, sans-serif',
        "ui": '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    },
    "humanist": {
        "body": '"Nunito", "Segoe UI", system-ui, sans-serif',
        "heading": '"Nunito", "Segoe UI", system-ui, sans-serif',
        "ui": '"Nunito", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google_fonts": "https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700&display=swap",
    },
}


@dataclass(frozen=True, slots=True)
class UIConfig:
    """Visual settings consumed by the theme + runtime adapters.

    The defaults aim for a calm, research-grade look: serif body type,
    narrow measure, single accent, comfortable spacing. Override any field
    for brand-specific surveys or pick one of the
    :data:`siamang.frontend.theme.presets.THEME_PRESETS` entries.

    Font presets:
        - ``"academic"`` — Source Serif 4 body + Inter UI (default)
        - ``"modern"`` — Inter everywhere, clean geometric sans
        - ``"humanist"`` — Nunito, friendly rounded sans-serif
    """

    # --- palette ----------------------------------------------------------
    primary_color: str = "#2c5f8a"
    accent_color: str | None = None  # falls back to primary_color
    background_color: str = "#fbfbfb"
    surface_color: str = "#ffffff"  # cards / panels
    text_color: str = "#1a1a1a"
    muted_text_color: str = "#5a5a5a"
    border_color: str = "#e6e4df"
    error_color: str = "#b3261e"
    error_soft_color: str = "#fdf1f0"

    # --- typography -------------------------------------------------------
    font_preset: str = "academic"  # "academic" | "modern" | "humanist"
    font_family: str = '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif'
    heading_font_family: str | None = None  # None -> mirrors body font
    ui_font_family: str = '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif'
    mono_font_family: str = '"JetBrains Mono", "Menlo", "Consolas", monospace'
    font_size: str = "15.5px"
    line_height: str = "1.6"
    font_pair: str = "serif"  # "serif" | "sans" | "mixed"

    # --- layout / density -------------------------------------------------
    width: str = "700px"
    radius: str = "4px"
    density: str = "comfortable"  # "compact" | "comfortable" | "spacious"
    question_style: str = "plain"  # "plain" | "divided" | "carded" | "accent"

    # --- header / branding ------------------------------------------------
    logo_url: str | None = None
    logo_text: str | None = None  # short text shown when logo_url is unset
    logo_position: str = "left"  # "left" | "right" | "center"
    show_title: bool = True
    institution_name: str | None = None
    study_subtitle: str | None = None
    show_section_numbers: bool = True
    show_progress_text: bool = True
    estimated_minutes: int | None = None

    # --- footer -----------------------------------------------------------
    privacy_url: str | None = None
    contact_email: str | None = None
    ethics_statement: str | None = None

    # --- overrides --------------------------------------------------------
    custom_css: str | None = None

    # --- i18n UI strings ---------------------------------------------------
    next_button_text: str | None = None
    prev_button_text: str | None = None
    submit_button_text: str | None = None
    submitting_text: str | None = None
    required_text: str | None = None
    saving_text: str | None = None
    select_placeholder: str | None = None
    of_text: str | None = None
    selected_text: str | None = None
    resume_title: str | None = None
    resume_action: str | None = None
    restart_action: str | None = None
    page_text: str | None = None
    of_total_text: str | None = None
    retry_title: str | None = None
    retry_body: str | None = None
    retry_action: str | None = None
    save_local_action: str | None = None
    completion_title: str | None = None
    completion_body: str | None = None

    # --- progress style -------------------------------------------------
    progress_style: str = "bar"  # "bar" | "dots" | "both"

    # --- theme default --------------------------------------------------
    default_theme: str = "light"  # "light" | "dark" | "system"

    # --- redirect -------------------------------------------------------
    redirect_url: str | None = None

    # --- color palette extras -------------------------------------------
    warn_color: str = "#9a6a1a"

    # --- navigation -----------------------------------------------------
    allow_back: bool = True  # Show the "Previous" button between pages.

    # --- analytics ------------------------------------------------------
    enable_analytics: bool = False  # Injects Vercel Analytics script

    # --- access code ----------------------------------------------------
    require_access_code: bool = False
    access_codes: list[str] | None = None  # None or list of valid codes
    access_title: str | None = None
    access_body: str | None = None
    access_placeholder: str | None = None
    access_button: str | None = None

    def __post_init__(self) -> None:
        if self.logo_position not in _LOGO_POSITIONS:
            raise ValueError(f"logo_position must be one of: {sorted(_LOGO_POSITIONS)}.")
        if self.density not in _DENSITY_VALUES:
            raise ValueError(f"density must be one of: {sorted(_DENSITY_VALUES)}.")
        if self.font_pair not in _FONT_PAIR_VALUES:
            raise ValueError(f"font_pair must be one of: {sorted(_FONT_PAIR_VALUES)}.")
        if self.question_style not in _QUESTION_STYLES:
            raise ValueError(f"question_style must be one of: {sorted(_QUESTION_STYLES)}.")
        if self.font_preset not in _FONT_PRESET_VALUES:
            raise ValueError(f"font_preset must be one of: {sorted(_FONT_PRESET_VALUES)}.")

    @property
    def effective_accent(self) -> str:
        return self.accent_color or self.primary_color

    @property
    def effective_heading_font(self) -> str:
        if self.heading_font_family:
            return self.heading_font_family
        # Use font preset heading if no explicit override
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        return preset["heading"]

    @property
    def effective_body_font(self) -> str:
        """Body font — uses font_preset unless font_family was explicitly changed."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        # If user set a custom font_family different from the default, respect it
        default_body = '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif'
        if self.font_family != default_body:
            return self.font_family
        return preset["body"]

    @property
    def effective_ui_font(self) -> str:
        """UI font — uses font_preset unless ui_font_family was explicitly changed."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        default_ui = '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif'
        if self.ui_font_family != default_ui:
            return self.ui_font_family
        return preset["ui"]

    @property
    def effective_google_fonts_url(self) -> str:
        """Google Fonts URL for the active font preset."""
        preset = FONT_PRESETS.get(self.font_preset, FONT_PRESETS["academic"])
        return preset["google_fonts"]

    @property
    def effective_logo_text(self) -> str:
        if self.logo_text:
            return self.logo_text
        if self.institution_name:
            words = [w for w in self.institution_name.split() if w and w[0].isalpha()]
            initials = "".join(w[0].upper() for w in words[:2]) or self.institution_name[:2].upper()
            return initials
        return ""
