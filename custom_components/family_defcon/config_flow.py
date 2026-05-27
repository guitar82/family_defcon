"""Config flow for Family DEFCON."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class FamilyDefconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Family DEFCON."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", "Family DEFCON"),
                data={
                    "name": user_input.get("name", "Family DEFCON"),
                    "config_file": user_input.get("config_file", "family_defcon.yaml"),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional("name", default="Family DEFCON"): str,
                vol.Optional("config_file", default="family_defcon.yaml"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
