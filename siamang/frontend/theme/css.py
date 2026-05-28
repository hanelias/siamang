"""Compile UIConfig into a CSS string consumed by the runtime bundle.

The generated stylesheet:

- defines CSS custom properties (palette, typography, spacing) so SurveyJS
  classes can be tuned through ``custom_css`` if needed;
- styles the siamang-specific institutional header, progress strip,
  numbered section markers, and footer;
- overrides SurveyJS' ``defaultV2`` defaults to match the research-grade
  look (narrow measure, restrained typography, focus rings, larger Likert
  hit areas, accessible contrast).

The aim is a calm, scholarly survey page with WCAG-AA contrast and clear
focus states — not a flashy product onboarding flow.
"""

from __future__ import annotations

from siamang.frontend.theme.ui_config import UIConfig

_DENSITY_SPACING = {
    "compact": ("18px", "10px", "8px", "24px"),
    "comfortable": ("28px", "14px", "12px", "36px"),
    "spacious": ("40px", "18px", "16px", "48px"),
}


def _density_vars(density: str) -> dict[str, str]:
    section, gap, control, page = _DENSITY_SPACING[density]
    return {
        "section": section,
        "gap": gap,
        "control": control,
        "page": page,
    }


_CSS_TEMPLATE = """\
/* ── siamang theme — research-grade ─────────────────────────────────── */

:root {{
  --siamang-primary:        {primary};
  --siamang-accent:         {accent};
  --siamang-bg:             {background};
  --siamang-surface:        {surface};
  --siamang-text:           {text};
  --siamang-muted:          {muted};
  --siamang-border:         {border};
  --siamang-font:           {font};
  --siamang-heading-font:   {heading_font};
  --siamang-mono:           {mono};
  --siamang-font-size:      {font_size};
  --siamang-line-height:    {line_height};
  --siamang-width:          {width};
  --siamang-radius:         {radius};
  --siamang-section-gap:    {gap_section};
  --siamang-item-gap:       {gap_item};
  --siamang-control-pad:    {gap_control};
  --siamang-page-pad:       {gap_page};
  --siamang-focus-ring:     0 0 0 3px color-mix(in srgb, var(--siamang-accent) 35%, transparent);
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-siamang-force-light]) {{
    color-scheme: dark light;
  }}
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0;
  padding: 0;
  background: var(--siamang-bg);
  color: var(--siamang-text);
  font-family: var(--siamang-font);
  font-size: var(--siamang-font-size);
  line-height: var(--siamang-line-height);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}}

a {{
  color: var(--siamang-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}}
a:focus-visible {{ outline: none; box-shadow: var(--siamang-focus-ring); border-radius: 2px; }}

.siamang-skip-link {{
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--siamang-accent);
  color: #fff;
  padding: 8px 12px;
  z-index: 1000;
}}
.siamang-skip-link:focus {{ left: 8px; top: 8px; }}

#survey {{
  max-width: var(--siamang-width);
  margin: 0 auto;
  padding: var(--siamang-page-pad) 20px 64px;
}}

/* ── institutional header ──────────────────────────────────────────── */

.siamang-header {{
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  margin-bottom: var(--siamang-section-gap);
  border-bottom: 1px solid var(--siamang-border);
}}
.siamang-header.right     {{ flex-direction: row-reverse; text-align: right; }}
.siamang-header.center    {{ flex-direction: column; text-align: center; }}
.siamang-header__logo     {{ height: 44px; width: auto; flex-shrink: 0; }}
.siamang-header__text     {{ flex: 1; min-width: 0; }}
.siamang-header__title    {{
  font-family: var(--siamang-heading-font);
  font-size: 1.45rem;
  font-weight: 600;
  line-height: 1.3;
  margin: 0 0 4px;
  letter-spacing: -0.005em;
}}
.siamang-header__institution {{
  color: var(--siamang-muted);
  font-size: 0.92rem;
  margin: 0;
}}
.siamang-header__subtitle {{
  color: var(--siamang-muted);
  font-size: 0.95rem;
  margin: 4px 0 0;
  font-style: italic;
}}

/* ── progress strip ────────────────────────────────────────────────── */

.siamang-progress {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--siamang-section-gap);
  font-size: 0.85rem;
  color: var(--siamang-muted);
  font-variant-numeric: tabular-nums;
}}
.siamang-progress__bar {{
  flex: 1;
  height: 3px;
  background: var(--siamang-border);
  border-radius: 999px;
  overflow: hidden;
}}
.siamang-progress__fill {{
  display: block;
  height: 100%;
  background: var(--siamang-accent);
  width: 0;
  transition: width 200ms ease-out;
}}

/* ── SurveyJS overrides (defaultV2) ────────────────────────────────── */

.sd-root-modern,
.sv-root-modern {{
  --primary: var(--siamang-accent) !important;
  --primary-light: color-mix(in srgb, var(--siamang-accent) 12%, var(--siamang-surface)) !important;
  --background: var(--siamang-bg) !important;
  --background-dim: var(--siamang-bg) !important;
  --foreground: var(--siamang-text) !important;
  --base-unit: 8px !important;
  background: var(--siamang-bg) !important;
  font-family: var(--siamang-font) !important;
}}

.sd-page,
.sv_page_root {{
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: var(--siamang-section-gap);
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.02);
}}

.sd-page__title,
.sv_p_title {{
  font-family: var(--siamang-heading-font);
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0 0 var(--siamang-item-gap);
  color: var(--siamang-text);
  letter-spacing: -0.005em;
}}

.sd-question,
.sv_q {{
  margin-bottom: var(--siamang-section-gap);
}}

.sd-question__title,
.sv_q_title {{
  font-family: var(--siamang-heading-font);
  font-size: 1.02rem;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--siamang-text);
}}

.sd-question__num {{
  color: var(--siamang-muted);
  font-weight: 500;
  margin-right: 8px;
}}

.sd-question__description {{
  color: var(--siamang-muted);
  font-size: 0.92rem;
  margin: 0 0 12px;
  font-style: italic;
}}

.sd-question__required-text {{
  color: var(--siamang-accent);
  margin-left: 4px;
}}

/* inputs */

.sd-input,
.sv_q_text_root input,
.sv_q_text_root textarea {{
  width: 100%;
  padding: var(--siamang-control-pad) 12px;
  font: inherit;
  color: var(--siamang-text);
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  transition: border-color 120ms ease, box-shadow 120ms ease;
}}
.sd-input:focus,
.sv_q_text_root input:focus,
.sv_q_text_root textarea:focus {{
  outline: none;
  border-color: var(--siamang-accent);
  box-shadow: var(--siamang-focus-ring);
}}

/* radios / checkboxes */

.sd-radio,
.sd-checkbox,
.sv_q_radiogroup .sv_q_radiogroup_label,
.sv_q_checkbox .sv_q_checkbox_label {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: var(--siamang-control-pad) 8px;
  border-radius: var(--siamang-radius);
  cursor: pointer;
  transition: background-color 120ms ease;
}}
.sd-radio:hover,
.sd-checkbox:hover {{
  background: color-mix(in srgb, var(--siamang-accent) 6%, transparent);
}}
.sd-radio__decorator,
.sd-checkbox__decorator {{
  border-color: var(--siamang-muted) !important;
}}
.sd-item--checked .sd-radio__decorator,
.sd-item--checked .sd-checkbox__decorator {{
  background: var(--siamang-accent) !important;
  border-color: var(--siamang-accent) !important;
}}

/* Likert / rating */

.sd-rating,
.sv_q_rating {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
}}
.sd-rating__item,
.sv_q_rating_item {{
  min-width: 44px;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  background: var(--siamang-surface);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition: background-color 120ms ease, border-color 120ms ease;
}}
.sd-rating__item:hover,
.sv_q_rating_item:hover {{
  border-color: var(--siamang-accent);
}}
.sd-rating__item--selected,
.sv_q_rating_item.checked {{
  background: var(--siamang-accent);
  border-color: var(--siamang-accent);
  color: #fff;
}}

/* matrix */

.sd-matrix table,
.sv_q_matrix table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 0.95rem;
}}
.sd-matrix th,
.sd-matrix td,
.sv_q_matrix th,
.sv_q_matrix td {{
  border-bottom: 1px solid var(--siamang-border);
  padding: 12px 8px;
  text-align: center;
  vertical-align: middle;
}}
.sd-matrix th:first-child,
.sd-matrix td:first-child {{
  text-align: left;
  color: var(--siamang-text);
  font-weight: 500;
}}

/* buttons */

.sd-navigation__complete-btn,
.sd-navigation__next-btn,
.sd-navigation__prev-btn,
.sv_complete_btn,
.sv_next_btn,
.sv_prev_btn,
button[type="submit"] {{
  font: inherit;
  font-weight: 600;
  padding: 12px 22px;
  border-radius: var(--siamang-radius);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background-color 120ms ease, border-color 120ms ease;
}}

.sd-navigation__complete-btn,
.sd-navigation__next-btn,
.sv_complete_btn,
.sv_next_btn,
button[type="submit"] {{
  background: var(--siamang-accent);
  color: #fff;
}}
.sd-navigation__complete-btn:hover,
.sd-navigation__next-btn:hover,
.sv_complete_btn:hover,
.sv_next_btn:hover,
button[type="submit"]:hover {{
  background: color-mix(in srgb, var(--siamang-accent) 88%, black);
}}

.sd-navigation__prev-btn,
.sv_prev_btn {{
  background: transparent;
  color: var(--siamang-text);
  border-color: var(--siamang-border);
}}
.sd-navigation__prev-btn:hover,
.sv_prev_btn:hover {{
  background: color-mix(in srgb, var(--siamang-accent) 6%, transparent);
  border-color: var(--siamang-accent);
}}

button:focus-visible {{
  outline: none;
  box-shadow: var(--siamang-focus-ring);
}}

/* completed page */

.sd-completedpage,
.sv_completed_page {{
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: var(--siamang-section-gap);
  text-align: center;
  font-size: 1.1rem;
}}

/* ── footer ───────────────────────────────────────────────────────── */

.siamang-footer {{
  margin-top: 48px;
  padding-top: 20px;
  border-top: 1px solid var(--siamang-border);
  font-size: 0.85rem;
  color: var(--siamang-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  align-items: baseline;
}}
.siamang-footer__ethics {{
  flex-basis: 100%;
  font-style: italic;
  margin: 0 0 8px;
}}

/* ── closed / quota-full page ────────────────────────────────────── */

.siamang-closed {{
  max-width: var(--siamang-width);
  margin: 80px auto;
  padding: 0 20px;
  text-align: center;
}}
.siamang-closed h2 {{
  font-family: var(--siamang-heading-font);
  font-weight: 600;
  font-size: 1.7rem;
  margin: 0 0 16px;
}}
.siamang-closed p {{
  font-size: 1.05rem;
  color: var(--siamang-muted);
  margin: 0;
}}

/* ── responsive ───────────────────────────────────────────────────── */

@media (max-width: 540px) {{
  #survey {{ padding: 24px 16px 56px; }}
  .siamang-header__title    {{ font-size: 1.25rem; }}
  .sd-rating__item          {{ min-width: 40px; min-height: 40px; }}
}}

@media print {{
  body {{ background: #fff; color: #000; }}
  .siamang-header, .siamang-footer, .siamang-progress {{ border-color: #000; }}
  .sd-navigation, .siamang-skip-link {{ display: none !important; }}
}}
"""


def compile_css(ui: UIConfig) -> str:
    """Return a CSS string for ``ui``. ``custom_css`` is appended last."""

    density = _density_vars(ui.density)
    base = _CSS_TEMPLATE.format(
        primary=ui.primary_color,
        accent=ui.effective_accent,
        background=ui.background_color,
        surface=ui.surface_color,
        text=ui.text_color,
        muted=ui.muted_text_color,
        border=ui.border_color,
        font=ui.font_family,
        heading_font=ui.effective_heading_font,
        mono=ui.mono_font_family,
        font_size=ui.font_size,
        line_height=ui.line_height,
        width=ui.width,
        radius=ui.radius,
        gap_section=density["section"],
        gap_item=density["gap"],
        gap_control=density["control"],
        gap_page=density["page"],
    )
    if ui.custom_css:
        return base + "\n/* user overrides */\n" + ui.custom_css
    return base
