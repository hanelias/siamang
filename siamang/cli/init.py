"""`siamang init` — interactive wizard for ~/.siamang.toml."""

from __future__ import annotations

import getpass
from pathlib import Path

from siamang.config import Config, save


def _ask(prompt: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    text = f"{prompt}{suffix}: "
    value = getpass.getpass(text) if secret else input(text)
    return value or default or ""


def run(path: str | Path = "~/.siamang.toml", non_interactive: bool = False) -> int:
    target = Path(path).expanduser()
    if non_interactive:
        cfg = Config(
            defaults={"backend": "local", "frontend": "local"},
            backends={},
            frontends={},
        )
        destination = save(cfg, target)
        print(f"Wrote {destination} (defaults: local/local).")
        return 0

    print("siamang init — interactive setup")
    print(f"Target: {target}")
    backend = _ask("Default backend (local/supabase)", default="local")
    frontend = _ask("Default frontend (local/vercel)", default="local")

    cfg = Config(defaults={"backend": backend, "frontend": frontend})

    if backend == "supabase":
        url = _ask("Supabase URL")
        anon = _ask("Supabase anon_key", secret=True)
        service = _ask("Supabase service_key", secret=True)
        cfg = Config(
            defaults=cfg.defaults,
            backends={"supabase": {"url": url, "anon_key": anon, "service_key": service}},
            frontends=cfg.frontends,
            profiles=cfg.profiles,
        )

    if frontend == "vercel":
        token = _ask("Vercel token", secret=True)
        team_id = _ask("Vercel team_id (optional)") or ""
        vercel = {"token": token}
        if team_id:
            vercel["team_id"] = team_id
        cfg = Config(
            defaults=cfg.defaults,
            backends=cfg.backends,
            frontends={**cfg.frontends, "vercel": vercel},
            profiles=cfg.profiles,
        )

    destination = save(cfg, target)
    print(f"\nWrote {destination} (chmod 600 applied).")
    return 0
