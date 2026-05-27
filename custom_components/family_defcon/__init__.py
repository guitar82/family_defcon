"""Family DEFCON custom integration.

v1.4 keeps variable data in family_defcon.yaml, uses async-safe file loading, and manages AdGuard custom rules safely:
people, targets, PINs, stations, AdGuard URL, client names, penalties, timers, and DNS behavior.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
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



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Family DEFCON from a UI config entry."""
    config_file = entry.data.get("config_file", CONFIG_PATH)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config_path"] = config_file

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

    raw = await load_yaml(hass.data.get(DOMAIN, {}).get("config_path", CONFIG_PATH))
    if not raw:
        _LOGGER.warning("Family DEFCON config missing or empty at %s.", hass.config.path(CONFIG_PATH))
    hass.data[DOMAIN]["config"] = normalize_config(raw)
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
        "dashboard_pin": "",
        "dashboard_target": str(stored.get("dashboard_target", "")),
        "dashboard_confirm": bool(stored.get("dashboard_confirm", False)),
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
        payload["blocked_until"] = {
            person: value.isoformat() if isinstance(value, datetime) else None
            for person, value in st()["blocked_until"].items()
        }
        await store.async_save(payload)

    async def update_entities() -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

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
        if st()["mutual_destruction"] and person in conf()["default_targets"]:
            return True
        until = st()["blocked_until"].get(person)
        return isinstance(until, datetime) and until > datetime.now()

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
                        return False, None
                    try:
                        return True, await resp.json()
                    except Exception:
                        return True, text

            async with session.post(f"{base_url}{path}", json=payload or {}, auth=auth, timeout=10) as resp:
                text = await resp.text()
                if resp.status not in (200, 204):
                    _LOGGER.warning("Family DEFCON AdGuard POST failed: %s %s %s", path, resp.status, text)
                    return False, None
                try:
                    return True, await resp.json()
                except Exception:
                    return True, text
        except Exception as err:
            _LOGGER.error("Family DEFCON AdGuard call error: %s %s", path, err)
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
            return

        if isinstance(existing, dict):
            raw_rules = existing.get("user_rules", existing.get("rules"))
            if raw_rules is None:
                _LOGGER.error(
                    "Family DEFCON AdGuard status response did not include user_rules or rules. "
                    "Refusing to overwrite custom filtering rules. Keys returned: %s",
                    list(existing.keys()),
                )
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

    def station_record(station: str):
        stations = conf()["stations"]
        if station in stations:
            return station, stations[station]
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

    async def apply_launch(launcher: str, target: str, station: str) -> None:
        if not st()["armed"]:
            await log_event("Launch rejected. Command system is not armed.")
            return
        if launcher not in conf()["people"]:
            await log_event(f"Launch rejected. Unknown launcher {launcher}.")
            return
        if target not in valid_targets():
            await log_event(f"Launch rejected. {target} is protected.")
            return
        if launcher == target:
            await log_event("Launch rejected. Self targeting is not allowed.")
            return

        ok, reason = await validate_station(launcher, station)
        if not ok:
            await log_event(reason)
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
            await log_event(f"DEFCON 1. Mutual WiFi Destruction activated by {launcher} targeting {target}.")
            await enforce_now()
            return

        if new_chain == 1:
            await add_timeout(target, p["first_strike_target_minutes"])
            await log_event(f"DEFCON 4. {launcher} launched at {target}. {target} receives {p['first_strike_target_minutes']} minute timeout.")
        elif new_chain == 2:
            await add_timeout(launcher, p["retaliator_extra_minutes"])
            await add_timeout(target, p["retaliation_target_minutes"])
            await log_event(f"DEFCON 3. Retaliation detected. {launcher} receives +{p['retaliator_extra_minutes']} minutes. {target} receives {p['retaliation_target_minutes']} minutes.")
        elif new_chain == 3:
            await add_timeout(launcher, p["reattacker_extra_minutes"])
            await add_timeout(target, p["reattack_target_minutes"])
            await log_event(f"DEFCON 2. Escalation warning. {launcher} receives +{p['reattacker_extra_minutes']} minutes. {target} receives {p['reattack_target_minutes']} minutes. Next retaliation triggers mutual destruction.")

        await enforce_now()

    async def handle_launch(call: ServiceCall) -> None:
        await apply_launch(call.data["launcher"], call.data["target"], call.data.get("station", ""))

    async def handle_launch_with_pin(call: ServiceCall) -> None:
        station = call.data.get("station", "")
        locked_raw = st()["pin_locked_until"].get(station)
        if locked_raw:
            try:
                locked_until = datetime.fromisoformat(locked_raw)
                if locked_until > datetime.now():
                    await log_event(f"PIN entry locked at {station} until {locked_until.strftime('%H:%M:%S')}.")
                    return
            except Exception:
                pass

        launcher = None
        for person, data in conf()["auth"]["users"].items():
            if str(data.get("pin", "")) == str(call.data["pin"]):
                launcher = person
                break

        if not launcher:
            attempts = int(st()["pin_bad_attempts"].get(station, 0)) + 1
            st()["pin_bad_attempts"][station] = attempts
            if attempts >= conf()["auth"]["max_bad_pin_attempts"]:
                until = datetime.now() + timedelta(seconds=conf()["auth"]["lockout_seconds_after_bad_pins"])
                st()["pin_locked_until"][station] = until.isoformat()
                st()["pin_bad_attempts"][station] = 0
                await log_event(f"Too many bad PIN attempts at {station}. Terminal locked temporarily.")
            else:
                await log_event(f"Bad PIN attempt at {station}.")
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
        hass.data[DOMAIN]["config"] = normalize_config(await load_yaml(hass.data.get(DOMAIN, {}).get("config_path", CONFIG_PATH)))
        targets = dashboard_targets()
        if st().get("dashboard_target") not in targets:
            dash = dashboard_config()
            default_target = str(dash.get("default_target", "")) if isinstance(dash, dict) else ""
            st()["dashboard_target"] = default_target if default_target in targets else (targets[0] if targets else "")
        await log_event("Config reloaded.")

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

    async def handle_dashboard_keypress(call: ServiceCall) -> None:
        digit = str(call.data["digit"])
        if digit not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            return
        current = str(st().get("dashboard_pin", ""))
        st()["dashboard_pin"] = (current + digit)[-12:]
        await update_entities()

    async def handle_dashboard_backspace(call: ServiceCall) -> None:
        current = str(st().get("dashboard_pin", ""))
        st()["dashboard_pin"] = current[:-1]
        await update_entities()

    async def handle_dashboard_clear_pin(call: ServiceCall) -> None:
        st()["dashboard_pin"] = ""
        await update_entities()

    async def handle_dashboard_set_pin(call: ServiceCall) -> None:
        pin = str(call.data["pin"])
        st()["dashboard_pin"] = pin[-12:]
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
        launcher = None
        for person, data in conf()["auth"]["users"].items():
            if str(data.get("pin", "")) == str(pin):
                launcher = person
                break

        if not launcher:
            await log_event(f"Bad PIN attempt at {station}.")
            return

        await apply_launch(launcher, target, station)

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
