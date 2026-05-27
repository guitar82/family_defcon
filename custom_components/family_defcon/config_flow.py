"Config flow and guided options flow for Family DEFCON."""
from __future__ import annotations

from typing import Any

import hashlib
import secrets

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN


PEOPLE_SLOTS = 8
STATION_SLOTS = 8


def hash_pin_for_options(pin: str, iterations: int = 200000) -> str:
    """Return a PBKDF2-SHA256 hash string for a PIN entered in the options UI."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", str(pin).encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


PIN_PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)



def _int_range(default: int, minimum: int = 0, maximum: int = 9999):
    return vol.All(vol.Coerce(int), vol.Range(min=minimum, max=maximum))



def _number_box(default: int, minimum: int = 0, maximum: int = 9999):
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
    pins = options.get("people_pins", {})
    pin_hashes = options.get("people_pin_hashes", {})
    clients = options.get("people_adguard_clients", {})
    default_targets = set(options.get("default_targets_list", []))
    parent_targets = set(options.get("parent_targets_list", []))
    dashboard_targets = set(options.get("dashboard_targets_list", []))

    if not isinstance(people, list) or not people:
        people = ["Mom", "Dad", "Henry", "Marc", "Maggie"]

    out = []
    for name in people[:PEOPLE_SLOTS]:
        role = roles.get(name, "parent" if name in ("Mom", "Dad") else "child") if isinstance(roles, dict) else "child"
        out.append({
            "name": name,
            "role": role,
            "pin": "",
            "pin_hash": pin_hashes.get(name, "") if isinstance(pin_hashes, dict) else "",
            "adguard_client": clients.get(name, name) if isinstance(clients, dict) else name,
            "default_target": name in default_targets or (role == "child" and name not in ("Mom", "Dad")),
            "parent_target": name in parent_targets or role == "parent",
            "dashboard_target": name in dashboard_targets or True,
        })
    while len(out) < PEOPLE_SLOTS:
        out.append({
            "name": "",
            "role": "child",
            "pin": "",
            "pin_hash": "",
            "adguard_client": "",
            "default_target": False,
            "parent_target": False,
            "dashboard_target": False,
        })
    return out


def _station_defaults(options: dict[str, Any]) -> list[dict[str, Any]]:
    stations = options.get("stations_list")
    if not isinstance(stations, list) or not stations:
        stations = [{"id": "dashboard", "name": "Home Assistant Dashboard", "enabled": True, "key_entity": ""}]
    out = []
    for st in stations[:STATION_SLOTS]:
        if isinstance(st, dict):
            out.append({
                "id": str(st.get("id", "")),
                "name": str(st.get("name", "")),
                "enabled": bool(st.get("enabled", True)),
                "key_entity": str(st.get("key_entity", "")),
            })
    while len(out) < STATION_SLOTS:
        out.append({"id": "", "name": "", "enabled": True, "key_entity": ""})
    return out


def _build_people_options(user_input: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    people = []
    roles = {}
    # Plain PINs are intentionally not persisted. They are write-only fields.
    pins = {}
    pin_hashes = {}
    clients = {}
    default_targets = []
    parent_targets = []
    dashboard_targets = []

    existing_pin_hashes = existing.get("people_pin_hashes", {}) if isinstance(existing.get("people_pin_hashes", {}), dict) else {}

    for i in range(1, PEOPLE_SLOTS + 1):
        name = str(user_input.get(f"person_{i}_name", "")).strip()
        if not name:
            continue
        people.append(name)
        role = str(user_input.get(f"person_{i}_role", "child"))
        roles[name] = role

        new_pin = str(user_input.get(f"person_{i}_pin", "")).strip()
        typed_hash = str(user_input.get(f"person_{i}_pin_hash", "")).strip()
        client = str(user_input.get(f"person_{i}_adguard_client", "")).strip() or name

        # New PIN is write-only. Hash immediately and never store the plain value.
        if new_pin:
            pin_hashes[name] = hash_pin_for_options(new_pin)
        elif typed_hash:
            pin_hashes[name] = typed_hash
        elif name in existing_pin_hashes:
            pin_hashes[name] = str(existing_pin_hashes[name])

        clients[name] = client

        if bool(user_input.get(f"person_{i}_default_target", False)):
            default_targets.append(name)
        if bool(user_input.get(f"person_{i}_parent_target", False)):
            parent_targets.append(name)
        if bool(user_input.get(f"person_{i}_dashboard_target", True)):
            dashboard_targets.append(name)

    existing.update({
        "people_list": people,
        "people_roles": roles,
        "people_pins": pins,
        "people_pin_hashes": pin_hashes,
        "people_adguard_clients": clients,
        "default_targets_list": default_targets,
        "parent_targets_list": parent_targets,
        "dashboard_targets_list": dashboard_targets,
    })
    if people and existing.get("dashboard_default_target", "") not in people:
        existing["dashboard_default_target"] = default_targets[0] if default_targets else people[0]
    return existing


def _build_station_options(user_input: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    stations = []
    for i in range(1, STATION_SLOTS + 1):
        sid = str(user_input.get(f"station_{i}_id", "")).strip()
        if not sid:
            continue
        stations.append({
            "id": sid,
            "name": str(user_input.get(f"station_{i}_name", sid)).strip() or sid,
            "enabled": bool(user_input.get(f"station_{i}_enabled", True)),
            "key_entity": str(user_input.get(f"station_{i}_key_entity", "")).strip(),
        })
    existing["stations_list"] = stations
    return existing


class FamilyDefconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Family DEFCON."""

    VERSION = 4

    @staticmethod
    def async_get_options_flow(config_entry):
        return FamilyDefconOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Initial setup."""
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
                    "use_ui_config": True,
                    "cooldown_seconds": int(user_input.get("cooldown_seconds", 30)),
                    "people_list": ["Mom", "Dad", "Henry", "Marc", "Maggie"],
                    "people_roles": {"Mom": "parent", "Dad": "parent", "Henry": "child", "Marc": "child", "Maggie": "child"},
                    "people_pins": {},
                    "people_pin_hashes": {
                        "Mom": hash_pin_for_options("1111"),
                        "Dad": hash_pin_for_options("2222"),
                        "Henry": hash_pin_for_options("3333"),
                        "Marc": hash_pin_for_options("4444"),
                        "Maggie": hash_pin_for_options("5555"),
                    },
                    "people_adguard_clients": {"Mom": "Mom", "Dad": "Dad", "Henry": "Henry", "Marc": "Marc", "Maggie": "Maggie"},
                    "default_targets_list": ["Henry", "Marc", "Maggie"],
                    "parent_targets_list": ["Mom", "Dad"],
                    "dashboard_targets_list": ["Henry", "Marc", "Maggie", "Mom", "Dad"],
                    "dashboard_station_id": "dashboard",
                    "dashboard_default_target": "Henry",
                    "stations_list": [{"id": "dashboard", "name": "Home Assistant Dashboard", "enabled": True, "key_entity": ""}],
                    "dns_enabled": bool(user_input.get("dns_enabled", True)),
                    "adguard_base_url": str(user_input.get("adguard_base_url", "")).rstrip("/"),
                    "enforcement_mode": "active",
                    "mutual_destruction_scope": "default_targets",
                    "adguard_username_secret": "adguard_username",
                    "adguard_password_secret": "adguard_password",
                    "adguard_rule_prefix": "Family DEFCON Block",
                    "use_advanced_yaml_overrides": False,
                    "people_yaml": "",
                    "auth_users_yaml": "",
                    "stations_yaml": "",
                    "adguard_clients_yaml": "",
                    "penalties_yaml": "",
                    "launches_before_mutual_destruction": 5,
                    "chain_before_mutual_destruction": 4,
                    "daily_reset_time": "05:00:00",
                    "max_event_log": 25,
                    "allow_parent_targets_default": False,
                    "require_station_match": False,
                    "require_key_for_launch": False,
                    "pin_timeout_seconds": 60,
                    "max_bad_pin_attempts": 3,
                    "lockout_seconds_after_bad_pins": 120,
                    "first_strike_target_minutes": 30,
                    "retaliator_extra_minutes": 15,
                    "retaliation_target_minutes": 30,
                    "reattacker_extra_minutes": 15,
                    "reattack_target_minutes": 45,
                },
            )

        schema = vol.Schema({
            vol.Optional("name", default="Family DEFCON"): str,
            vol.Optional("config_file", default="family_defcon.yaml"): str,
            vol.Optional("cooldown_seconds", default=30): _int_range(30, 0, 3600),
            vol.Optional("dns_enabled", default=True): bool,
            vol.Optional("adguard_base_url", default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema)


class FamilyDefconOptionsFlowHandler(config_entries.OptionsFlow):
    """Guided options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._pending: dict[str, Any] = dict(config_entry.options)

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
        opts = self._pending
        if user_input is not None:
            opts = _build_people_options(user_input, opts)
            return self.async_create_entry(title="", data=opts)

        defaults = _person_defaults(opts)
        fields = {}
        for idx, person in enumerate(defaults, start=1):
            prefix = f"person_{idx}"
            fields[vol.Optional(f"{prefix}_name", default=person["name"])] = str
            fields[vol.Optional(f"{prefix}_role", default=person["role"])] = vol.In(["parent", "child"])
            fields[vol.Optional(f"{prefix}_pin", default="")] = PIN_PASSWORD_SELECTOR
            fields[vol.Optional(f"{prefix}_pin_hash", default=person["pin_hash"])] = str
            fields[vol.Optional(f"{prefix}_adguard_client", default=person["adguard_client"])] = str
            fields[vol.Optional(f"{prefix}_default_target", default=person["default_target"])] = bool
            fields[vol.Optional(f"{prefix}_parent_target", default=person["parent_target"])] = bool
            fields[vol.Optional(f"{prefix}_dashboard_target", default=person["dashboard_target"])] = bool

        return self.async_show_form(step_id="people", data_schema=vol.Schema(fields))

    async def async_step_system(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
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

        schema = vol.Schema({
            vol.Optional("use_ui_config", default=opts.get("use_ui_config", True)): bool,
            vol.Optional("cooldown_seconds", default=opts.get("cooldown_seconds", 30)): _int_range(30, 0, 3600),
            vol.Optional("launches_before_mutual_destruction", default=opts.get("launches_before_mutual_destruction", 5)): _number_box(5, 2, 99),
            vol.Optional("chain_before_mutual_destruction", default=opts.get("chain_before_mutual_destruction", 4)): _number_box(4, 2, 99),
            vol.Optional("daily_reset_time", default=opts.get("daily_reset_time", "05:00:00")): str,
            vol.Optional("max_event_log", default=opts.get("max_event_log", 25)): _number_box(25, 5, 200),
            vol.Optional("allow_parent_targets_default", default=opts.get("allow_parent_targets_default", False)): bool,
            vol.Optional("require_station_match", default=opts.get("require_station_match", False)): bool,
            vol.Optional("require_key_for_launch", default=opts.get("require_key_for_launch", False)): bool,
            vol.Optional("pin_timeout_seconds", default=opts.get("pin_timeout_seconds", 60)): _int_range(60, 1, 3600),
            vol.Optional("max_bad_pin_attempts", default=opts.get("max_bad_pin_attempts", 3)): _number_box(3, 1, 20),
            vol.Optional("lockout_seconds_after_bad_pins", default=opts.get("lockout_seconds_after_bad_pins", 120)): _int_range(120, 1, 3600),
        })
        return self.async_show_form(step_id="system", data_schema=schema)

    async def async_step_stations(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts = _build_station_options(user_input, opts)
            opts["dashboard_station_id"] = str(user_input.get("dashboard_station_id", opts.get("dashboard_station_id", "dashboard")))
            opts["dashboard_default_target"] = str(user_input.get("dashboard_default_target", opts.get("dashboard_default_target", "")))
            return self.async_create_entry(title="", data=opts)

        stations = _station_defaults(opts)
        fields = {
            vol.Optional("dashboard_station_id", default=opts.get("dashboard_station_id", "dashboard")): str,
            vol.Optional("dashboard_default_target", default=opts.get("dashboard_default_target", "Henry")): str,
        }
        for idx, station in enumerate(stations, start=1):
            prefix = f"station_{idx}"
            fields[vol.Optional(f"{prefix}_id", default=station["id"])] = str
            fields[vol.Optional(f"{prefix}_name", default=station["name"])] = str
            fields[vol.Optional(f"{prefix}_enabled", default=station["enabled"])] = bool
            fields[vol.Optional(f"{prefix}_key_entity", default=station["key_entity"])] = str

        return self.async_show_form(step_id="stations", data_schema=vol.Schema(fields))

    async def async_step_adguard(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema({
            vol.Optional("dns_enabled", default=opts.get("dns_enabled", True)): bool,
            vol.Optional("adguard_base_url", default=opts.get("adguard_base_url", "")): str,
            vol.Optional("enforcement_mode", default=opts.get("enforcement_mode", "active")): vol.In(["active", "disabled"]),
            vol.Optional("mutual_destruction_scope", default=opts.get("mutual_destruction_scope", "default_targets")): vol.In(["default_targets", "all"]),
            vol.Optional("adguard_username_secret", default=opts.get("adguard_username_secret", "adguard_username")): str,
            vol.Optional("adguard_password_secret", default=opts.get("adguard_password_secret", "adguard_password")): str,
            vol.Optional("adguard_rule_prefix", default=opts.get("adguard_rule_prefix", "Family DEFCON Block")): str,
        })
        return self.async_show_form(step_id="adguard", data_schema=schema)

    async def async_step_penalties(self, user_input: dict[str, Any] | None = None):
        opts = self._pending
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="", data=opts)

        schema = vol.Schema({
            vol.Optional("first_strike_target_minutes", default=opts.get("first_strike_target_minutes", 30)): _int_range(30, 1, 999),
            vol.Optional("retaliator_extra_minutes", default=opts.get("retaliator_extra_minutes", 15)): _int_range(15, 1, 999),
            vol.Optional("retaliation_target_minutes", default=opts.get("retaliation_target_minutes", 30)): _int_range(30, 1, 999),
            vol.Optional("reattacker_extra_minutes", default=opts.get("reattacker_extra_minutes", 15)): _int_range(15, 1, 999),
            vol.Optional("reattack_target_minutes", default=opts.get("reattack_target_minutes", 45)): _int_range(45, 1, 999),
        })
        return self.async_show_form(step_id="penalties", data_schema=schema)

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None):
        """Advanced raw YAML import.

        This is intentionally opt-in. Empty fields stay empty and are not
        repopulated from older saved values unless advanced overrides are enabled.
        """
        opts = self._pending
        if user_input is not None:
            clear = bool(user_input.get("clear_advanced_yaml_overrides", False))
            enabled = bool(user_input.get("use_advanced_yaml_overrides", False))

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
                opts["auth_users_yaml"] = str(user_input.get("auth_users_yaml", "") or "")
                opts["stations_yaml"] = str(user_input.get("stations_yaml", "") or "")
                opts["adguard_clients_yaml"] = str(user_input.get("adguard_clients_yaml", "") or "")
                opts["penalties_yaml"] = str(user_input.get("penalties_yaml", "") or "")

            return self.async_create_entry(title="", data=opts)

        enabled = bool(opts.get("use_advanced_yaml_overrides", False))

        schema = vol.Schema({
            vol.Optional("use_advanced_yaml_overrides", default=enabled): bool,
            vol.Optional("clear_advanced_yaml_overrides", default=False): bool,
            vol.Optional("people_yaml", default=opts.get("people_yaml", "") if enabled else ""): str,
            vol.Optional("auth_users_yaml", default=opts.get("auth_users_yaml", "") if enabled else ""): str,
            vol.Optional("stations_yaml", default=opts.get("stations_yaml", "") if enabled else ""): str,
            vol.Optional("adguard_clients_yaml", default=opts.get("adguard_clients_yaml", "") if enabled else ""): str,
            vol.Optional("penalties_yaml", default=opts.get("penalties_yaml", "") if enabled else ""): str,
        })
        return self.async_show_form(step_id="advanced", data_schema=schema)
