"""Config flow and guided options flow for Family DEFCON."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN
from .config_helpers import (
    CONFIG_ENTRY_VERSION,
    PEOPLE_SLOTS,
    STATION_SLOTS,
    build_people_options,
    build_station_options,
    default_options,
    normalize_adguard_url,
    normalize_daily_reset_time,
    validate_people_input,
    validate_station_input,
)


PIN_PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

TEXT_SELECTOR = selector.TextSelector(selector.TextSelectorConfig())
URL_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
)
MULTILINE_TEXT_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(multiline=True)
)
ROLE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=["parent", "child"],
        mode=selector.SelectSelectorMode.DROPDOWN,
        translation_key="person_role",
    )
)
ENFORCEMENT_MODE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=["active", "disabled"],
        mode=selector.SelectSelectorMode.DROPDOWN,
        translation_key="enforcement_mode",
    )
)
MUTUAL_SCOPE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=["default_targets", "all"],
        mode=selector.SelectSelectorMode.DROPDOWN,
        translation_key="mutual_destruction_scope",
    )
)


def _number_box(minimum: int = 0, maximum: int = 9999):
    """Return a number input box selector instead of a slider."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _person_defaults(options: dict[str, Any]) -> list[dict[str, Any]]:
    people = options.get("people_list")
    roles = options.get("people_roles", {})
    clients = options.get("people_adguard_clients", {})
    default_targets = set(options.get("default_targets_list", []))
    parent_targets = set(options.get("parent_targets_list", []))
    saved_dashboard_targets = options.get("dashboard_targets_list", [])
    has_saved_dashboard_targets = isinstance(saved_dashboard_targets, list)
    dashboard_targets = set(
        saved_dashboard_targets if has_saved_dashboard_targets else []
    )

    if not isinstance(people, list) or not people:
        people = ["Parent 1", "Parent 2", "Child 1", "Child 2", "Child 3"]
        has_saved_dashboard_targets = False

    out = []
    for name in people[:PEOPLE_SLOTS]:
        if isinstance(roles, dict) and name in roles:
            role = roles.get(name, "child")
        else:
            lowered = str(name).lower()
            role = (
                "parent"
                if lowered.startswith(("parent", "adult", "guardian"))
                else "child"
            )

        is_parent = role == "parent"
        out.append(
            {
                "name": name,
                "role": role,
                "pin": "",
                "clear_pin": False,
                "adguard_client": clients.get(name, name)
                if isinstance(clients, dict)
                else name,
                "default_target": name in default_targets or not is_parent,
                "parent_target": name in parent_targets or is_parent,
                "dashboard_target": (name in dashboard_targets)
                if has_saved_dashboard_targets
                else True,
            }
        )
    while len(out) < PEOPLE_SLOTS:
        out.append(
            {
                "name": "",
                "role": "child",
                "pin": "",
                "clear_pin": False,
                "adguard_client": "",
                "default_target": False,
                "parent_target": False,
                "dashboard_target": False,
            }
        )
    return out


def _station_defaults(options: dict[str, Any]) -> list[dict[str, Any]]:
    stations = options.get("stations_list")
    if not isinstance(stations, list) or not stations:
        stations = [
            {
                "id": "dashboard",
                "name": "Home Assistant Dashboard",
                "enabled": True,
                "key_entity": "",
            }
        ]
    out = []
    for st in stations[:STATION_SLOTS]:
        if isinstance(st, dict):
            out.append(
                {
                    "id": str(st.get("id", "")),
                    "name": str(st.get("name", "")),
                    "enabled": bool(st.get("enabled", True)),
                    "key_entity": str(st.get("key_entity", "")),
                }
            )
    while len(out) < STATION_SLOTS:
        out.append({"id": "", "name": "", "enabled": True, "key_entity": ""})
    return out


