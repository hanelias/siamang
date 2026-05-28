"""Secret-file hardening helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path

_logger = logging.getLogger("siamang.config")


def check_permissions(path: Path) -> bool:
    """Warn (and return False) if a config file is world/group readable on POSIX."""

    if os.name != "posix":  # pragma: no cover - Windows
        return True
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        return True
    if mode & 0o077:
        _logger.warning(
            "siamang config at %s has permissions %o; secrets may leak. Run `chmod 600 %s`.",
            path,
            mode & 0o777,
            path,
        )
        return False
    return True
