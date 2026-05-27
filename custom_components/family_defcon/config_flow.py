"Config flow and options flow for Family DEFCON."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


def _int_range(default: int, minimum: int = 0, maximum: int = 9999):
    return vol.All(vol.Coerce(int), vol.Range(min=minimum, max=maximum))


DEFAULT_PEOPLE_YAML = """- Mom
- Dad
- Henry
- Marc
- Maggie
"""

DEFAULT_AUTH_USERS_YAML = """Mom:
  role: parent
  pin: "1111"
Dad:
  role: parent
  pin: "2222"
Henry:
  role: child
  pin: "3333"
Marc:
  role: child
  pin: "4444"
Maggie:
  role: child
  pin: "5555"
"""

DEFAULT_STATIONS_YAML = """dashboard:
  name: Home Assistant Dashboard
  enabled: true
  key_entity: ""
"""

DEFAULT_ADGUARD_CLIENTS_YAML = """Mom:
  client_name: Mom
  enabled: true
Dad:
  client_name: Dad
  enabled: true
Henry:
  client_name: Henry
  enabled: true
Marc:
  client_name: Marc
  enabled: true
Maggie:
  client_name: Maggie
  enabled: true
"""

DEFAULT_PENALTIES_YAML = """first_strike_target_minutes: 30
retaliator_extra_minutes: 15
retaliation_target_minutes: 30
reattacker_extra_minutes: 15
reattack_target_minutes: 45
"""


class FamilyDefconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Family DEFCON."""

    VERSION = 3

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return FamilyDefconOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", "Family DEFCON"),
                data={
                    "name": user_input.get("name", "Family DEFCON"),
                    "config_file": user_input.get("config_file", "family_defcon.yaml"),
                },
                options={
                    "use_ui_config": bool(user_input.get("use_ui_config", True)),
                    "cooldown_seconds": int(user_input.get("cooldown_seconds", 30)),
                    "adguard_base_url": str(user_input.get("adguard_base_url", "")).rstrip("/"),
                    "dns_enabled": bool(user_input.get("dns_enabled", True)),
                    "enforcement_mode": str(user_input.get("enforcement_mode", "active")),
                    "mutual_destruction_scope": str(user_input.get("mutual_destruction_scope", "default_targets")),
                    "people_yaml": DEFAULT_PEOPLE_YAML,
                    "default_targets_yaml": "- Henry\n- Marc\n- Maggie\n",
                    "parent_targets_yaml": "- Mom\n- Dad\n",
                    "auth_users_yaml": DEFAULT_AUTH_USERS_YAML,
                    "stations_yaml": DEFAULT_STATIONS_YAML,
                    "adguard_clients_yaml": DEFAULT_ADGUARD_CLIENTS_YAML,
                    "dashboard_targets_yaml": "- Henry\n- Marc\n- Maggie\n- Mom\n- Dad\n",
                    "dashboard_station_id": "dashboard",
                    "dashboard_default_target": "Henry",
                    "penalties_yaml": DEFAULT_PENALTIES_YAML,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional("name", default="Family DEFCON"): str,
                vol.Optional("config_file", default="family_defcon.yaml"): str,
                vol.Optional("use_ui_config", default=True): bool,
                vol.Optional("cooldown_seconds", default=30): _int_range(30, 0, 3600),
                vol.Optional("adguard_base_url", default=""): str,
                vol.Optional("dns_enabled", default=True): bool,
                vol.Optional("enforcement_mode", default="active"): vol.In(["active", "disabled"]),
                vol.Optional("mutual_destruction_scope", default="default_targets"): vol.In(["default_targets", "all"]),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors={},
        )


class FamilyDefconOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Family DEFCON options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._pending: dict[str, Any] = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Start options flow with a menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "system",
                "people_targets",
                "auth_pins",
                "stations_dashboard",
                "adguard",
                "penalties",
            ],
        )

    async def async_step_system(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("use_ui_config", default=opts.get("use_ui_config", True)): bool,
                vol.Optional("cooldown_seconds", default=opts.get("cooldown_seconds", 30)): _int_range(30, 0, 3600),
                vol.Optional(
                    "launches_before_mutual_destruction",
                    default=opts.get("launches_before_mutual_destruction", 5),
                ): _int_range(5, 2, 99),
                vol.Optional(
                    "chain_before_mutual_destruction",
                    default=opts.get("chain_before_mutual_destruction", 4),
                ): _int_range(4, 2, 99),
                vol.Optional("daily_reset_time", default=opts.get("daily_reset_time", "05:00:00")): str,
                vol.Optional("max_event_log", default=opts.get("max_event_log", 25)): _int_range(25, 5, 200),
                vol.Optional(
                    "allow_parent_targets_default",
                    default=opts.get("allow_parent_targets_default", False),
                ): bool,
                vol.Optional("require_station_match", default=opts.get("require_station_match", False)): bool,
                vol.Optional("require_key_for_launch", default=opts.get("require_key_for_launch", False)): bool,
            }
        )
        return self.async_show_form(step_id="system", data_schema=schema)

    async def async_step_people_targets(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("people_yaml", default=opts.get("people_yaml", DEFAULT_PEOPLE_YAML)): str,
                vol.Optional("default_targets_yaml", default=opts.get("default_targets_yaml", "- Henry\n- Marc\n- Maggie\n")): str,
                vol.Optional("parent_targets_yaml", default=opts.get("parent_targets_yaml", "- Mom\n- Dad\n")): str,
            }
        )
        return self.async_show_form(
            step_id="people_targets",
            data_schema=schema,
            description_placeholders={
                "hint": "Enter YAML lists. Example: - Henry",
            },
        )

    async def async_step_auth_pins(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("auth_users_yaml", default=opts.get("auth_users_yaml", DEFAULT_AUTH_USERS_YAML)): str,
                vol.Optional("pin_timeout_seconds", default=opts.get("pin_timeout_seconds", 60)): _int_range(60, 1, 3600),
                vol.Optional("max_bad_pin_attempts", default=opts.get("max_bad_pin_attempts", 3)): _int_range(3, 1, 20),
                vol.Optional(
                    "lockout_seconds_after_bad_pins",
                    default=opts.get("lockout_seconds_after_bad_pins", 120),
                ): _int_range(120, 1, 3600),
            }
        )
        return self.async_show_form(
            step_id="auth_pins",
            data_schema=schema,
            description_placeholders={
                "hint": "Use pin_hash where possible. Generate with family_defcon.hash_pin.",
            },
        )

    async def async_step_stations_dashboard(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("stations_yaml", default=opts.get("stations_yaml", DEFAULT_STATIONS_YAML)): str,
                vol.Optional("dashboard_station_id", default=opts.get("dashboard_station_id", "dashboard")): str,
                vol.Optional("dashboard_default_target", default=opts.get("dashboard_default_target", "Henry")): str,
                vol.Optional("dashboard_targets_yaml", default=opts.get("dashboard_targets_yaml", "- Henry\n- Marc\n- Maggie\n- Mom\n- Dad\n")): str,
            }
        )
        return self.async_show_form(step_id="stations_dashboard", data_schema=schema)

    async def async_step_adguard(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("dns_enabled", default=opts.get("dns_enabled", True)): bool,
                vol.Optional("adguard_base_url", default=opts.get("adguard_base_url", "")): str,
                vol.Optional("enforcement_mode", default=opts.get("enforcement_mode", "active")): vol.In(["active", "disabled"]),
                vol.Optional(
                    "mutual_destruction_scope",
                    default=opts.get("mutual_destruction_scope", "default_targets"),
                ): vol.In(["default_targets", "all"]),
                vol.Optional("adguard_username_secret", default=opts.get("adguard_username_secret", "adguard_username")): str,
                vol.Optional("adguard_password_secret", default=opts.get("adguard_password_secret", "adguard_password")): str,
                vol.Optional("adguard_rule_prefix", default=opts.get("adguard_rule_prefix", "Family DEFCON Block")): str,
                vol.Optional("adguard_clients_yaml", default=opts.get("adguard_clients_yaml", DEFAULT_ADGUARD_CLIENTS_YAML)): str,
            }
        )
        return self.async_show_form(step_id="adguard", data_schema=schema)

    async def async_step_penalties(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional("penalties_yaml", default=opts.get("penalties_yaml", DEFAULT_PENALTIES_YAML)): str,
            }
        )
        return self.async_show_form(step_id="penalties", data_schema=schema)
