"""Family DEFCON custom integration.

v1.4 keeps variable data in family_defcon.yaml, uses async-safe file loading, and manages AdGuard custom rules safely:
people, targets, PINs, stations, AdGuard URL, client names, penalties, timers, and DNS behavior.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Any

import aiohttp
import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.components import persistent_notification
from homeassistant.helpers import entity_registry as er
from homeassistant.util import yaml as yaml_util

from .const import (
    DOMAIN,
    DEFAULT_PEOPLE,
    DEFAULT_TARGETS,
    DEFAULT_PARENTS,
    STORAGE_KEY,
    STORAGE_VERSION,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)
CONFIG_PATH = "family_defcon.yaml"
PLATFORMS = ["sensor", "switch", "binary_sensor", "text", "select", "button"]

LAUNCH_SCHEMA = vol.Schema({
    vol.Required("launcher"): cv.string,
    vol.Required("target"): cv.string,
    vol.Optional("station", default=""): cv.string,
})

LAUNCH_WITH_PIN_SCHEMA = vol.Schema({
    vol.Required("pin"): cv.string,
    vol.Required("target"): cv.string,
    vol.Optional("station", default=""): cv.string,
})

BOOL_SCHEMA = vol.Schema({vol.Required("enabled"): cv.boolean})
PERSON_SCHEMA = vol.Schema({vol.Required("person"): cv.string})
DASHBOARD_KEYPRESS_SCHEMA = vol.Schema({vol.Required("digit"): cv.string})
DASHBOARD_PIN_SCHEMA = vol.Schema({vol.Required("pin"): cv.string})
DASHBOARD_TARGET_SCHEMA = vol.Schema({vol.Required("target"): cv.string})
HASH_PIN_SCHEMA = vol.Schema({vol.Required("pin"): cv.string})
AUTH_SOURCE_SCHEMA = vol.Schema({})
CONFIG_AUDIT_SCHEMA = vol.Schema({})
CLEANUP_TARGET_BUTTON_ENTITIES_SCHEMA = vol.Schema({vol.Optional("remove_old_select_target", default=True): cv.boolean, vol.Optional("remove_family_defcon_target_buttons", default=False): cv.boolean})





async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old Family DEFCON config entries safely.

    Older test builds changed the config flow VERSION without providing a migration
    handler, which can cause Home Assistant to report that the migration agent is
    not available. This migration is intentionally conservative. It preserves the
    user's existing data/options and only adds missing defaults used by newer UI
    option flows.
    """
    _LOGGER.info(
        "Migrating Family DEFCON config entry from version %s.%s",
        entry.version,
        entry.minor_version,
    )

    options = dict(entry.options or {})
    options.setdefault("use_ui_config", bool(options.get("use_ui_config", False)))
    options.setdefault("cooldown_seconds", int(options.get("cooldown_seconds", 30)))
    options.setdefault("launches_before_mutual_destruction", int(options.get("launches_before_mutual_destruction", 5)))
    options.setdefault("chain_before_mutual_destruction", int(options.get("chain_before_mutual_destruction", 4)))
    options.setdefault("daily_reset_time", str(options.get("daily_reset_time", "05:00:00")))
    options.setdefault("max_event_log", int(options.get("max_event_log", 25)))
    options.setdefault("allow_parent_targets_default", bool(options.get("allow_parent_targets_default", False)))
    options.setdefault("require_station_match", bool(options.get("require_station_match", False)))
    options.setdefault("require_key_for_launch", bool(options.get("require_key_for_launch", False)))
    options.setdefault("pin_timeout_seconds", int(options.get("pin_timeout_seconds", 60)))
    options.setdefault("max_bad_pin_attempts", int(options.get("max_bad_pin_attempts", 3)))
    options.setdefault("lockout_seconds_after_bad_pins", int(options.get("lockout_seconds_after_bad_pins", 120)))

    options.setdefault("dns_enabled", bool(options.get("dns_enabled", True)))
    options.setdefault("enforcement_mode", str(options.get("enforcement_mode", "active")))
    options.setdefault("mutual_destruction_scope", str(options.get("mutual_destruction_scope", "default_targets")))
    options.setdefault("adguard_base_url", str(options.get("adguard_base_url", "")))
    options.setdefault("adguard_username_secret", str(options.get("adguard_username_secret", "adguard_username")))
    options.setdefault("adguard_password_secret", str(options.get("adguard_password_secret", "adguard_password")))
    options.setdefault("adguard_rule_prefix", str(options.get("adguard_rule_prefix", "Family DEFCON Block")))

    options.setdefault("first_strike_target_minutes", int(options.get("first_strike_target_minutes", 30)))
    options.setdefault("retaliator_extra_minutes", int(options.get("retaliator_extra_minutes", 15)))
    options.setdefault("retaliation_target_minutes", int(options.get("retaliation_target_minutes", 30)))
    options.setdefault("reattacker_extra_minutes", int(options.get("reattacker_extra_minutes", 15)))
    options.setdefault("reattack_target_minutes", int(options.get("reattack_target_minutes", 45)))

    # Guided UI defaults only if no existing guided config exists.
    # Advanced raw YAML overrides caused confusion in early v5 builds.
    # Keep old text saved, but do not apply it unless the user explicitly enables the switch.
    options.setdefault("use_advanced_yaml_overrides", False)

    options.setdefault("people_list", options.get("people_list", []))
    options.setdefault("people_roles", options.get("people_roles", {}))
    options.setdefault("people_pins", {})
    options.setdefault("people_pin_hashes", options.get("people_pin_hashes", {}))
    options.setdefault("people_adguard_clients", options.get("people_adguard_clients", {}))
    options.setdefault("default_targets_list", options.get("default_targets_list", []))
    options.setdefault("parent_targets_list", options.get("parent_targets_list", []))
    options.setdefault("dashboard_targets_list", options.get("dashboard_targets_list", []))
    options.setdefault("dashboard_station_id", str(options.get("dashboard_station_id", "dashboard")))
    options.setdefault("dashboard_default_target", str(options.get("dashboard_default_target", "")))
    options.setdefault("stations_list", options.get("stations_list", []))

    station_id = str(options.get("dashboard_station_id", "dashboard") or "dashboard")
    stations_list = options.get("stations_list", [])
    if not isinstance(stations_list, list):
        stations_list = []
    if not any(isinstance(item, dict) and str(item.get("id", "")) == station_id for item in stations_list):
        stations_list.append({
            "id": station_id,
            "name": "Home Assistant Dashboard",
            "enabled": True,
            "key_entity": "",
        })
    options["stations_list"] = stations_list

    data = dict(entry.data or {})
    data.setdefault("name", data.get("name", "Family DEFCON"))
    data.setdefault("config_file", data.get("config_file", CONFIG_PATH))

    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=4,
        minor_version=0,
    )
    _LOGGER.info("Family DEFCON config entry migration complete.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Family DEFCON from a UI config entry."""
    config_file = entry.data.get("config_file", CONFIG_PATH)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config_entry"] = entry
    hass.data[DOMAIN]["config_path"] = config_file

    async def _options_updated(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        """Apply UI option changes to the active config when possible.

        Existing entity platforms are not fully unloaded by this legacy platform setup,
        so newly added people or dynamic target buttons still require a Home Assistant restart.
        Existing config values, PIN hashes, AdGuard client names, targets, penalties, and
        station settings are refreshed through the reload_config service.
        """
        hass.data.setdefault(DOMAIN, {})["config_entry"] = updated_entry
        if hass.data[DOMAIN].get("setup_complete") and hass.services.has_service(DOMAIN, "reload_config"):
            _LOGGER.info("Family DEFCON options updated. Applying active config. Restart Home Assistant if people or dashboard targets were added or removed.")
            await hass.services.async_call(DOMAIN, "reload_config", {}, blocking=True)
            persistent_notification.async_create(
                hass,
                "Family DEFCON settings were saved. Active config was reloaded. If you added, removed, or renamed people or dashboard targets, restart Home Assistant so generated entities are recreated.",
                title="Family DEFCON settings updated",
                notification_id="family_defcon_options_updated",
            )

    entry.async_on_unload(entry.add_update_listener(_options_updated))

    if hass.data[DOMAIN].get("setup_complete"):
        return True

    result = await async_setup(hass, {})
    if result:
        hass.data[DOMAIN]["setup_complete"] = True
    return result


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Family DEFCON config entry."""
    # Services and YAML backed shared state are registered globally.
    # Restarting Home Assistant is the safest way to fully unload this integration.
    return True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Family DEFCON."""
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def load_yaml(filename: str) -> dict:
        """Load a YAML file without blocking Home Assistant's event loop."""
        path = Path(hass.config.path(filename))
        if not path.exists():
            return {}

        def _read_yaml() -> dict:
            loaded = yaml.safe_load(path.read_text()) or {}
            return loaded if isinstance(loaded, dict) else {}

        try:
            return await hass.async_add_executor_job(_read_yaml)
        except Exception as err:
            _LOGGER.error("Family DEFCON could not load %s: %s", filename, err)
            return {}

    secrets_cache: dict[str, str] = {}

    async def get_secret(secret_name: str, default: str = "") -> str:
        """Read a secret from secrets.yaml without blocking the event loop."""
        if not secret_name:
            return default

        if not secrets_cache:
            secrets = await load_yaml("secrets.yaml")
            for key, value in secrets.items():
                secrets_cache[str(key)] = "" if value is None else str(value)

        return secrets_cache.get(secret_name, default)

    def normalize_config(raw: dict) -> dict:
        people = list(raw.get("people", DEFAULT_PEOPLE))
        default_targets = list(raw.get("default_targets", DEFAULT_TARGETS))
        parent_targets = list(raw.get("parent_targets", DEFAULT_PARENTS))
        penalties = raw.get("penalties", {}) if isinstance(raw.get("penalties", {}), dict) else {}
        auth = raw.get("auth", {}) if isinstance(raw.get("auth", {}), dict) else {}
        dns = raw.get("dns", {}) if isinstance(raw.get("dns", {}), dict) else {}
        adguard = dns.get("adguard_home", {}) if isinstance(dns.get("adguard_home", {}), dict) else {}

        stations_in = raw.get("stations", {}) if isinstance(raw.get("stations", {}), dict) else {}
        stations = {}
        for station_id, station_data in stations_in.items():
            if isinstance(station_data, dict):
                stations[str(station_id)] = {
                    "name": str(station_data.get("name", station_id)),
                    "commander": str(station_data.get("commander", "")),
                    "enabled": bool(station_data.get("enabled", True)),
                    "key_entity": str(station_data.get("key_entity", "")),
                }

        users = auth.get("users", {}) if isinstance(auth.get("users", {}), dict) else {}
        clients_in = adguard.get("clients", {}) if isinstance(adguard.get("clients", {}), dict) else {}
        clients = {}
        for person in people:
            entry = clients_in.get(person, person)
            if isinstance(entry, dict):
                clients[person] = {
                    "client_name": str(entry.get("client_name", person)),
                    "enabled": bool(entry.get("enabled", True)),
                }
            else:
                clients[person] = {"client_name": str(entry), "enabled": True}

        return {
            "people": people,
            "default_targets": default_targets,
            "parent_targets": parent_targets,
            "allow_parent_targets_default": bool(raw.get("allow_parent_targets_default", False)),
            "require_station_match": bool(raw.get("require_station_match", False)),
            "require_key_for_launch": bool(raw.get("require_key_for_launch", False)),
            "cooldown_seconds": int(raw.get("cooldown_seconds", 30)),
            "launches_before_mutual_destruction": int(raw.get("launches_before_mutual_destruction", 5)),
            "chain_before_mutual_destruction": int(raw.get("chain_before_mutual_destruction", 4)),
            "daily_reset_time": str(raw.get("daily_reset_time", "05:00:00")),
            "max_event_log": int(raw.get("max_event_log", 25)),
            "penalties": {
                "first_strike_target_minutes": int(penalties.get("first_strike_target_minutes", 30)),
                "retaliator_extra_minutes": int(penalties.get("retaliator_extra_minutes", 15)),
                "retaliation_target_minutes": int(penalties.get("retaliation_target_minutes", 30)),
                "reattacker_extra_minutes": int(penalties.get("reattacker_extra_minutes", 15)),
                "reattack_target_minutes": int(penalties.get("reattack_target_minutes", 45)),
            },
            "auth": {
                "mode": str(auth.get("mode", "pin")),
                "pin_timeout_seconds": int(auth.get("pin_timeout_seconds", 60)),
                "max_bad_pin_attempts": int(auth.get("max_bad_pin_attempts", 3)),
                "lockout_seconds_after_bad_pins": int(auth.get("lockout_seconds_after_bad_pins", 120)),
                "users": users,
            },
            "stations": stations,
            "dns": {
                "enabled": bool(dns.get("enabled", False)),
                "provider": str(dns.get("provider", "none")),
                "enforcement_mode": str(dns.get("enforcement_mode", "disabled")),
                "mutual_destruction_scope": str(dns.get("mutual_destruction_scope", "default_targets")),
                "custom_services": dns.get("custom_services", {}) if isinstance(dns.get("custom_services", {}), dict) else {},
                "adguard_home": {
                    "base_url": str(adguard.get("base_url", "")).rstrip("/"),
                    "username": str(adguard.get("username", "")),
                    "password": str(adguard.get("password", "")),
                    "username_secret": str(adguard.get("username_secret", "")),
                    "password_secret": str(adguard.get("password_secret", "")),
                    "rule_prefix": str(adguard.get("rule_prefix", "Family DEFCON Block")),
                    "clients": clients,
                },
            },
        }

    def _parse_ui_yaml(value: str, fallback):
        """Parse YAML from UI option text boxes."""
        if value in (None, ""):
            return fallback
        try:
            parsed = yaml_util.parse_yaml(str(value))
            return parsed if parsed is not None else fallback
        except Exception as err:
            _LOGGER.error("Family DEFCON UI YAML parse error: %s", err)
            return fallback

    def _string_list(value, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return list(fallback)

    def _dict_value(value, fallback: dict) -> dict:
        return value if isinstance(value, dict) else dict(fallback)

    def ensure_dashboard_station(normalized: dict) -> dict:
        """Guarantee the dashboard station exists.

        Older config entries may have dashboard.station_id set to "dashboard" but
        no matching station record in stations_list or YAML. Without this,
        dashboard launches fail with: Launch rejected. Unknown station dashboard.
        """
        dashboard = normalized.get("dashboard", {})
        if not isinstance(dashboard, dict):
            dashboard = {}
            normalized["dashboard"] = dashboard

        station_id = str(dashboard.get("station_id", "") or "dashboard")
        dashboard["station_id"] = station_id

        if not isinstance(normalized.get("stations"), dict):
            normalized["stations"] = {}

        if station_id not in normalized["stations"]:
            normalized["stations"][station_id] = {
                "name": "Home Assistant Dashboard",
                "enabled": True,
                "key_entity": "",
            }

        return normalized

    def validate_active_config(normalized: dict) -> dict:
        """Clean and validate cross references in the active normalized config."""
        people = [str(person) for person in normalized.get("people", []) if str(person).strip()]
        normalized["people"] = people
        people_set = set(people)

        normalized["default_targets"] = [
            str(person) for person in normalized.get("default_targets", [])
            if str(person) in people_set
        ]
        normalized["parent_targets"] = [
            str(person) for person in normalized.get("parent_targets", [])
            if str(person) in people_set
        ]

        auth_users = normalized.get("auth", {}).get("users", {})
        if not isinstance(auth_users, dict):
            auth_users = {}
        normalized["auth"]["users"] = {
            person: auth_users.get(person, {"role": "child"})
            for person in people
        }

        clients = normalized.get("dns", {}).get("adguard_home", {}).get("clients", {})
        if not isinstance(clients, dict):
            clients = {}
        normalized["dns"]["adguard_home"]["clients"] = {
            person: clients.get(person, {"client_name": person, "enabled": True})
            for person in people
        }

        dashboard = normalized.get("dashboard", {})
        if not isinstance(dashboard, dict):
            dashboard = {}
        dash_targets = dashboard.get("targets", normalized.get("default_targets", []))
        if not isinstance(dash_targets, list):
            dash_targets = normalized.get("default_targets", [])
        dashboard["targets"] = [str(person) for person in dash_targets if str(person) in people_set]
        if not dashboard["targets"]:
            dashboard["targets"] = normalized.get("default_targets", []) or people
        dashboard["default_target"] = str(dashboard.get("default_target") or (dashboard["targets"][0] if dashboard["targets"] else ""))
        if dashboard["default_target"] not in people_set and dashboard["targets"]:
            dashboard["default_target"] = dashboard["targets"][0]
        dashboard["station_id"] = str(dashboard.get("station_id", "dashboard") or "dashboard")
        normalized["dashboard"] = dashboard

        return ensure_dashboard_station(normalized)

    def apply_options_overrides(normalized: dict) -> dict:
        """Apply UI options over YAML values.

        v5.2 uses guided per-person setup fields instead of forcing YAML snippets.
        family_defcon.yaml remains a fallback and portable backup.
        """
        entry = hass.data.get(DOMAIN, {}).get("config_entry")
        opts = dict(getattr(entry, "options", {}) or {})

        use_ui_config = bool(opts.get("use_ui_config", False))
        if use_ui_config:
            people_list = opts.get("people_list")
            if isinstance(people_list, list) and people_list:
                normalized["people"] = [str(person) for person in people_list if str(person).strip()]

                roles = opts.get("people_roles", {}) if isinstance(opts.get("people_roles", {}), dict) else {}
                pins = opts.get("people_pins", {}) if isinstance(opts.get("people_pins", {}), dict) else {}
                pin_hashes = opts.get("people_pin_hashes", {}) if isinstance(opts.get("people_pin_hashes", {}), dict) else {}

                normalized["auth"]["users"] = {}
                for person in normalized["people"]:
                    user_data = {"role": str(roles.get(person, "child"))}
                    if str(pin_hashes.get(person, "")).strip():
                        user_data["pin_hash"] = str(pin_hashes.get(person, "")).strip()
                    elif str(pins.get(person, "")).strip():
                        # Legacy fallback only. Guided UI does not store plain PINs.
                        user_data["pin"] = str(pins.get(person, "")).strip()
                    normalized["auth"]["users"][person] = user_data

                normalized["default_targets"] = [
                    str(p) for p in opts.get("default_targets_list", [])
                    if str(p) in normalized["people"]
                ] if isinstance(opts.get("default_targets_list"), list) else normalized["default_targets"]

                normalized["parent_targets"] = [
                    str(p) for p in opts.get("parent_targets_list", [])
                    if str(p) in normalized["people"]
                ] if isinstance(opts.get("parent_targets_list"), list) else normalized["parent_targets"]

                clients = opts.get("people_adguard_clients", {}) if isinstance(opts.get("people_adguard_clients", {}), dict) else {}
                normalized["dns"]["adguard_home"]["clients"] = {}
                for person in normalized["people"]:
                    normalized["dns"]["adguard_home"]["clients"][person] = {
                        "client_name": str(clients.get(person, person)),
                        "enabled": True,
                    }

                dashboard_targets = opts.get("dashboard_targets_list", [])
                if isinstance(dashboard_targets, list):
                    dashboard_targets = [str(p) for p in dashboard_targets if str(p) in normalized["people"]]
                else:
                    dashboard_targets = normalized.get("dashboard", {}).get("targets", normalized["people"])

                normalized["dashboard"] = {
                    "station_id": str(opts.get("dashboard_station_id", "dashboard")),
                    "default_target": str(opts.get("dashboard_default_target", dashboard_targets[0] if dashboard_targets else "")),
                    "targets": dashboard_targets,
                }

            stations_list = opts.get("stations_list")
            if isinstance(stations_list, list) and stations_list:
                normalized["stations"] = {}
                for station in stations_list:
                    if not isinstance(station, dict):
                        continue
                    station_id = str(station.get("id", "")).strip()
                    if not station_id:
                        continue
                    normalized["stations"][station_id] = {
                        "name": str(station.get("name", station_id)),
                        "enabled": bool(station.get("enabled", True)),
                        "key_entity": str(station.get("key_entity", "")),
                    }

            # Advanced YAML import is now opt-in only.
            # Old advanced fields are ignored unless use_advanced_yaml_overrides is enabled.
            if bool(opts.get("use_advanced_yaml_overrides", False)):
                people_yaml = opts.get("people_yaml", "")
                if people_yaml:
                    parsed_people = _parse_ui_yaml(people_yaml, normalized.get("people", []))
                    normalized["people"] = _string_list(parsed_people, normalized.get("people", []))

                auth_users_yaml = opts.get("auth_users_yaml", "")
                if auth_users_yaml:
                    normalized["auth"]["users"] = _dict_value(
                        _parse_ui_yaml(auth_users_yaml, normalized.get("auth", {}).get("users", {})),
                        normalized.get("auth", {}).get("users", {}),
                    )

                stations_yaml = opts.get("stations_yaml", "")
                if stations_yaml:
                    stations = _dict_value(
                        _parse_ui_yaml(stations_yaml, normalized.get("stations", {})),
                        normalized.get("stations", {}),
                    )
                    normalized["stations"] = {}
                    for station_id, station_data in stations.items():
                        if isinstance(station_data, dict):
                            normalized["stations"][str(station_id)] = {
                                "name": str(station_data.get("name", station_id)),
                                "enabled": bool(station_data.get("enabled", True)),
                                "key_entity": str(station_data.get("key_entity", "")),
                            }

                adguard_clients_yaml = opts.get("adguard_clients_yaml", "")
                if adguard_clients_yaml:
                    clients = _dict_value(
                        _parse_ui_yaml(adguard_clients_yaml, normalized.get("dns", {}).get("adguard_home", {}).get("clients", {})),
                        normalized.get("dns", {}).get("adguard_home", {}).get("clients", {}),
                    )
                    normalized["dns"]["adguard_home"]["clients"] = {}
                    for person in normalized["people"]:
                        entry_data = clients.get(person, person) if isinstance(clients, dict) else person
                        if isinstance(entry_data, dict):
                            normalized["dns"]["adguard_home"]["clients"][person] = {
                                "client_name": str(entry_data.get("client_name", person)),
                                "enabled": bool(entry_data.get("enabled", True)),
                            }
                        else:
                            normalized["dns"]["adguard_home"]["clients"][person] = {
                                "client_name": str(entry_data),
                                "enabled": True,
                            }

                penalties_yaml = opts.get("penalties_yaml", "")
                if penalties_yaml:
                    penalties = _dict_value(
                        _parse_ui_yaml(penalties_yaml, normalized.get("penalties", {})),
                        normalized.get("penalties", {}),
                    )
                    for key, value in penalties.items():
                        if key in normalized["penalties"]:
                            normalized["penalties"][key] = int(value)

        int_keys = [
            "cooldown_seconds",
            "launches_before_mutual_destruction",
            "chain_before_mutual_destruction",
            "max_event_log",
        ]
        for key in int_keys:
            if key in opts and opts[key] not in (None, ""):
                normalized[key] = int(opts[key])

        auth_int_keys = [
            "pin_timeout_seconds",
            "max_bad_pin_attempts",
            "lockout_seconds_after_bad_pins",
        ]
        for key in auth_int_keys:
            if key in opts and opts[key] not in (None, ""):
                normalized["auth"][key] = int(opts[key])

        penalty_keys = [
            "first_strike_target_minutes",
            "retaliator_extra_minutes",
            "retaliation_target_minutes",
            "reattacker_extra_minutes",
            "reattack_target_minutes",
        ]
        for key in penalty_keys:
            if key in opts and opts[key] not in (None, ""):
                normalized["penalties"][key] = int(opts[key])

        bool_keys = [
            "allow_parent_targets_default",
            "require_station_match",
            "require_key_for_launch",
        ]
        for key in bool_keys:
            if key in opts:
                normalized[key] = bool(opts[key])

        if opts.get("daily_reset_time"):
            normalized["daily_reset_time"] = str(opts["daily_reset_time"])

        if "dns_enabled" in opts:
            normalized["dns"]["enabled"] = bool(opts["dns_enabled"])
        if opts.get("enforcement_mode"):
            normalized["dns"]["enforcement_mode"] = str(opts["enforcement_mode"])
        if opts.get("mutual_destruction_scope"):
            normalized["dns"]["mutual_destruction_scope"] = str(opts["mutual_destruction_scope"])
        if opts.get("adguard_base_url"):
            normalized["dns"]["adguard_home"]["base_url"] = str(opts["adguard_base_url"]).rstrip("/")
        if opts.get("adguard_username_secret"):
            normalized["dns"]["adguard_home"]["username_secret"] = str(opts["adguard_username_secret"])
        if opts.get("adguard_password_secret"):
            normalized["dns"]["adguard_home"]["password_secret"] = str(opts["adguard_password_secret"])
        if opts.get("adguard_rule_prefix"):
            normalized["dns"]["adguard_home"]["rule_prefix"] = str(opts["adguard_rule_prefix"])

        return validate_active_config(normalized)
    raw = await load_yaml(hass.data.get(DOMAIN, {}).get("config_path", CONFIG_PATH))
    if not raw:
        _LOGGER.warning("Family DEFCON config missing or empty at %s.", hass.config.path(CONFIG_PATH))
    hass.data[DOMAIN]["config"] = apply_options_overrides(normalize_config(raw))
    if not hass.data[DOMAIN]["config"]["people"]:
        _LOGGER.error("Family DEFCON has no people configured. Add people to /config/family_defcon.yaml.")

    stored = await store.async_load() or {}
    people = hass.data[DOMAIN]["config"]["people"]

    state = {
        "armed": bool(stored.get("armed", False)),
        "allow_parent_targets": bool(stored.get("allow_parent_targets", hass.data[DOMAIN]["config"]["allow_parent_targets_default"])),
        "mutual_destruction": bool(stored.get("mutual_destruction", False)),
        "daily_launches": int(stored.get("daily_launches", 0)),
        "conflict_chain": int(stored.get("conflict_chain", 0)),
        "last_launcher": str(stored.get("last_launcher", "")),
        "last_target": str(stored.get("last_target", "")),
        "last_event": str(stored.get("last_event", "System initialized.")),
        "event_log": list(stored.get("event_log", [])),
        "last_station_launch": dict(stored.get("last_station_launch", {})),
        "pin_bad_attempts": dict(stored.get("pin_bad_attempts", {})),
        "pin_locked_until": dict(stored.get("pin_locked_until", {})),
        "blocked_until": {person: None for person in people},
        "last_reset_date": str(stored.get("last_reset_date", "")),
        "adguard_applied": dict(stored.get("adguard_applied", {})),
        "adguard_last_sync": str(stored.get("adguard_last_sync", "")),
        "adguard_last_status": str(stored.get("adguard_last_status", "unknown")),
        "adguard_last_error": str(stored.get("adguard_last_error", "")),
        "adguard_managed_rule_count": int(stored.get("adguard_managed_rule_count", 0)),
        "dashboard_pin": "",
        "dashboard_target": str(stored.get("dashboard_target", "")),
        # Dashboard confirmation is intentionally never restored after restart.
        "dashboard_confirm": False,
    }

    for person, value in stored.get("blocked_until", {}).items():
        if person in state["blocked_until"] and value:
            try:
                state["blocked_until"][person] = datetime.fromisoformat(value)
            except Exception:
                state["blocked_until"][person] = None

    hass.data[DOMAIN]["state"] = state
    hass.data[DOMAIN]["store"] = store

    def conf() -> dict:
        return hass.data[DOMAIN]["config"]

    def st() -> dict:
        return hass.data[DOMAIN]["state"]

    async def save_state() -> None:
        payload = dict(st())

        # Privacy and safety:
        # Do not ever persist the live dashboard PIN or a confirmed launch state.
        # The PIN is only valid while it is held in integration memory.
        payload["dashboard_pin"] = ""
        payload["dashboard_confirm"] = False

        payload["blocked_until"] = {
            person: value.isoformat() if isinstance(value, datetime) else None
            for person, value in st()["blocked_until"].items()
        }
        await store.async_save(payload)

    async def update_entities() -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

    async def cleanup_target_button_entity_registry(
        *,
        remove_old_select_target: bool = True,
        remove_family_defcon_target_buttons: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Remove stale generated target button entity registry entries."""
        registry = er.async_get(hass)
        removed: list[str] = []
        failed: list[str] = []

        for entry in list(registry.entities.values()):
            entity_id = str(entry.entity_id)
            platform = str(entry.platform)
            unique_id = str(entry.unique_id)

            should_remove = False

            if remove_old_select_target and entity_id.startswith("button.select_target_"):
                should_remove = True

            if (
                remove_family_defcon_target_buttons
                and platform == DOMAIN
                and unique_id.startswith("family_defcon_select_target_")
            ):
                should_remove = True

            if not should_remove:
                continue

            try:
                registry.async_remove(entity_id)
                removed.append(entity_id)
            except Exception as exc:
                failed.append(f"{entity_id}: {exc}")

        return removed, failed

    def fire_family_event(event_name: str, **data) -> None:
        """Expose Family DEFCON actions as Home Assistant events for automations."""
        hass.bus.async_fire(f"family_defcon_{event_name}", data)

    async def log_event(message: str) -> None:
        st()["last_event"] = message
        event_log = st().setdefault("event_log", [])
        event_log.insert(0, {"time": datetime.now().isoformat(timespec="seconds"), "message": message})
        del event_log[conf()["max_event_log"]:]
        await save_state()
        await update_entities()

    def valid_targets() -> list[str]:
        if st()["allow_parent_targets"]:
            return list(dict.fromkeys(conf()["default_targets"] + conf()["parent_targets"]))
        return conf()["default_targets"]

    def is_blocked(person: str) -> bool:
        if st()["mutual_destruction"]:
            scope = str(conf().get("dns", {}).get("mutual_destruction_scope", "default_targets")).lower()
            if scope in ("all", "everyone", "people", "all_people"):
                return person in conf()["people"]
            return person in conf()["default_targets"]
        until = st()["blocked_until"].get(person)
        return isinstance(until, datetime) and until > datetime.now()

    def active_block_count() -> int:
        return sum(1 for person in conf()["people"] if is_blocked(person))

    def current_defcon_level() -> int:
        """Calculate DEFCON from the worst active condition, matching the level sensor."""
        if st()["mutual_destruction"]:
            return 1

        daily_launches = int(st().get("daily_launches", 0))
        conflict_chain = int(st().get("conflict_chain", 0))
        launch_limit = int(conf().get("launches_before_mutual_destruction", 5))
        chain_limit = int(conf().get("chain_before_mutual_destruction", 4))
        active_blocks = active_block_count()

        if (launch_limit > 1 and daily_launches >= launch_limit - 1) or (chain_limit > 1 and conflict_chain >= chain_limit - 1):
            return 2

        if conflict_chain >= 2 or active_blocks >= 2:
            return 3

        if active_blocks >= 1 or conflict_chain >= 1:
            return 4

        return 5

    async def adguard_call_json(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[bool, Any]:
        """Call AdGuard Home using JSON."""
        adguard = conf()["dns"]["adguard_home"]
        base_url = adguard["base_url"]
        if not base_url:
            _LOGGER.error("Family DEFCON AdGuard base_url is blank.")
            return False, None

        username = adguard["username"] or await get_secret(adguard["username_secret"])
        password = adguard["password"] or await get_secret(adguard["password_secret"])
        auth = aiohttp.BasicAuth(username, password) if username or password else None

        session = async_get_clientsession(hass)
        try:
            if method == "GET":
                async with session.get(f"{base_url}{path}", auth=auth, timeout=10) as resp:
                    text = await resp.text()
                    if resp.status not in (200, 204):
                        _LOGGER.warning("Family DEFCON AdGuard GET failed: %s %s %s", path, resp.status, text)
                        if "state" in hass.data.get(DOMAIN, {}):
                            st()["adguard_last_status"] = "error"
                            st()["adguard_last_error"] = f"GET {path} failed: HTTP {resp.status}"
                            st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
                        return False, None
                    try:
                        return True, await resp.json()
                    except Exception:
                        return True, text

            async with session.post(f"{base_url}{path}", json=payload or {}, auth=auth, timeout=10) as resp:
                text = await resp.text()
                if resp.status not in (200, 204):
                    _LOGGER.warning("Family DEFCON AdGuard POST failed: %s %s %s", path, resp.status, text)
                    if "state" in hass.data.get(DOMAIN, {}):
                        st()["adguard_last_status"] = "error"
                        st()["adguard_last_error"] = f"POST {path} failed: HTTP {resp.status}"
                        st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
                    return False, None
                try:
                    return True, await resp.json()
                except Exception:
                    return True, text
        except Exception as err:
            _LOGGER.error("Family DEFCON AdGuard call error: %s %s", path, err)
            if "state" in hass.data.get(DOMAIN, {}):
                st()["adguard_last_status"] = "error"
                st()["adguard_last_error"] = f"{path}: {err}"
                st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
            return False, None

    def adguard_rule_for_person(person: str) -> str | None:
        adguard = conf()["dns"]["adguard_home"]
        client = adguard["clients"].get(person)
        if not client or not client.get("enabled", True):
            return None
        client_name = client["client_name"]
        return f"||*^$client='{client_name}'"

    def desired_adguard_rules() -> list[str]:
        rules: list[str] = []
        for person in conf()["people"]:
            if is_blocked(person):
                rule = adguard_rule_for_person(person)
                if rule:
                    rules.append(rule)
        return rules

    async def adguard_apply_rules() -> None:
        """Preserve existing AdGuard custom rules and replace only the Family DEFCON block."""
        adguard = conf()["dns"]["adguard_home"]
        start_marker = str(adguard.get("managed_start_marker", "! FAMILY DEFCON START"))
        end_marker = str(adguard.get("managed_end_marker", "! FAMILY DEFCON END"))

        ok, existing = await adguard_call_json("GET", "/control/filtering/status")
        if not ok:
            await save_state()
            await update_entities()
            return

        if isinstance(existing, dict):
            raw_rules = existing.get("user_rules", existing.get("rules"))
            if raw_rules is None:
                _LOGGER.error(
                    "Family DEFCON AdGuard status response did not include user_rules or rules. "
                    "Refusing to overwrite custom filtering rules. Keys returned: %s",
                    list(existing.keys()),
                )
                st()["adguard_last_status"] = "error"
                st()["adguard_last_error"] = "AdGuard status response missing user_rules/rules."
                st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
                await save_state()
                await update_entities()
                return
            rules = list(raw_rules)
        elif isinstance(existing, list):
            rules = list(existing)
        elif isinstance(existing, str):
            rules = [line for line in existing.splitlines() if line.strip()]
        else:
            _LOGGER.error(
                "Family DEFCON AdGuard status response had unexpected type %s. "
                "Refusing to overwrite custom filtering rules.",
                type(existing).__name__,
            )
            st()["adguard_last_status"] = "error"
            st()["adguard_last_error"] = f"Unexpected AdGuard status type: {type(existing).__name__}"
            st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
            await save_state()
            await update_entities()
            return

        cleaned: list[str] = []
        skipping = False
        for rule in rules:
            if rule == start_marker:
                skipping = True
                continue
            if rule == end_marker:
                skipping = False
                continue
            if not skipping:
                cleaned.append(rule)

        managed_rules = desired_adguard_rules()
        new_rules = cleaned
        if managed_rules:
            new_rules = cleaned + [start_marker] + managed_rules + [end_marker]

        ok, _ = await adguard_call_json("POST", "/control/filtering/set_rules", {"rules": new_rules})
        if ok:
            st()["adguard_applied"] = {person: is_blocked(person) for person in conf()["people"]}
            st()["adguard_last_status"] = "ok"
            st()["adguard_last_error"] = ""
            st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
            st()["adguard_managed_rule_count"] = len(managed_rules)
            await save_state()
            await update_entities()
        else:
            st()["adguard_last_status"] = "error"
            st()["adguard_last_error"] = "AdGuard set_rules failed."
            st()["adguard_last_sync"] = datetime.now().isoformat(timespec="seconds")
            await save_state()
            await update_entities()

    async def call_custom_action(action_def: dict[str, Any] | None) -> None:
        if not isinstance(action_def, dict):
            return
        action = action_def.get("action") or action_def.get("service")
        if not action or "." not in action:
            return
        domain, service = action.split(".", 1)
        service_data = dict(action_def.get("data", {}))
        target = action_def.get("target")
        if isinstance(target, dict):
            service_data.update(target)
        await hass.services.async_call(domain, service, service_data, blocking=False)

    async def enforce_now() -> None:
        dns = conf()["dns"]
        if not dns["enabled"] or dns["enforcement_mode"] != "active":
            return

        provider = dns["provider"]

        if provider == "adguard_home":
            await adguard_apply_rules()
            return

        if provider == "custom_services":
            custom = dns["custom_services"]
            people_actions = custom.get("people", {})
            groups = custom.get("groups", {})
            if st()["mutual_destruction"]:
                scope = dns.get("mutual_destruction_scope", "default_targets")
                group_action = groups.get(scope, {}).get("block")
                if group_action:
                    await call_custom_action(group_action)
                    return
            for person in conf()["people"]:
                actions = people_actions.get(person, {})
                await call_custom_action(actions.get("block") if is_blocked(person) else actions.get("unblock"))

    def hash_pin_value(pin: str) -> str:
        """Return a fast salted SHA256 hash string for a 4 digit local dashboard PIN."""
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
        return f"sha256${salt}${digest}"

    def verify_pin_value(pin: str, user_data: dict[str, Any]) -> bool:
        """Verify fast SHA256 hashes, old PBKDF2 hashes, or legacy plain text PINs."""
        stored_hash = str(user_data.get("pin_hash", "") or "")
        if stored_hash:
            try:
                parts = stored_hash.split("$")
                algo = parts[0]

                if algo == "sha256" and len(parts) == 3:
                    _, salt, expected = parts
                    digest = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
                    return hmac.compare_digest(digest, expected)

                if algo == "pbkdf2_sha256" and len(parts) == 4:
                    _, iterations_raw, salt, expected = parts
                    digest = hashlib.pbkdf2_hmac(
                        "sha256",
                        str(pin).encode(),
                        salt.encode(),
                        int(iterations_raw),
                    ).hex()
                    return hmac.compare_digest(digest, expected)

                return False
            except Exception:
                return False

        # Backward compatible fallback. Prefer pin_hash in new configs.
        return hmac.compare_digest(str(user_data.get("pin", "")), str(pin))

    def station_record(station: str):
        stations = conf()["stations"]
        dashboard = conf().get("dashboard", {})
        dashboard_station_id = str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"

        if station in stations:
            return station, stations[station]

        # Safety fallback for older migrated configs where the dashboard station record was missing.
        if station == dashboard_station_id:
            return dashboard_station_id, {
                "name": "Home Assistant Dashboard",
                "enabled": True,
                "key_entity": "",
            }

        for station_id, record in stations.items():
            if record.get("name") == station:
                return station_id, record
        return station, None

    async def validate_station(launcher: str, station: str) -> tuple[bool, str]:
        if not station:
            return False, "Launch rejected. Missing station."
        station_id, record = station_record(station)
        if record is None:
            return False, f"Launch rejected. Unknown station {station}."
        if not record.get("enabled", True):
            return False, f"Launch rejected. {record.get('name', station_id)} is disabled."

        if conf()["require_station_match"] and conf()["auth"]["mode"] != "pin":
            commander = record.get("commander")
            if commander and commander != launcher:
                return False, f"Launch rejected. {record.get('name', station_id)} belongs to {commander}."

        key_entity = record.get("key_entity")
        if conf()["require_key_for_launch"] and key_entity and not hass.states.is_state(key_entity, "on"):
            return False, f"Launch rejected. Key is not active for {record.get('name', station_id)}."

        cooldown = conf()["cooldown_seconds"]
        last_raw = st()["last_station_launch"].get(station_id)
        if last_raw:
            try:
                last = datetime.fromisoformat(last_raw)
                if (datetime.now() - last).total_seconds() < cooldown:
                    return False, f"Launch rejected. {record.get('name', station_id)} is cooling down."
            except Exception:
                pass
        st()["last_station_launch"][station_id] = datetime.now().isoformat()
        return True, ""

    async def add_timeout(person: str, minutes: int) -> None:
        now = datetime.now()
        current = st()["blocked_until"].get(person)
        base = current if isinstance(current, datetime) and current > now else now
        st()["blocked_until"][person] = base + timedelta(minutes=minutes)

    async def reject_launch(reason: str, launcher: str = "", target: str = "", station: str = "") -> None:
        message = f"Launch rejected. {reason}"
        await log_event(message)
        fire_family_event(
            "launch_rejected",
            reason=reason,
            launcher=launcher,
            target=target,
            station=station,
            message=message,
        )

    async def apply_launch(launcher: str, target: str, station: str) -> None:
        if not st()["armed"]:
            await reject_launch("Command system is not armed.", launcher, target, station)
            return
        if launcher not in conf()["people"]:
            await reject_launch(f"Unknown launcher {launcher}.", launcher, target, station)
            return
        if target not in valid_targets():
            await reject_launch(f"{target} is protected.", launcher, target, station)
            return
        if launcher == target:
            await reject_launch("Self targeting is not allowed.", launcher, target, station)
            return

        ok, reason = await validate_station(launcher, station)
        if not ok:
            await reject_launch(reason.replace("Launch rejected. ", ""), launcher, target, station)
            return

        new_launches = st()["daily_launches"] + 1
        is_retaliation = launcher == st()["last_target"] and target == st()["last_launcher"]
        new_chain = st()["conflict_chain"] + 1 if is_retaliation else 1

        st()["daily_launches"] = new_launches
        st()["conflict_chain"] = new_chain
        st()["last_launcher"] = launcher
        st()["last_target"] = target

        p = conf()["penalties"]
        if new_launches >= conf()["launches_before_mutual_destruction"] or new_chain >= conf()["chain_before_mutual_destruction"]:
            st()["mutual_destruction"] = True
            message = f"DEFCON 1. Mutual WiFi Destruction activated by {launcher} targeting {target}."
            await log_event(message)
            fire_family_event(
                "mutual_destruction",
                launcher=launcher,
                target=target,
                station=station,
                defcon_level=1,
                daily_launches=new_launches,
                conflict_chain=new_chain,
                message=message,
            )
            fire_family_event(
                "launch",
                launcher=launcher,
                target=target,
                station=station,
                defcon_level=1,
                daily_launches=new_launches,
                conflict_chain=new_chain,
                mutual_destruction=True,
                minutes=0,
                message=message,
            )
            await enforce_now()
            return

        event_minutes = 0
        event_kind = "launch"

        if new_chain == 1:
            event_minutes = p["first_strike_target_minutes"]
            await add_timeout(target, event_minutes)
            level = current_defcon_level()
            message = (
                f"DEFCON {level}. {launcher} launched at {target}. "
                f"{target} receives {event_minutes} minute timeout."
            )
            await log_event(message)
        elif new_chain == 2:
            event_kind = "retaliation"
            await add_timeout(launcher, p["retaliator_extra_minutes"])
            event_minutes = p["retaliation_target_minutes"]
            await add_timeout(target, event_minutes)
            level = current_defcon_level()
            message = (
                f"DEFCON {level}. Retaliation detected. "
                f"{launcher} receives +{p['retaliator_extra_minutes']} minutes. "
                f"{target} receives {event_minutes} minutes."
            )
            await log_event(message)
        elif new_chain >= 3:
            event_kind = "escalation"
            await add_timeout(launcher, p["reattacker_extra_minutes"])
            event_minutes = p["reattack_target_minutes"]
            await add_timeout(target, event_minutes)
            level = current_defcon_level()
            next_warning = " Next retaliation triggers mutual destruction." if level == 2 else ""
            message = (
                f"DEFCON {level}. Escalation warning. "
                f"{launcher} receives +{p['reattacker_extra_minutes']} minutes. "
                f"{target} receives {event_minutes} minutes."
                f"{next_warning}"
            )
            await log_event(message)

        fire_family_event(
            "launch",
            launcher=launcher,
            target=target,
            station=station,
            defcon_level=level,
            daily_launches=new_launches,
            conflict_chain=new_chain,
            kind=event_kind,
            minutes=event_minutes,
            mutual_destruction=False,
            message=message,
        )

        await enforce_now()

    async def handle_launch(call: ServiceCall) -> None:
        await apply_launch(call.data["launcher"], call.data["target"], call.data.get("station", ""))

    async def handle_launch_with_pin(call: ServiceCall) -> None:
        station = call.data.get("station", "")
        pin = str(call.data.get("pin", ""))

        if len(pin) > 4:
            message = f"Launch rejected. PIN longer than 4 characters at {station or 'unknown station'}."
            await log_event(message)
            fire_family_event("launch_rejected", reason="PIN longer than 4 characters.", station=station, message=message)
            return
        locked_raw = st()["pin_locked_until"].get(station)
        if locked_raw:
            try:
                locked_until = datetime.fromisoformat(locked_raw)
                if locked_until > datetime.now():
                    message = f"PIN entry locked at {station} until {locked_until.strftime('%H:%M:%S')}."
                    await log_event(message)
                    fire_family_event(
                        "pin_lockout",
                        station=station,
                        locked_until=locked_until.isoformat(),
                        message=message,
                    )
                    return
            except Exception:
                pass

        launcher = None
        for person, data in conf()["auth"]["users"].items():
            if verify_pin_value(pin, data if isinstance(data, dict) else {}):
                launcher = person
                break

        if not launcher:
            attempts = int(st()["pin_bad_attempts"].get(station, 0)) + 1
            st()["pin_bad_attempts"][station] = attempts
            entry = hass.data.get(DOMAIN, {}).get("config_entry")
            opts = dict(getattr(entry, "options", {}) or {})
            source = "UI options" if bool(opts.get("use_ui_config", False)) else "YAML"
            advanced = "on" if bool(opts.get("use_advanced_yaml_overrides", False)) else "off"
            hashed_users = [
                person for person, data in conf()["auth"]["users"].items()
                if isinstance(data, dict) and data.get("pin_hash")
            ]

            if attempts >= conf()["auth"]["max_bad_pin_attempts"]:
                until = datetime.now() + timedelta(seconds=conf()["auth"]["lockout_seconds_after_bad_pins"])
                st()["pin_locked_until"][station] = until.isoformat()
                st()["pin_bad_attempts"][station] = 0
                message = (
                    f"Too many bad PIN attempts at {station}. Terminal locked temporarily. "
                    f"Auth source: {source}. Advanced YAML overrides: {advanced}."
                )
                await log_event(message)
                fire_family_event(
                    "pin_lockout",
                    station=station,
                    attempts=attempts,
                    locked_until=until.isoformat(),
                    message=message,
                )
            else:
                message = (
                    f"Bad PIN attempt at {station}. Auth source: {source}. "
                    f"Advanced YAML overrides: {advanced}. "
                    f"Hashed PIN users: {', '.join(hashed_users) if hashed_users else 'none'}."
                )
                await log_event(message)
                fire_family_event(
                    "bad_pin",
                    station=station,
                    attempts=attempts,
                    max_attempts=conf()["auth"]["max_bad_pin_attempts"],
                    message=message,
                )
            return

        st()["pin_bad_attempts"][station] = 0
        await apply_launch(launcher, call.data["target"], station)

    async def handle_clear_all(call: ServiceCall) -> None:
        st()["mutual_destruction"] = False
        st()["daily_launches"] = 0
        st()["conflict_chain"] = 0
        st()["last_launcher"] = ""
        st()["last_target"] = ""
        for person in conf()["people"]:
            st()["blocked_until"][person] = None
        await log_event("All DEFCON timeouts cleared.")
        fire_family_event("clear_all", message="All DEFCON timeouts cleared.")
        await enforce_now()

    async def handle_stand_down(call: ServiceCall) -> None:
        st()["conflict_chain"] = 0
        st()["last_launcher"] = ""
        st()["last_target"] = ""
        await log_event("Stand down accepted. Conflict chain reset.")

    async def handle_set_armed(call: ServiceCall) -> None:
        st()["armed"] = bool(call.data["enabled"])
        await log_event("Command system armed." if call.data["enabled"] else "Command system disarmed.")

    async def handle_set_parent_targets(call: ServiceCall) -> None:
        st()["allow_parent_targets"] = bool(call.data["enabled"])
        await log_event("Parent 1 and Parent 2 are targetable." if call.data["enabled"] else "Parent 1 and Parent 2 are protected.")

    async def handle_enforce_now(call: ServiceCall) -> None:
        await enforce_now()
        await log_event("Enforcement reapplied.")

    async def handle_reload_config(call: ServiceCall) -> None:
        secrets_cache.clear()
        hass.data[DOMAIN]["config"] = apply_options_overrides(normalize_config(await load_yaml(hass.data.get(DOMAIN, {}).get("config_path", CONFIG_PATH))))

        # Keep runtime state aligned with the active people list.
        active_people = list(conf().get("people", []))
        st()["blocked_until"] = {person: st().get("blocked_until", {}).get(person) for person in active_people}
        st()["adguard_applied"] = {person: st().get("adguard_applied", {}).get(person, False) for person in active_people}

        targets = dashboard_targets()
        if st().get("dashboard_target") not in targets:
            dash = dashboard_config()
            default_target = str(dash.get("default_target", "")) if isinstance(dash, dict) else ""
            st()["dashboard_target"] = default_target if default_target in targets else (targets[0] if targets else "")

        st()["dashboard_pin"] = ""
        st()["dashboard_confirm"] = False

        entry = hass.data.get(DOMAIN, {}).get("config_entry")
        opts = dict(getattr(entry, "options", {}) or {})
        await log_event("Config reloaded. Source: " + ("UI options" if bool(opts.get("use_ui_config", False)) else "YAML") + ". Restart Home Assistant if people or dashboard targets were added, removed, or renamed.")

    async def handle_block_person(call: ServiceCall) -> None:
        person = call.data["person"]
        if person in conf()["people"]:
            await add_timeout(person, 999 * 60)
            await log_event(f"{person} manually blocked.")
            await enforce_now()

    async def handle_unblock_person(call: ServiceCall) -> None:
        person = call.data["person"]
        if person in conf()["people"]:
            st()["blocked_until"][person] = None
            await log_event(f"{person} manually unblocked.")
            await enforce_now()

    async def handle_hash_pin(call: ServiceCall) -> None:
        pin_hash = hash_pin_value(str(call.data["pin"]))
        persistent_notification.async_create(
            hass,
            f"Copy this into family_defcon.yaml under the user as pin_hash. Remove the plain pin after testing.\n\n`{pin_hash}`",
            title="Family DEFCON PIN Hash",
            notification_id="family_defcon_pin_hash",
        )
        await log_event("PIN hash generated in Home Assistant notifications.")

    async def handle_config_audit_status(call: ServiceCall) -> None:
        """Log a safe audit of active config variables without exposing PIN values."""
        entry = hass.data.get(DOMAIN, {}).get("config_entry")
        opts = dict(getattr(entry, "options", {}) or {})
        active = conf()

        auth_users = active.get("auth", {}).get("users", {})
        hash_users = [person for person, data in auth_users.items() if isinstance(data, dict) and data.get("pin_hash")]
        legacy_pin_users = [person for person, data in auth_users.items() if isinstance(data, dict) and data.get("pin") and not data.get("pin_hash")]

        stations = active.get("stations", {})
        dashboard = active.get("dashboard", {})
        dashboard_station_id = str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"
        missing_station = dashboard_station_id not in stations

        dashboard_targets = dashboard.get("targets", []) if isinstance(dashboard, dict) else []
        unknown_targets = [target for target in dashboard_targets if target not in active.get("people", [])]

        await log_event(
            "Config audit. "
            + f"Source: {'UI options' if bool(opts.get('use_ui_config', False)) else 'YAML'}. "
            + f"Advanced YAML overrides: {'on' if bool(opts.get('use_advanced_yaml_overrides', False)) else 'off'}. "
            + f"People: {len(active.get('people', []))}. "
            + f"Dashboard station: {dashboard_station_id} ({'missing' if missing_station else 'ok'}). "
            + f"Dashboard targets: {', '.join(dashboard_targets) if dashboard_targets else 'none'}. "
            + f"Unknown targets: {', '.join(unknown_targets) if unknown_targets else 'none'}. "
            + f"Hashed PIN users: {', '.join(hash_users) if hash_users else 'none'}. "
            + f"Legacy plain PIN users: {', '.join(legacy_pin_users) if legacy_pin_users else 'none'}."
        )

    async def handle_auth_config_status(call: ServiceCall) -> None:
        """Report whether active auth came from UI options or YAML without revealing PINs."""
        entry = hass.data.get(DOMAIN, {}).get("config_entry")
        opts = dict(getattr(entry, "options", {}) or {})
        use_ui = bool(opts.get("use_ui_config", False))
        users = conf().get("auth", {}).get("users", {})
        hash_users = [person for person, data in users.items() if isinstance(data, dict) and data.get("pin_hash")]
        legacy_pin_users = [person for person, data in users.items() if isinstance(data, dict) and data.get("pin") and not data.get("pin_hash")]
        await log_event(
            "Auth config source: "
            + ("UI options" if use_ui else "YAML")
            + f". Advanced YAML overrides: {'on' if bool(opts.get('use_advanced_yaml_overrides', False)) else 'off'}."
            + f" Hashed PIN users: {', '.join(hash_users) if hash_users else 'none'}."
            + f" Legacy plain PIN users: {', '.join(legacy_pin_users) if legacy_pin_users else 'none'}."
        )

    async def handle_migrate_entity_ids(call: ServiceCall) -> None:
        registry = er.async_get(hass)
        migrations = {
            "text.dashboard_pin": "text.family_defcon_dashboard_pin",
            "select.dashboard_target": "select.family_defcon_dashboard_target",
            "sensor.dashboard_people": "sensor.family_defcon_dashboard_people",
            "binary_sensor.dashboard_target_confirmed": "binary_sensor.family_defcon_dashboard_target_confirmed",
            "button.dashboard_confirm_targeting": "button.family_defcon_dashboard_confirm_targeting",
            "button.dashboard_launch": "button.family_defcon_dashboard_launch",
            "button.dashboard_cancel": "button.family_defcon_dashboard_cancel",
            "switch.family_defcon_allow_mom_and_dad_targets": "switch.family_defcon_allow_parent_targets",
        }
        changed = []
        skipped = []
        for old_entity_id, new_entity_id in migrations.items():
            old_entry = registry.async_get(old_entity_id)
            new_entry = registry.async_get(new_entity_id)
            if old_entry is not None and new_entry is None:
                registry.async_update_entity(old_entity_id, new_entity_id=new_entity_id)
                changed.append(f"{old_entity_id} → {new_entity_id}")
            elif old_entry is not None and new_entry is not None:
                skipped.append(f"{old_entity_id} skipped because {new_entity_id} already exists")

        message = "Entity ID migration complete."
        if changed:
            message += " Renamed: " + "; ".join(changed) + "."
        if skipped:
            message += " Skipped: " + "; ".join(skipped) + "."
        await log_event(message)

    async def handle_dashboard_keypress(call: ServiceCall) -> None:
        digit = str(call.data["digit"])
        if digit not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            return
        current = "".join(ch for ch in str(st().get("dashboard_pin", "")) if ch.isdigit())
        if len(current) >= 4:
            return
        st()["dashboard_pin"] = current + digit
        st()["dashboard_confirm"] = False
        await update_entities()

    async def handle_dashboard_backspace(call: ServiceCall) -> None:
        current = "".join(ch for ch in str(st().get("dashboard_pin", "")) if ch.isdigit())
        st()["dashboard_pin"] = current[:-1]
        st()["dashboard_confirm"] = False
        await update_entities()

    async def handle_dashboard_clear_pin(call: ServiceCall) -> None:
        st()["dashboard_pin"] = ""
        st()["dashboard_confirm"] = False
        await update_entities()

    async def handle_dashboard_set_pin(call: ServiceCall) -> None:
        pin = "".join(ch for ch in str(call.data["pin"]) if ch.isdigit())
        st()["dashboard_pin"] = pin[:4]
        st()["dashboard_confirm"] = False
        await update_entities()

    async def handle_dashboard_select_target(call: ServiceCall) -> None:
        target = str(call.data["target"])
        targets = dashboard_targets()
        if target not in targets:
            await log_event(f"Dashboard target rejected. {target} is not in dashboard targets.")
            return
        st()["dashboard_target"] = target
        st()["dashboard_confirm"] = False
        await save_state()
        await update_entities()

    def dashboard_config() -> dict:
        dash = conf().get("dashboard", {})
        return dash if isinstance(dash, dict) else {}

    def dashboard_targets() -> list[str]:
        dash = dashboard_config()
        configured = dash.get("targets")
        if isinstance(configured, list) and configured:
            return [str(item) for item in configured]
        return list(dict.fromkeys(conf()["default_targets"] + conf()["parent_targets"]))

    def dashboard_station_id() -> str:
        return str(dashboard_config().get("station_id", "dashboard"))

    async def dashboard_set_pin(pin: str) -> None:
        st()["dashboard_pin"] = str(pin)
        await update_entities()

    async def dashboard_set_target(target: str) -> None:
        st()["dashboard_target"] = str(target)
        await save_state()
        await update_entities()

    async def dashboard_set_confirm(confirm: bool) -> None:
        st()["dashboard_confirm"] = bool(confirm)
        await update_entities()

    async def dashboard_cancel() -> None:
        st()["dashboard_pin"] = ""
        targets = dashboard_targets()
        st()["dashboard_target"] = targets[0] if targets else ""
        st()["dashboard_confirm"] = False
        await save_state()
        await update_entities()

    async def dashboard_launch() -> None:
        pin = str(st().get("dashboard_pin", ""))
        target = str(st().get("dashboard_target", ""))
        if not pin:
            await log_event("Dashboard launch rejected. Missing PIN.")
            await dashboard_cancel()
            return
        if not target:
            await log_event("Dashboard launch rejected. Missing target.")
            await dashboard_cancel()
            return

        await apply_launch_with_dashboard_pin(pin, target, dashboard_station_id())
        st()["dashboard_pin"] = ""
        st()["dashboard_confirm"] = False
        await save_state()
        await update_entities()

    async def apply_launch_with_dashboard_pin(pin: str, target: str, station: str) -> None:
        """Compatibility helper for any older dashboard launch path."""
        launcher = None
        for person, data in conf()["auth"]["users"].items():
            if verify_pin_value(pin, data if isinstance(data, dict) else {}):
                launcher = person
                break

        if not launcher:
            await log_event(f"Bad PIN attempt at {station}.")
            fire_family_event("bad_pin", station=station, attempts=1, max_attempts=conf()["auth"]["max_bad_pin_attempts"], message=f"Bad PIN attempt at {station}.")
            return

        await apply_launch(launcher, target, station)

    async def handle_cleanup_target_button_entities(call: ServiceCall) -> None:
        """Remove stale generated target button entity registry entries."""
        remove_old_select_target = bool(call.data.get("remove_old_select_target", True))
        remove_family_defcon_target_buttons = bool(call.data.get("remove_family_defcon_target_buttons", False))

        removed, failed = await cleanup_target_button_entity_registry(
            remove_old_select_target=remove_old_select_target,
            remove_family_defcon_target_buttons=remove_family_defcon_target_buttons,
        )

        message = f"Target button entity cleanup complete. Removed {len(removed)} entities."
        if remove_family_defcon_target_buttons:
            message += " Restart Home Assistant so dynamic target buttons are recreated."
        if failed:
            message += f" Failed to remove {len(failed)} entities."

        await log_event(message)
        fire_family_event(
            "target_button_cleanup",
            removed_count=len(removed),
            failed_count=len(failed),
            removed=removed,
            failed=failed,
            message=message,
        )

        removed_lines = "\n".join(f"- {item}" for item in removed) if removed else "None"
        failed_lines = "\n".join(f"- {item}" for item in failed) if failed else ""

        notification = message + "\n\nRemoved:\n" + removed_lines
        if failed_lines:
            notification += "\n\nFailed:\n" + failed_lines
        notification += "\n\nIf the target buttons do not appear, restart Home Assistant."

        persistent_notification.async_create(
            hass,
            notification,
            title="Family DEFCON target button cleanup",
            notification_id="family_defcon_target_button_cleanup",
        )

        await update_entities()

    # Family DEFCON automatic target button cleanup.
    # Remove old button.select_target_* registry entries from earlier pre-release builds.
    auto_removed, auto_failed = await cleanup_target_button_entity_registry(
        remove_old_select_target=True,
        remove_family_defcon_target_buttons=False,
    )
    if auto_removed or auto_failed:
        _LOGGER.info(
            "Family DEFCON automatic target button cleanup removed %s stale entities and failed %s.",
            len(auto_removed),
            len(auto_failed),
        )

    hass.services.async_register(DOMAIN, "cleanup_target_button_entities", handle_cleanup_target_button_entities, schema=CLEANUP_TARGET_BUTTON_ENTITIES_SCHEMA)
    hass.services.async_register(DOMAIN, "launch", handle_launch, schema=LAUNCH_SCHEMA)
    hass.services.async_register(DOMAIN, "launch_with_pin", handle_launch_with_pin, schema=LAUNCH_WITH_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, "clear_all", handle_clear_all)
    hass.services.async_register(DOMAIN, "stand_down", handle_stand_down)
    hass.services.async_register(DOMAIN, "set_armed", handle_set_armed, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "set_parent_targets", handle_set_parent_targets, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "enforce_now", handle_enforce_now)
    hass.services.async_register(DOMAIN, "reload_config", handle_reload_config)
    hass.services.async_register(DOMAIN, "block_person", handle_block_person, schema=PERSON_SCHEMA)
    hass.services.async_register(DOMAIN, "unblock_person", handle_unblock_person, schema=PERSON_SCHEMA)
    hass.services.async_register(DOMAIN, "dashboard_keypress", handle_dashboard_keypress, schema=DASHBOARD_KEYPRESS_SCHEMA)
    hass.services.async_register(DOMAIN, "dashboard_backspace", handle_dashboard_backspace)
    hass.services.async_register(DOMAIN, "dashboard_clear_pin", handle_dashboard_clear_pin)
    hass.services.async_register(DOMAIN, "dashboard_set_pin", handle_dashboard_set_pin, schema=DASHBOARD_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, "dashboard_select_target", handle_dashboard_select_target, schema=DASHBOARD_TARGET_SCHEMA)
    hass.services.async_register(DOMAIN, "hash_pin", handle_hash_pin, schema=HASH_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, "auth_config_status", handle_auth_config_status, schema=AUTH_SOURCE_SCHEMA)
    hass.services.async_register(DOMAIN, "config_audit_status", handle_config_audit_status, schema=CONFIG_AUDIT_SCHEMA)
    hass.services.async_register(DOMAIN, "migrate_entity_ids", handle_migrate_entity_ids)

    async def periodic(now: datetime) -> None:
        today = datetime.now().date().isoformat()
        if datetime.now().strftime("%H:%M:%S") >= conf()["daily_reset_time"] and st()["last_reset_date"] != today:
            st()["last_reset_date"] = today
            st()["mutual_destruction"] = False
            st()["daily_launches"] = 0
            st()["conflict_chain"] = 0
            st()["last_launcher"] = ""
            st()["last_target"] = ""
            for person in conf()["people"]:
                st()["blocked_until"][person] = None
            await log_event("Daily reset complete.")
        await enforce_now()
        await update_entities()
        await save_state()

    hass.data[DOMAIN]["remove_interval"] = async_track_time_interval(hass, periodic, timedelta(minutes=1))

    if not st().get("dashboard_target"):
        targets = dashboard_targets()
        st()["dashboard_target"] = targets[0] if targets else ""

    def ensure_dashboard_defaults() -> None:
        targets = dashboard_targets()
        if not st().get("dashboard_target"):
            dash = dashboard_config()
            default_target = str(dash.get("default_target", "")) if isinstance(dash, dict) else ""
            st()["dashboard_target"] = default_target if default_target in targets else (targets[0] if targets else "")
        st()["dashboard_pin"] = str(st().get("dashboard_pin", ""))
        st()["dashboard_confirm"] = bool(st().get("dashboard_confirm", False))

    ensure_dashboard_defaults()

    for platform in PLATFORMS:
        try:
            await async_load_platform(hass, platform, DOMAIN, {}, config)
        except Exception:
            _LOGGER.exception("Family DEFCON failed to load %s platform", platform)

    return True
