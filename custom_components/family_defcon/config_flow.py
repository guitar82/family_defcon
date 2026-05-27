"""Config flow for Family DEFCON."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class FamilyDefconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Family DEFCON."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", "Family DEFCON"),
                data={
                    "name": user_input.get("name", "Family DEFCON"),
                    "config_file": user_input.get("config_file", "family_defcon.yaml"),
                },
            )

        schema = vol.Schema(
            {
                vol.Optional("name", default="Family DEFCON"): str,
                vol.Optional("config_file", default="family_defcon.yaml"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "config_file": "family_defcon.yaml",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FamilyDefconOptionsFlow(config_entry)


class FamilyDefconOptionsFlow(config_entries.OptionsFlow):
    """Handle Family DEFCON options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config_file = self.config_entry.options.get(
            "config_file",
            self.config_entry.data.get("config_file", "family_defcon.yaml"),
        )

        schema = vol.Schema(
            {
                vol.Optional("config_file", default=current_config_file): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
