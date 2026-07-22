"""Diagnostics support for Family DEFCON."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "adguard_password_secret",
    "adguard_username_secret",
    "dashboard_pin",
    "parent_admin_pin",
    "password",
    "people_pin_hashes",
    "people_pins",
    "pin",
    "pin_hash",
    "username",
}


def _serialize(value: Any) -> Any:
    """Convert runtime-only values into diagnostics-safe primitives."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for a Family DEFCON config entry."""
    domain_data = hass.data.get(DOMAIN, {})
    diagnostics = {
        "config_entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "active_config": domain_data.get("config", {}),
        "runtime_state": domain_data.get("state", {}),
        "registered_services": sorted(domain_data.get("registered_services", set())),
    }
    return async_redact_data(_serialize(diagnostics), TO_REDACT)
