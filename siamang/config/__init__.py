"""Configuration: ~/.siamang.toml loader, profiles, secret hardening."""

from siamang.config.loader import Config, ConfigError, current, load, save, use_profile
from siamang.config.secrets import check_permissions

__all__ = [
    "Config",
    "ConfigError",
    "check_permissions",
    "current",
    "load",
    "save",
    "use_profile",
]
