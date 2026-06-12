# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **License**: switched from MIT to dual licensing. Noncommercial use is
  free under the **PolyForm Noncommercial License 1.0.0** (`LICENSE`);
  commercial use now requires a separate commercial license
  (`LICENSE-COMMERCIAL.md`). Versions up to and including 0.5.0 remain
  available under the MIT License.
- Build: `setuptools>=77` is now required (PEP 639 license metadata).

## [0.5.0] — 2026-05-28

### Added

- **Theming system**: `UIConfig` with `font_preset` (classic, modern, humanist),
  `accent_color`, and CSS custom properties for full visual customization.
- **"Other (specify)"** option for `SingleChoice` and `MultiChoice` questions
  via `other_specify=True`.
- **Answers store**: lightweight reactive store (`useSyncExternalStore`) replacing
  top-level `useState` — eliminates full-tree re-renders on every keystroke.
- **Compiled visibility**: `show_if`/`hide_if` conditions compiled to JS functions
  at load time (no more per-render AST interpretation).
- **Hooks decomposition**: `useSurveyNav`, `useSubmission`, `useAutosave`,
  `useLifecycleScripts`, `useKeyboardShortcuts`, `useTheme`.
- Supabase backend now uses a single shared `responses` table with `survey_id`
  column (consistent with local SQLite backend).
- Environment variable naming: `SIAMANG_SUPABASE_*` with backward-compatible
  fallback to legacy `SURVLIB_SUPABASE_*`.
- Script factory functions now use `json.dumps()` for parameter escaping
  (prevents injection from special characters in IDs/messages).

### Changed

- Development status set to **Beta** (honest reflection of current test coverage).
- Slider component: adaptive tick rendering (≤20 steps → labeled ticks,
  >20 steps → end-labels only). Fixes the "wall of numbers" bug.
- Frontend JS globals renamed: `window.SIAMANG_ENV` / `window.SIAMANG_TRANSPORTS`
  (runtime falls back to legacy `SURVLIB_*` names for backward compatibility).

### Fixed

- Supabase backend/frontend mismatch: frontend now POSTs `{survey_id, data}`
  matching the shared table schema (previously sent `{survey_id, payload}` to
  a per-survey table that didn't have a `survey_id` column).
- Slider rendering bug: no longer outputs 61 `<option>` elements for range 0–60.

### Removed

- Per-survey table creation (`responses_{survey_id}`) in Supabase backend —
  replaced by shared `responses` table.
- `BUILD.md` reference removed from MANIFEST.in (file never existed).

## [0.4.1] — 2026-04-15

### Added

- Initial public structure with core survey engine, React frontend, CLI,
  local SQLite backend, and Supabase/Vercel deployment support.
