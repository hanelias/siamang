"""Frontend-side backend client templates."""

from siamang.frontend.client.base import BackendClientTemplate, ClientEnv
from siamang.frontend.client.gsheets import GoogleSheetsClientTemplate
from siamang.frontend.client.local import LocalClientTemplate
from siamang.frontend.client.supabase import SupabaseClientTemplate

__all__ = [
    "BackendClientTemplate",
    "ClientEnv",
    "GoogleSheetsClientTemplate",
    "LocalClientTemplate",
    "SupabaseClientTemplate",
]
