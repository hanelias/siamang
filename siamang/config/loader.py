"""Load and write ``~/.siamang.toml`` and switch between profiles."""

from __future__ import annotations

import contextlib
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.config.secrets import check_permissions


class ConfigError(RuntimeError):
    """Raised on invalid config payloads or missing required fields."""


DEFAULT_PATH = "~/.siamang.toml"


@dataclass(frozen=True, slots=True)
class Config:
    """In-memory representation of ``~/.siamang.toml``."""

    defaults: dict[str, Any] = field(default_factory=dict)
    backends: dict[str, dict[str, Any]] = field(default_factory=dict)
    frontends: dict[str, dict[str, Any]] = field(default_factory=dict)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    path: Path | None = None

    def backend(self, name: str) -> dict[str, Any]:
        if name not in self.backends:
            raise ConfigError(f"Backend '{name}' is not configured. Run `siamang init`.")
        return dict(self.backends[name])

    def frontend(self, name: str) -> dict[str, Any]:
        if name not in self.frontends:
            raise ConfigError(f"Frontend '{name}' is not configured. Run `siamang init`.")
        return dict(self.frontends[name])

    def default_backend(self) -> str:
        return self.defaults.get("backend", "local")

    def default_frontend(self) -> str:
        return self.defaults.get("frontend", "local")

    def with_profile(self, name: str) -> Config:
        if name not in self.profiles:
            raise ConfigError(f"Profile '{name}' is not defined.")
        profile = self.profiles[name]
        return Config(
            defaults={**self.defaults, **profile},
            backends=self.backends,
            frontends=self.frontends,
            profiles=self.profiles,
            path=self.path,
        )

    def to_toml(self) -> str:
        return _to_toml(self)


_CURRENT: Config | None = None


def current() -> Config:
    """Return the currently loaded config, or an empty one."""

    return _CURRENT or Config()


def load(path: str | Path = DEFAULT_PATH) -> Config:
    """Load ``path`` and make it the active config."""

    global _CURRENT
    resolved = Path(os.path.expanduser(str(path)))
    if not resolved.is_file():
        cfg = Config(path=resolved)
        _CURRENT = cfg
        return cfg

    check_permissions(resolved)
    with resolved.open("rb") as fp:
        data = tomllib.load(fp)

    cfg = _config_from_dict(data, path=resolved)
    cfg = _apply_env_overrides(cfg)
    _CURRENT = cfg
    return cfg


def use_profile(name: str) -> Config:
    """Switch the global current config to a named profile."""

    global _CURRENT
    cfg = current().with_profile(name)
    _CURRENT = cfg
    return cfg


def save(config: Config, path: str | Path | None = None) -> Path:
    """Write ``config`` to disk as TOML. Creates parents and sets 600."""

    destination = Path(os.path.expanduser(str(path or config.path or DEFAULT_PATH)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(config.to_toml(), encoding="utf-8")
    with contextlib.suppress(PermissionError, OSError):  # pragma: no cover
        destination.chmod(0o600)
    return destination


def _config_from_dict(data: dict[str, Any], path: Path | None) -> Config:
    return Config(
        defaults=dict(data.get("defaults", {})),
        backends=_namespace(data.get("backends", {})),
        frontends=_namespace(data.get("frontends", {})),
        profiles=_namespace(data.get("profiles", {})),
        path=path,
    )


def _namespace(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    return {name: dict(value) for name, value in payload.items() if isinstance(value, dict)}


# New canonical prefix + legacy fallback (SURVLIB_* still works)
_ENV_PREFIXES = {
    "SIAMANG_SUPABASE_": ("backends", "supabase"),
    "SIAMANG_GSHEETS_": ("backends", "gsheets"),
    "SIAMANG_VERCEL_": ("frontends", "vercel"),
    "SIAMANG_NETLIFY_": ("frontends", "netlify"),
    # Legacy (backward-compatible)
    "SURVLIB_SUPABASE_": ("backends", "supabase"),
    "SURVLIB_GSHEETS_": ("backends", "gsheets"),
    "SURVLIB_VERCEL_": ("frontends", "vercel"),
    "SURVLIB_NETLIFY_": ("frontends", "netlify"),
}


def _apply_env_overrides(cfg: Config) -> Config:
    backends = {k: dict(v) for k, v in cfg.backends.items()}
    frontends = {k: dict(v) for k, v in cfg.frontends.items()}

    for env_name, value in os.environ.items():
        for prefix, (kind, adapter) in _ENV_PREFIXES.items():
            if not env_name.startswith(prefix):
                continue
            key = env_name[len(prefix) :].lower()
            target = backends if kind == "backends" else frontends
            target.setdefault(adapter, {})[key] = value

    return Config(
        defaults=cfg.defaults,
        backends=backends,
        frontends=frontends,
        profiles=cfg.profiles,
        path=cfg.path,
    )


def _to_toml(cfg: Config) -> str:
    lines: list[str] = []
    if cfg.defaults:
        lines.append("[defaults]")
        for key, value in cfg.defaults.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    for kind, adapters in (("backends", cfg.backends), ("frontends", cfg.frontends)):
        for adapter_name, settings in adapters.items():
            lines.append(f"[{kind}.{adapter_name}]")
            for key, value in settings.items():
                lines.append(f"{key} = {_toml_value(value)}")
            lines.append("")
    for profile_name, settings in cfg.profiles.items():
        lines.append(f"[profiles.{profile_name}]")
        for key, value in settings.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return '""'
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
