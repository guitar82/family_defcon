"""Family DEFCON Home Assistant custom integration."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_interval, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import loader as yaml_loader

from .const import CONFIG_PATH, DEFAULT_CONFIG, DOMAIN, PLATFORMS, SIGNAL_UPDATE, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

LAUNCH_SCHEMA = vol.Schema({vol.Required("launcher"): cv.string, vol.Required("target"): cv.string, vol.Optional("station", default=""): cv.string})
BOOL_SCHEMA = vol.Schema({vol.Required("enabled"): cv.boolean})


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _split_action(action: str) -> tuple[str, str] | None:
    if not action or "." not in action:
        return None
    domain, service = action.split(".", 1)
    return (domain, service) if domain and service else None


class FamilyDefconManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.config: dict[str, Any] = deepcopy(DEFAULT_CONFIG)
        self.state: dict[str, Any] = {}
        self._last_station_launch: dict[str, datetime] = {}
        self._unsub_daily_reset = None
        self._unsub_enforcement_tick = None

    async def async_initialize(self) -> None:
        await self.async_reload_config(record_event=False)
        stored = await self.store.async_load()
        self.state = self._default_state()
        if isinstance(stored, dict):
            self._restore_state(stored)
        self._schedule_jobs()

    def _default_state(self) -> dict[str, Any]:
        return {
            "armed": False,
            "allow_parent_targets": bool(self.config.get("allow_parent_targets_default", False)),
            "mutual_destruction": False,
            "daily_launches": 0,
            "conflict_chain": 0,
            "last_launcher": "",
            "last_target": "",
            "blocked_until": {person: None for person in self.people},
            "last_event": "System initialized.",
            "event_log": [],
        }

    def _restore_state(self, stored: dict[str, Any]) -> None:
        for key in ("armed", "allow_parent_targets", "mutual_destruction", "daily_launches", "conflict_chain", "last_launcher", "last_target", "last_event", "event_log"):
            if key in stored:
                self.state[key] = stored[key]
        stored_until = stored.get("blocked_until", {})
        if isinstance(stored_until, dict):
            self.state["blocked_until"] = {person: _parse_dt(stored_until.get(person)) for person in self.people}
        for person in self.people:
            self.state["blocked_until"].setdefault(person, None)

    async def async_save(self) -> None:
        data = deepcopy(self.state)
        data["blocked_until"] = {person: _dt_to_str(value) for person, value in self.state.get("blocked_until", {}).items()}
        await self.store.async_save(data)

    @property
    def people(self) -> list[str]:
        return list(self.config.get("people", []))

    @property
    def default_targets(self) -> list[str]:
        return list(self.config.get("default_targets", []))

    @property
    def parent_targets(self) -> list[str]:
        return list(self.config.get("parent_targets", []))

    @property
    def allowed_targets(self) -> list[str]:
        if self.state.get("allow_parent_targets"):
            return list(dict.fromkeys(self.default_targets + self.parent_targets))
        return self.default_targets

    @property
    def dns_enabled(self) -> bool:
        dns = self.config.get("dns", {})
        return bool(dns.get("enabled")) and dns.get("enforcement_mode") == "active"

    async def async_reload_config(self, record_event: bool = True) -> None:
        path = self.hass.config.path(CONFIG_PATH)
        loaded: dict[str, Any] = {}
        try:
            raw = await self.hass.async_add_executor_job(yaml_loader.load_yaml, path)
            if isinstance(raw, dict):
                loaded = raw
        except FileNotFoundError:
            _LOGGER.warning("family_defcon.yaml not found, using defaults")
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error loading family_defcon.yaml: %s", err)
        self.config = _deep_merge(DEFAULT_CONFIG, loaded)
        if self.state:
            for person in self.people:
                self.state.setdefault("blocked_until", {}).setdefault(person, None)
            for person in list(self.state.get("blocked_until", {})):
                if person not in self.people:
                    self.state["blocked_until"].pop(person, None)
            self._schedule_jobs()
            if record_event:
                await self._record_event("Config reloaded.")
                await self.async_write_update(save=True)

    def _schedule_jobs(self) -> None:
        if self._unsub_daily_reset:
            self._unsub_daily_reset()
            self._unsub_daily_reset = None
        if self._unsub_enforcement_tick:
            self._unsub_enforcement_tick()
            self._unsub_enforcement_tick = None
        reset_time = str(self.config.get("daily_reset_time", "05:00:00"))
        try:
            parts = [int(x) for x in reset_time.split(":")]
            hour, minute, second = (parts + [0, 0, 0])[:3]
        except (TypeError, ValueError):
            hour, minute, second = 5, 0, 0
        self._unsub_daily_reset = async_track_time_change(self.hass, self._async_daily_reset_callback, hour=hour, minute=minute, second=second)
        self._unsub_enforcement_tick = async_track_time_interval(self.hass, self._async_enforcement_tick, timedelta(minutes=1))

    @callback
    def _async_daily_reset_callback(self, now: datetime) -> None:
        self.hass.async_create_task(self.async_clear_all("Daily reset."))

    @callback
    def _async_enforcement_tick(self, now: datetime) -> None:
        self.hass.async_create_task(self.async_enforce_now())

    async def async_write_update(self, save: bool = False) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
        if save:
            await self.async_save()

    async def _record_event(self, message: str) -> None:
        self.state["last_event"] = message
        log = self.state.setdefault("event_log", [])
        log.insert(0, {"time": dt_util.now().isoformat(timespec="seconds"), "message": message})
        max_log = int(self.config.get("max_event_log", 25))
        del log[max_log:]

    def _resolve_station(self, station_value: str) -> tuple[str | None, dict[str, Any] | None]:
        stations = self.config.get("stations", {}) or {}
        for station_id, data in stations.items():
            if isinstance(data, dict) and (station_value == station_id or station_value == data.get("name")):
                return station_id, data
        for station_id, data in stations.items():
            if isinstance(data, str) and station_value == station_id:
                return station_id, {"name": station_id, "commander": data, "enabled": True, "key_entity": ""}
        return None, None

    def _is_key_ok(self, station_data: dict[str, Any]) -> bool:
        if not self.config.get("require_key_for_launch", False):
            return True
        key_entity = station_data.get("key_entity") or ""
        return bool(key_entity) and self.hass.states.is_state(key_entity, "on")

    def _cooldown_ok(self, station_id: str) -> bool:
        cooldown = int(self.config.get("cooldown_seconds", 30))
        if cooldown <= 0:
            return True
        now = dt_util.now()
        last = self._last_station_launch.get(station_id)
        if last is None or (now - last).total_seconds() >= cooldown:
            self._last_station_launch[station_id] = now
            return True
        return False

    def defcon_level(self) -> int:
        if self.state.get("mutual_destruction"):
            return 1
        chain = int(self.state.get("conflict_chain", 0))
        if chain >= 3:
            return 2
        if chain == 2:
            return 3
        if chain == 1:
            return 4
        return 5

    def peace_status(self) -> str:
        return {1: "Mutual WiFi Destruction", 2: "Red", 3: "Yellow", 4: "Watch", 5: "Green"}.get(self.defcon_level(), "Green")

    def minutes_remaining(self, person: str) -> int:
        until = self.state.get("blocked_until", {}).get(person)
        if not until:
            return 0
        return max(int((until - dt_util.now()).total_seconds() / 60), 0)

    def person_blocked(self, person: str) -> bool:
        if self.state.get("mutual_destruction") and person in self._mutual_destruction_people():
            return True
        return self.minutes_remaining(person) > 0

    def _mutual_destruction_people(self) -> list[str]:
        dns = self.config.get("dns", {})
        scope = dns.get("mutual_destruction_scope", "default_targets")
        if scope == "all_people":
            return self.people
        if scope == "allowed_targets":
            return self.allowed_targets
        if scope == "default_targets":
            return self.default_targets
        if isinstance(scope, list):
            return [p for p in scope if p in self.people]
        return self.default_targets

    def _add_timeout(self, person: str, minutes: int) -> None:
        now = dt_util.now()
        current_until = self.state["blocked_until"].get(person)
        base = current_until if current_until and current_until > now else now
        self.state["blocked_until"][person] = base + timedelta(minutes=minutes)

    async def async_launch(self, launcher: str, target: str, station: str) -> None:
        if not self.state.get("armed"):
            await self._record_event(f"Launch rejected from {station or 'unknown station'}. System is not armed.")
            await self.async_write_update(save=True)
            return
        if launcher not in self.people:
            await self._record_event(f"Launch rejected. Unknown launcher: {launcher}.")
            await self.async_write_update(save=True)
            return
        if target not in self.people:
            await self._record_event(f"Launch rejected. Unknown target: {target}.")
            await self.async_write_update(save=True)
            return
        if launcher == target:
            await self._record_event("Launch rejected. Self targeting is not allowed.")
            await self.async_write_update(save=True)
            return
        if target not in self.allowed_targets:
            await self._record_event(f"Launch rejected. {target} is protected.")
            await self.async_write_update(save=True)
            return
        if self.config.get("require_station_match", True):
            station_id, station_data = self._resolve_station(station)
            if not station_id or not station_data:
                await self._record_event(f"Launch rejected. Unknown station: {station}.")
                await self.async_write_update(save=True)
                return
            if not station_data.get("enabled", True):
                await self._record_event(f"Launch rejected. Station disabled: {station}.")
                await self.async_write_update(save=True)
                return
            if station_data.get("commander") != launcher:
                await self._record_event(f"Launch rejected. {station_data.get('name', station_id)} belongs to {station_data.get('commander')}, not {launcher}.")
                await self.async_write_update(save=True)
                return
            if not self._is_key_ok(station_data):
                await self._record_event(f"Launch rejected. Key not verified for {station_data.get('name', station_id)}.")
                await self.async_write_update(save=True)
                return
            if not self._cooldown_ok(station_id):
                await self._record_event(f"Launch rejected. Station cooldown active for {station_data.get('name', station_id)}.")
                await self.async_write_update(save=True)
                return
        new_launches = int(self.state.get("daily_launches", 0)) + 1
        last_launcher = self.state.get("last_launcher", "")
        last_target = self.state.get("last_target", "")
        is_retaliation = launcher == last_target and target == last_launcher
        new_chain = int(self.state.get("conflict_chain", 0)) + 1 if is_retaliation else 1
        self.state["daily_launches"] = new_launches
        self.state["conflict_chain"] = new_chain
        self.state["last_launcher"] = launcher
        self.state["last_target"] = target
        launch_limit = int(self.config.get("launches_before_mutual_destruction", 5))
        chain_limit = int(self.config.get("chain_before_mutual_destruction", 4))
        if new_launches >= launch_limit or new_chain >= chain_limit:
            self.state["mutual_destruction"] = True
            await self._record_event(f"DEFCON 1. Mutual WiFi Destruction activated by {launcher} targeting {target}.")
            await self.async_write_update(save=True)
            await self.async_enforce_now()
            return
        penalties = self.config.get("penalties", {})
        if new_chain == 1:
            minutes = int(penalties.get("first_strike_target_minutes", 30))
            self._add_timeout(target, minutes)
            await self._record_event(f"DEFCON 4. {launcher} launched at {target}. {target} receives {minutes} minute timeout.")
        elif new_chain == 2:
            launcher_minutes = int(penalties.get("retaliator_extra_minutes", 15))
            target_minutes = int(penalties.get("retaliation_target_minutes", 30))
            self._add_timeout(launcher, launcher_minutes)
            self._add_timeout(target, target_minutes)
            await self._record_event(f"DEFCON 3. Retaliation detected. {launcher} receives +{launcher_minutes} minutes. {target} receives {target_minutes} minutes.")
        elif new_chain == 3:
            launcher_minutes = int(penalties.get("reattacker_extra_minutes", 15))
            target_minutes = int(penalties.get("reattack_target_minutes", 45))
            self._add_timeout(launcher, launcher_minutes)
            self._add_timeout(target, target_minutes)
            await self._record_event(f"DEFCON 2. Escalation warning. {launcher} receives +{launcher_minutes} minutes. {target} receives {target_minutes} minutes.")
        await self.async_write_update(save=True)
        await self.async_enforce_now()

    async def async_clear_all(self, message: str = "All DEFCON timeouts cleared.") -> None:
        self.state["mutual_destruction"] = False
        self.state["daily_launches"] = 0
        self.state["conflict_chain"] = 0
        self.state["last_launcher"] = ""
        self.state["last_target"] = ""
        self.state["blocked_until"] = {person: None for person in self.people}
        await self._record_event(message)
        await self.async_write_update(save=True)
        await self.async_enforce_now()

    async def async_stand_down(self) -> None:
        self.state["conflict_chain"] = 0
        self.state["last_launcher"] = ""
        self.state["last_target"] = ""
        await self._record_event("Stand down accepted. Conflict chain reset.")
        await self.async_write_update(save=True)

    async def async_set_armed(self, enabled: bool) -> None:
        self.state["armed"] = enabled
        await self._record_event("Command system armed." if enabled else "Command system disarmed.")
        await self.async_write_update(save=True)

    async def async_set_parent_targets(self, enabled: bool) -> None:
        self.state["allow_parent_targets"] = enabled
        await self._record_event("Mom and Dad are now targetable." if enabled else "Mom and Dad are protected.")
        await self.async_write_update(save=True)

    async def async_enforce_now(self) -> None:
        if not self.dns_enabled:
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return
        custom = self.config.get("dns", {}).get("custom_services", {})
        people_cfg = custom.get("people", {}) or {}
        group_cfg = custom.get("groups", {}) or {}
        if self.state.get("mutual_destruction"):
            scope = self.config.get("dns", {}).get("mutual_destruction_scope", "default_targets")
            group_action = (group_cfg.get(scope) or {}).get("block")
            if group_action:
                await self._call_configured_action(group_action)
        else:
            for group in group_cfg.values():
                unblock = group.get("unblock") if isinstance(group, dict) else None
                if unblock:
                    await self._call_configured_action(unblock)
        for person in self.people:
            cfg = people_cfg.get(person, {})
            if not isinstance(cfg, dict):
                continue
            action = cfg.get("block") if self.person_blocked(person) else cfg.get("unblock")
            if action:
                await self._call_configured_action(action)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    async def _call_configured_action(self, action_cfg: dict[str, Any]) -> None:
        if not isinstance(action_cfg, dict):
            return
        action = action_cfg.get("action") or action_cfg.get("service")
        split = _split_action(action)
        if not split:
            _LOGGER.warning("Invalid action in family_defcon.yaml: %s", action_cfg)
            return
        domain, service = split
        service_data = deepcopy(action_cfg.get("data", {})) or {}
        target = deepcopy(action_cfg.get("target", {})) or {}
        service_data.update(target)
        try:
            await self.hass.services.async_call(domain, service, service_data, blocking=False)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed calling configured action %s: %s", action, err)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    manager = FamilyDefconManager(hass)
    hass.data[DOMAIN] = manager
    await manager.async_initialize()

    async def handle_launch(call: ServiceCall) -> None:
        await manager.async_launch(call.data["launcher"], call.data["target"], call.data.get("station", ""))
    async def handle_clear_all(call: ServiceCall) -> None:
        await manager.async_clear_all()
    async def handle_stand_down(call: ServiceCall) -> None:
        await manager.async_stand_down()
    async def handle_set_armed(call: ServiceCall) -> None:
        await manager.async_set_armed(call.data["enabled"])
    async def handle_set_parent_targets(call: ServiceCall) -> None:
        await manager.async_set_parent_targets(call.data["enabled"])
    async def handle_enforce_now(call: ServiceCall) -> None:
        await manager.async_enforce_now()
    async def handle_reload_config(call: ServiceCall) -> None:
        await manager.async_reload_config()

    hass.services.async_register(DOMAIN, "launch", handle_launch, schema=LAUNCH_SCHEMA)
    hass.services.async_register(DOMAIN, "clear_all", handle_clear_all)
    hass.services.async_register(DOMAIN, "stand_down", handle_stand_down)
    hass.services.async_register(DOMAIN, "set_armed", handle_set_armed, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "set_parent_targets", handle_set_parent_targets, schema=BOOL_SCHEMA)
    hass.services.async_register(DOMAIN, "enforce_now", handle_enforce_now)
    hass.services.async_register(DOMAIN, "reload_config", handle_reload_config)

    for platform in PLATFORMS:
        await async_load_platform(hass, platform, DOMAIN, {}, config)
    return True
