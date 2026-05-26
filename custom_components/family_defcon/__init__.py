"""Family DEFCON custom integration with PIN mode."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    def load_config() -> dict:
        path = Path(hass.config.path(CONFIG_PATH))
        if not path.exists():
            _LOGGER.warning("Family DEFCON config file not found at %s. Using defaults.", path)
            return {}
        try:
            loaded = yaml.safe_load(path.read_text()) or {}
            return loaded if isinstance(loaded, dict) else {}
        except Exception as err:
            _LOGGER.error("Unable to load Family DEFCON config: %s", err)
            return {}

    def normalize_config(raw: dict) -> dict:
        people = list(raw.get("people", DEFAULT_PEOPLE))
        default_targets = list(raw.get("default_targets", DEFAULT_TARGETS))
        parent_targets = list(raw.get("parent_targets", DEFAULT_PARENTS))
        penalties = raw.get("penalties", {}) if isinstance(raw.get("penalties", {}), dict) else {}
        auth = raw.get("auth", {}) if isinstance(raw.get("auth", {}), dict) else {}
        dns = raw.get("dns", {}) if isinstance(raw.get("dns", {}), dict) else {}
        users = auth.get("users", {}) if isinstance(auth.get("users", {}), dict) else {}
        stations_in = raw.get("stations", {}) if isinstance(raw.get("stations", {}), dict) else {}

        stations = {}
        for station_id, station_data in stations_in.items():
            if isinstance(station_data, dict):
                stations[str(station_id)] = {
                    "name": station_data.get("name", str(station_id)),
                    "commander": station_data.get("commander", ""),
                    "enabled": bool(station_data.get("enabled", True)),
                    "key_entity": station_data.get("key_entity", ""),
                }
            else:
                stations[str(station_id)] = {
                    "name": str(station_data),
                    "commander": "",
                    "enabled": True,
                    "key_entity": "",
                }

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
            "dns": dns,
        }

    hass.data[DOMAIN]["config"] = normalize_config(load_config())
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
        data = dict(st())
        data["blocked_until"] = {
            person: value.isoformat() if isinstance(value, datetime) else None
            for person, value in st()["blocked_until"].items()
        }
        await store.async_save(data)

    async def update_entities() -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

    async def log_event(message: str) -> None:
        st()["last_event"] = message
        log = st().setdefault("event_log", [])
        log.insert(0, {"time": datetime.now().isoformat(timespec="seconds"), "message": message})
        del log[conf()["max_event_log"]:]
        await save_state()
        await update_entities()

    def targets() -> list[str]:
        if st()["allow_parent_targets"]:
            return list(dict.fromkeys(conf()["default_targets"] + conf()["parent_targets"]))
        return conf()["default_targets"]

    def is_blocked(person: str) -> bool:
        if st()["mutual_destruction"] and person in conf()["default_targets"]:
            return True
        until = st()["blocked_until"].get(person)
        return isinstance(until, datetime) and until > datetime.now()

    async def call_action(action_def: dict[str, Any] | None) -> None:
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
        dns = conf().get("dns", {})
        if not dns.get("enabled") or dns.get("enforcement_mode") != "active":
            return
        custom = dns.get("custom_services", {})
        people_actions = custom.get("people", {})
        groups = custom.get("groups", {})
        if st()["mutual_destruction"]:
            scope = dns.get("mutual_destruction_scope", "default_targets")
            group_action = groups.get(scope, {}).get("block")
            if group_action:
                await call_action(group_action)
                return
        for person in conf()["people"]:
            actions = people_actions.get(person, {})
            await call_action(actions.get("block") if is_blocked(person) else actions.get("unblock"))

    def station_record(station: str):
        stations = conf()["stations"]
        if station in stations:
            return station, stations[station]
        for sid, record in stations.items():
            if record.get("name") == station:
                return sid, record
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
        if target not in targets():
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
        retaliation = launcher == st()["last_target"] and target == st()["last_launcher"]
        new_chain = st()["conflict_chain"] + 1 if retaliation else 1

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
        await log_event("Mom and Dad are targetable." if call.data["enabled"] else "Mom and Dad are protected.")

    async def handle_enforce_now(call: ServiceCall) -> None:
        await enforce_now()
        await log_event("Enforcement reapplied.")

    async def handle_reload_config(call: ServiceCall) -> None:
        hass.data[DOMAIN]["config"] = normalize_config(load_config())
        await log_event("Config reloaded.")

    hass.services.async_register(DOMAIN, "launch", handle_launch, schema=LAUNCH_SCHEMA)
    hass.services.async_register(DOMAIN, "launch_with_pin", handle_launch_with_pin, schema=LAUNCH_WITH_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, "clear_all", handle_clear_all)
    hass.services.async_register(DOMAIN, "stand_down", handle_stand_down)
    hass.services.async_register(DOMAIN, "set_armed", handle_set_armed, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "set_parent_targets", handle_set_parent_targets, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "enforce_now", handle_enforce_now)
    hass.services.async_register(DOMAIN, "reload_config", handle_reload_config)

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

    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)
    hass.helpers.discovery.load_platform("switch", DOMAIN, {}, config)
    hass.helpers.discovery.load_platform("binary_sensor", DOMAIN, {}, config)

    return True