def _validate_advanced_yaml(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate opt-in YAML overrides before they are persisted."""
    if not bool(user_input.get("use_advanced_yaml_overrides", False)):
        return {}

    expected_types = {
        "people_yaml": list,
        "auth_users_yaml": dict,
        "stations_yaml": dict,
        "adguard_clients_yaml": dict,
        "penalties_yaml": dict,
    }
    errors: dict[str, str] = {}
    for field, expected_type in expected_types.items():
        value = str(user_input.get(field, "") or "").strip()
        if not value:
            continue
        try:
            parsed = yaml.safe_load(value)
        except yaml.YAMLError:
            errors[field] = "invalid_yaml"
            continue
        if parsed is not None and not isinstance(parsed, expected_type):
            errors[field] = "invalid_yaml_type"
            continue
        if field == "auth_users_yaml" and isinstance(parsed, dict):
            if any(
                isinstance(user, dict) and str(user.get("pin", "") or "")
                for user in parsed.values()
            ):
                errors[field] = "plaintext_pin_not_allowed"
        if field == "penalties_yaml" and isinstance(parsed, dict):
            for value_to_check in parsed.values():
                try:
                    parsed_value = int(float(value_to_check))
                except (TypeError, ValueError):
                    errors[field] = "invalid_yaml_value"
                    break
                if not 1 <= parsed_value <= 999:
                    errors[field] = "invalid_yaml_value"
                    break
    return errors


class FamilyDefconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Family DEFCON."""

    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = 0

    @staticmethod
    def async_get_options_flow(config_entry):
        return FamilyDefconOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Initial setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                adguard_base_url = normalize_adguard_url(
                    user_input.get("adguard_base_url", "")
                )
            except ValueError:
                errors["adguard_base_url"] = "invalid_url"

        if user_input is not None and not errors:
            name = str(user_input.get("name", "Family DEFCON") or "").strip()
            return self.async_create_entry(
                title=name or "Family DEFCON",
                data={
                    "name": name or "Family DEFCON",
                    "config_file": "family_defcon.yaml",
                },
                options=default_options(
                    cooldown_seconds=int(float(user_input.get("cooldown_seconds", 30))),
                    dns_enabled=bool(user_input.get("dns_enabled", True)),
                    adguard_base_url=adguard_base_url,
                ),
            )

        values = user_input or {}
        schema = vol.Schema(
            {
                vol.Optional(
                    "name", default=values.get("name", "Family DEFCON")
                ): TEXT_SELECTOR,
                vol.Optional(
                    "cooldown_seconds",
                    default=values.get("cooldown_seconds", 30),
                ): _number_box(0, 3600),
                vol.Optional(
                    "dns_enabled", default=values.get("dns_enabled", True)
                ): bool,
                vol.Optional(
                    "adguard_base_url",
                    default=values.get("adguard_base_url", ""),
                ): URL_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


class FamilyDefconOptionsFlowHandler(config_entries.OptionsFlow):
    """Guided options flow."""

    def __init__(self) -> None:
        """Initialize a current-style options flow."""
        self._pending: dict[str, Any] | None = None

    @property
    def pending(self) -> dict[str, Any]:
        """Return a mutable copy of the saved options for this flow."""
        if self._pending is None:
            self._pending = dict(self.config_entry.options)
        return self._pending

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "people",
                "system",
                "stations",
                "adguard",
                "penalties",
                "advanced",
            ],
        )

    async def async_step_people(self, user_input: dict[str, Any] | None = None):
        opts = self.pending
        if user_input is not None:
            errors = validate_people_input(user_input)
            if errors:
                return self.async_show_form(
                    step_id="people",
                    data_schema=self._people_schema(opts, user_input),
                    errors=errors,
                )
            opts = build_people_options(user_input, opts)
            return self.async_create_entry(title="", data=opts)

        return self.async_show_form(
            step_id="people", data_schema=self._people_schema(opts)
        )

    def _people_schema(
        self,
        opts: dict[str, Any],
        suggested: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return guided people schema."""
        defaults = _person_defaults(opts)
        suggested = suggested or {}
        fields = {}
        for idx, person in enumerate(defaults, start=1):
            prefix = f"person_{idx}"
            fields[
                vol.Optional(
                    f"{prefix}_name",
                    default=suggested.get(f"{prefix}_name", person["name"]),
                )
            ] = TEXT_SELECTOR
            fields[
                vol.Optional(
                    f"{prefix}_role",
                    default=suggested.get(f"{prefix}_role", person["role"]),
                )
            ] = ROLE_SELECTOR
            fields[vol.Optional(f"{prefix}_pin", default="")] = PIN_PASSWORD_SELECTOR
            fields[
                vol.Optional(
                    f"{prefix}_clear_pin",
                    default=suggested.get(f"{prefix}_clear_pin", False),
                )
            ] = bool
            fields[
                vol.Optional(
                    f"{prefix}_adguard_client",
                    default=suggested.get(
                        f"{prefix}_adguard_client", person["adguard_client"]
                    ),
                )
            ] = TEXT_SELECTOR
            fields[
                vol.Optional(
                    f"{prefix}_default_target",
                    default=suggested.get(
                        f"{prefix}_default_target", person["default_target"]
                    ),
                )
            ] = bool
            fields[
                vol.Optional(
                    f"{prefix}_parent_target",
                    default=suggested.get(
                        f"{prefix}_parent_target", person["parent_target"]
                    ),
                )
            ] = bool
            fields[
                vol.Optional(
                    f"{prefix}_dashboard_target",
                    default=suggested.get(
                        f"{prefix}_dashboard_target", person["dashboard_target"]
                    ),
                )
            ] = bool
        return vol.Schema(fields)

    async def async_step_system(self, user_input: dict[str, Any] | None = None):
        opts = self.pending
        if user_input is not None:
            try:
                user_input["daily_reset_time"] = normalize_daily_reset_time(
                    user_input.get("daily_reset_time", "05:00:00")
                )
            except ValueError:
                return self.async_show_form(
                    step_id="system",
                    data_schema=self._system_schema(opts, user_input),
                    errors={"daily_reset_time": "invalid_time"},
                )

            opts.update(user_input)
            for key in (
                "cooldown_seconds",
                "launches_before_mutual_destruction",
                "chain_before_mutual_destruction",
                "max_event_log",
                "pin_timeout_seconds",
                "max_bad_pin_attempts",
                "lockout_seconds_after_bad_pins",
            ):
                if key in opts and opts[key] not in (None, ""):
                    opts[key] = int(float(opts[key]))
            return self.async_create_entry(title="", data=opts)

        return self.async_show_form(
            step_id="system",
            data_schema=self._system_schema(opts),
        )

    def _system_schema(
        self,
        opts: dict[str, Any],
        suggested: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return the system settings schema with native selectors."""
        values = {**opts, **(suggested or {})}
        schema = vol.Schema(
            {
                vol.Optional(
                    "use_ui_config", default=values.get("use_ui_config", True)
                ): bool,
                vol.Optional(
                    "cooldown_seconds", default=values.get("cooldown_seconds", 30)
                ): _number_box(0, 3600),
                vol.Optional(
                    "launches_before_mutual_destruction",
                    default=values.get("launches_before_mutual_destruction", 5),
                ): _number_box(2, 99),
                vol.Optional(
                    "chain_before_mutual_destruction",
                    default=values.get("chain_before_mutual_destruction", 4),
                ): _number_box(2, 99),
                vol.Optional(
                    "daily_reset_time",
                    default=values.get("daily_reset_time", "05:00:00"),
                ): selector.TimeSelector(),
                vol.Optional(
                    "max_event_log", default=values.get("max_event_log", 25)
                ): _number_box(5, 200),
                vol.Optional(
                    "allow_parent_targets_default",
                    default=values.get("allow_parent_targets_default", False),
                ): bool,
                vol.Optional(
                    "require_station_match",
                    default=values.get("require_station_match", False),
                ): bool,
                vol.Optional(
                    "require_key_for_launch",
                    default=values.get("require_key_for_launch", False),
                ): bool,
                vol.Optional(
                    "pin_timeout_seconds", default=values.get("pin_timeout_seconds", 60)
                ): _number_box(1, 3600),
                vol.Optional(
                    "max_bad_pin_attempts",
                    default=values.get("max_bad_pin_attempts", 3),
                ): _number_box(1, 20),
                vol.Optional(
                    "lockout_seconds_after_bad_pins",
                    default=values.get("lockout_seconds_after_bad_pins", 120),
                ): _number_box(1, 3600),
            }
        )
        return schema

    async def async_step_stations(self, user_input: dict[str, Any] | None = None):
        opts = self.pending
        if user_input is not None:
            errors = validate_station_input(user_input)
            if errors:
                return self.async_show_form(
                    step_id="stations",
                    data_schema=self._station_schema(opts, user_input),
                    errors=errors,
                )
            opts = build_station_options(user_input, opts)
            return self.async_create_entry(title="", data=opts)

        return self.async_show_form(
            step_id="stations",
            data_schema=self._station_schema(opts),
        )

    def _station_schema(
        self,
        opts: dict[str, Any],
        suggested: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return the station settings schema with entity selectors."""
        stations = _station_defaults(opts)
        suggested = suggested or {}
        dashboard_targets = opts.get("dashboard_targets_list", [])
        if not isinstance(dashboard_targets, list) or not dashboard_targets:
            dashboard_targets = [
                person["name"] for person in _person_defaults(opts) if person["name"]
            ]
        dashboard_default = suggested.get(
            "dashboard_default_target",
            opts.get(
                "dashboard_default_target",
                dashboard_targets[0] if dashboard_targets else "",
            ),
        )
        fields = {
            vol.Optional(
                "dashboard_station_id",
                default=suggested.get(
                    "dashboard_station_id",
                    opts.get("dashboard_station_id", "dashboard"),
                ),
            ): TEXT_SELECTOR,
            vol.Optional(
                "dashboard_default_target",
                default=dashboard_default,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[str(target) for target in dashboard_targets],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
        for idx, station in enumerate(stations, start=1):
            prefix = f"station_{idx}"
            fields[
                vol.Optional(
                    f"{prefix}_id",
                    default=suggested.get(f"{prefix}_id", station["id"]),
                )
            ] = TEXT_SELECTOR
            fields[
                vol.Optional(
                    f"{prefix}_name",
                    default=suggested.get(f"{prefix}_name", station["name"]),
                )
            ] = TEXT_SELECTOR
            fields[
                vol.Optional(
                    f"{prefix}_enabled",
                    default=suggested.get(f"{prefix}_enabled", station["enabled"]),
                )
            ] = bool
            key_entity_field = f"{prefix}_key_entity"
            key_entity = suggested.get(key_entity_field, station["key_entity"])
            key_entity_marker = (
                vol.Optional(
                    key_entity_field,
                    description={"suggested_value": key_entity},
                )
                if key_entity
                else vol.Optional(key_entity_field)
            )
            fields[key_entity_marker] = selector.EntitySelector(
                selector.EntitySelectorConfig()
            )

        return vol.Schema(fields)

    async def async_step_adguard(self, user_input: dict[str, Any] | None = None):
        opts = self.pending
        if user_input is not None:
            try:
                user_input["adguard_base_url"] = normalize_adguard_url(
                    user_input.get("adguard_base_url", "")
                )
            except ValueError:
                return self.async_show_form(
                    step_id="adguard",
                    data_schema=self._adguard_schema(opts, user_input),
                    errors={"adguard_base_url": "invalid_url"},
                )
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        return self.async_show_form(
            step_id="adguard",
            data_schema=self._adguard_schema(opts),
        )

    def _adguard_schema(
        self,
        opts: dict[str, Any],
        suggested: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return AdGuard settings using current selector controls."""
        values = {**opts, **(suggested or {})}
        schema = vol.Schema(
            {
                vol.Optional(
                    "dns_enabled", default=values.get("dns_enabled", True)
                ): bool,
                vol.Optional(
                    "adguard_use_ha_integration",
                    default=values.get("adguard_use_ha_integration", True),
                ): bool,
                vol.Optional(
                    "adguard_base_url", default=values.get("adguard_base_url", "")
                ): URL_SELECTOR,
                vol.Optional(
                    "enforcement_mode", default=values.get("enforcement_mode", "active")
                ): ENFORCEMENT_MODE_SELECTOR,
                vol.Optional(
                    "mutual_destruction_scope",
                    default=values.get("mutual_destruction_scope", "default_targets"),
                ): MUTUAL_SCOPE_SELECTOR,
                vol.Optional(
                    "adguard_username_secret",
                    default=values.get("adguard_username_secret", "adguard_username"),
                ): TEXT_SELECTOR,
                vol.Optional(
                    "adguard_password_secret",
                    default=values.get("adguard_password_secret", "adguard_password"),
                ): TEXT_SELECTOR,
                vol.Optional(
                    "adguard_rule_prefix",
                    default=values.get("adguard_rule_prefix", "Family DEFCON Block"),
                ): TEXT_SELECTOR,
            }
        )
        return schema

    async def async_step_penalties(self, user_input: dict[str, Any] | None = None):
        opts = self.pending
        if user_input is not None:
            for key, value in user_input.items():
                user_input[key] = int(float(value))
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema(
            {
                vol.Optional(
                    "first_strike_target_minutes",
                    default=opts.get("first_strike_target_minutes", 30),
                ): _number_box(1, 999),
                vol.Optional(
                    "retaliator_extra_minutes",
                    default=opts.get("retaliator_extra_minutes", 15),
                ): _number_box(1, 999),
                vol.Optional(
                    "retaliation_target_minutes",
                    default=opts.get("retaliation_target_minutes", 30),
                ): _number_box(1, 999),
                vol.Optional(
                    "reattacker_extra_minutes",
                    default=opts.get("reattacker_extra_minutes", 15),
                ): _number_box(1, 999),
                vol.Optional(
                    "reattack_target_minutes",
                    default=opts.get("reattack_target_minutes", 45),
                ): _number_box(1, 999),
            }
        )
        return self.async_show_form(step_id="penalties", data_schema=schema)

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None):
        """Advanced raw YAML import.

        This is intentionally opt-in. Empty fields stay empty and are not
        repopulated from older saved values unless advanced overrides are enabled.
        """
        opts = self.pending
        if user_input is not None:
            clear = bool(user_input.get("clear_advanced_yaml_overrides", False))
            enabled = bool(user_input.get("use_advanced_yaml_overrides", False))

            errors = _validate_advanced_yaml(user_input)
            if errors and not clear:
                return self.async_show_form(
                    step_id="advanced",
                    data_schema=self._advanced_schema(opts, user_input),
                    errors=errors,
                )

            if clear or not enabled:
                opts["use_advanced_yaml_overrides"] = False
                opts["people_yaml"] = ""
                opts["auth_users_yaml"] = ""
                opts["stations_yaml"] = ""
                opts["adguard_clients_yaml"] = ""
                opts["penalties_yaml"] = ""
            else:
                opts["use_advanced_yaml_overrides"] = True
                opts["people_yaml"] = str(user_input.get("people_yaml", "") or "")
                opts["auth_users_yaml"] = str(
                    user_input.get("auth_users_yaml", "") or ""
                )
                opts["stations_yaml"] = str(user_input.get("stations_yaml", "") or "")
                opts["adguard_clients_yaml"] = str(
                    user_input.get("adguard_clients_yaml", "") or ""
                )
                opts["penalties_yaml"] = str(user_input.get("penalties_yaml", "") or "")

            return self.async_create_entry(title="", data=opts)

        return self.async_show_form(
            step_id="advanced",
            data_schema=self._advanced_schema(opts),
        )

    def _advanced_schema(
        self,
        opts: dict[str, Any],
        suggested: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return the advanced YAML schema and preserve invalid input for repair."""
        values = {**opts, **(suggested or {})}
        enabled = bool(values.get("use_advanced_yaml_overrides", False))
        return vol.Schema(
            {
                vol.Optional("use_advanced_yaml_overrides", default=enabled): bool,
                vol.Optional("clear_advanced_yaml_overrides", default=False): bool,
                vol.Optional(
                    "people_yaml",
                    default=values.get("people_yaml", "") if enabled else "",
                ): MULTILINE_TEXT_SELECTOR,
                vol.Optional(
                    "auth_users_yaml",
                    default=values.get("auth_users_yaml", "") if enabled else "",
                ): MULTILINE_TEXT_SELECTOR,
                vol.Optional(
                    "stations_yaml",
                    default=values.get("stations_yaml", "") if enabled else "",
                ): MULTILINE_TEXT_SELECTOR,
                vol.Optional(
                    "adguard_clients_yaml",
                    default=values.get("adguard_clients_yaml", "") if enabled else "",
                ): MULTILINE_TEXT_SELECTOR,
                vol.Optional(
                    "penalties_yaml",
                    default=values.get("penalties_yaml", "") if enabled else "",
                ): MULTILINE_TEXT_SELECTOR,
            }
        )
