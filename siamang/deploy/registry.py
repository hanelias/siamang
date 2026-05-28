"""Adapter registry — resolves backend/frontend names to classes.

Adapters are discovered via ``importlib.metadata.entry_points`` under the
``siamang.backends`` / ``siamang.frontends`` groups, with built-in fallbacks
for all bundled adapters (backends: ``local``, ``supabase``, ``gsheets``;
frontends: ``local``, ``vercel``, ``netlify``).
"""

from __future__ import annotations

import contextlib
from importlib import metadata
from typing import Any

from siamang.deploy.base import BackendAdapter, FrontendAdapter

_BUILTIN_BACKENDS = {
    "local": "siamang.deploy.backends.local:LocalBackend",
    "supabase": "siamang.deploy.backends.supabase:SupabaseBackend",
    "gsheets": "siamang.deploy.backends.gsheets:GoogleSheetsBackend",
}

_BUILTIN_FRONTENDS = {
    "local": "siamang.deploy.frontends.local:LocalFrontend",
    "vercel": "siamang.deploy.frontends.vercel:VercelFrontend",
    "netlify": "siamang.deploy.frontends.netlify:NetlifyFrontend",
}


def _load_target(target: str) -> Any:
    module, _, attr = target.partition(":")
    obj = __import__(module, fromlist=[attr])
    return getattr(obj, attr)


def _resolve(group: str, name: str, builtin: dict[str, str]) -> Any:
    try:
        entries = metadata.entry_points(group=group)
        for entry in entries:
            if entry.name == name:
                return entry.load()
    except Exception:  # pragma: no cover - metadata can be flaky in some envs
        pass
    target = builtin.get(name)
    if target is None:
        raise KeyError(f"Unknown adapter '{name}' in group '{group}'.")
    return _load_target(target)


def backend_factory(name: str) -> type[BackendAdapter]:
    return _resolve("siamang.backends", name, _BUILTIN_BACKENDS)


def frontend_factory(name: str) -> type[FrontendAdapter]:
    return _resolve("siamang.frontends", name, _BUILTIN_FRONTENDS)


def list_backends() -> list[str]:
    names = set(_BUILTIN_BACKENDS)
    with contextlib.suppress(Exception):  # pragma: no cover
        names.update(ep.name for ep in metadata.entry_points(group="siamang.backends"))
    return sorted(names)


def list_frontends() -> list[str]:
    names = set(_BUILTIN_FRONTENDS)
    with contextlib.suppress(Exception):  # pragma: no cover
        names.update(ep.name for ep in metadata.entry_points(group="siamang.frontends"))
    return sorted(names)
