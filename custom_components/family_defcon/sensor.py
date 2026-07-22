"""Sensors for Family DEFCON."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE
from .entity import async_add_entry_entities


def _entity_slug(name: str) -> str:
    """Build the entity slug used by generated person sensors."""
    slug = re.sub(r"[^a-z0-9_]+", "_", str(name).strip().lower())
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Family DEFCON sensors from a config entry."""
    entities = [
        DefconLevelSensor(hass),
        PeaceStatusSensor(hass),
        DailyLaunchesSensor(hass),
        ConflictChainSensor(hass),
        LastLauncherSensor(hass),
        LastTargetSensor(hass),
        LastEventSensor(hass),
        DashboardPeopleSensor(hass),
        ParentAdminConfirmedBySensor(hass),
        ParentAdminStatusSensor(hass),
        AdGuardStatusSensor(hass),
        AdGuardLastSyncSensor(hass),
        AdGuardLastErrorSensor(hass),
        AdGuardManagedRuleCountSensor(hass),
    ]

    for person in hass.data[DOMAIN]["config"].get("people", []):
        entities.append(PersonWifiStatusSensor(hass, person))
        entities.append(PersonMinutesRemainingSensor(hass, person))

    async_add_entry_entities(entry, async_add_entities, entities)


class Base(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def s(self) -> dict[str, Any]:
        return self.hass.data[DOMAIN]["state"]

    @property
    def c(self) -> dict[str, Any]:
        return self.hass.data[DOMAIN]["config"]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )

    def _canonical_person_name(self, person: str) -> str:
        person_text = str(person).strip().lower()
        for configured in self.c.get("people", []):
            if str(configured).strip().lower() == person_text:
                return str(configured)
        return str(person).strip()

    def _list_contains_person(self, values: list, person: str) -> bool:
        person_text = str(person).strip().lower()
        return any(str(value).strip().lower() == person_text for value in values or [])

    def _blocked_until_for_person(self, person: str):
        person_text = str(person).strip().lower()
        blocked_until = self.s.get("blocked_until", {})
        if not isinstance(blocked_until, dict):
            return None

        for key, value in blocked_until.items():
            if str(key).strip().lower() == person_text:
                return value

        return None

    def _mutual_blocks_person(self, person: str) -> bool:
        if not self.s.get("mutual_destruction", False):
            return False

        scope = str(self.c.get("dns", {}).get("mutual_destruction_scope", "default_targets")).lower()
        if scope in ("all", "everyone", "people", "all_people"):
            return self._list_contains_person(self.c.get("people", []), person)

        return self._list_contains_person(self.c.get("default_targets", []), person)

    def _person_snapshot(self, person: str) -> tuple[str, bool, int]:
        canonical = self._canonical_person_name(person)

        if self._mutual_blocks_person(canonical):
            return "blocked", True, 999

        until = self._blocked_until_for_person(canonical)
        if isinstance(until, datetime) and until > datetime.now():
            minutes = max(int((until - datetime.now()).total_seconds() / 60), 0)
            return "blocked", True, minutes

        return "allowed", False, 0


class DefconLevelSensor(Base):
    _attr_name = "Level"
    _attr_unique_id = "family_defcon_level"
    _attr_suggested_object_id = "family_defcon_level"

    @property
    def native_value(self):
        if self.s.get("mutual_destruction", False):
            return 1

        daily_launches = int(self.s.get("daily_launches", 0))
        conflict_chain = int(self.s.get("conflict_chain", 0))
        launch_limit = int(self.c.get("launches_before_mutual_destruction", 5))
        chain_limit = int(self.c.get("chain_before_mutual_destruction", 4))
        active_block_count = sum(1 for person in self.c.get("people", []) if self._person_snapshot(person)[1])

        if (launch_limit > 1 and daily_launches >= launch_limit - 1) or (chain_limit > 1 and conflict_chain >= chain_limit - 1):
            return 2

        if conflict_chain >= 2 or active_block_count >= 2:
            return 3

        if active_block_count >= 1 or conflict_chain >= 1:
            return 4

        return 5


class PeaceStatusSensor(Base):
    _attr_name = "Peace Status"
    _attr_unique_id = "family_defcon_peace_status"
    _attr_suggested_object_id = "family_defcon_peace_status"

    @property
    def native_value(self):
        return {1: "Mutual WiFi Destruction", 2: "Red", 3: "Yellow", 4: "Watch", 5: "Green"}.get(
            DefconLevelSensor(self.hass).native_value,
            "Unknown",
        )


class DailyLaunchesSensor(Base):
    _attr_name = "Daily Launches"
    _attr_unique_id = "family_defcon_daily_launches"
    _attr_suggested_object_id = "family_defcon_daily_launches"

    @property
    def native_value(self):
        return int(self.s.get("daily_launches", 0))


class ConflictChainSensor(Base):
    _attr_name = "Conflict Chain"
    _attr_unique_id = "family_defcon_conflict_chain"
    _attr_suggested_object_id = "family_defcon_conflict_chain"

    @property
    def native_value(self):
        return int(self.s.get("conflict_chain", 0))


class LastLauncherSensor(Base):
    _attr_name = "Last Launcher"
    _attr_unique_id = "family_defcon_last_launcher"
    _attr_suggested_object_id = "family_defcon_last_launcher"

    @property
    def native_value(self):
        return self.s.get("last_launcher", "")


class LastTargetSensor(Base):
    _attr_name = "Last Target"
    _attr_unique_id = "family_defcon_last_target"
    _attr_suggested_object_id = "family_defcon_last_target"

    @property
    def native_value(self):
        return self.s.get("last_target", "")


class LastEventSensor(Base):
    _attr_name = "Last Event"
    _attr_unique_id = "family_defcon_last_event"
    _attr_suggested_object_id = "family_defcon_last_event"

    @property
    def native_value(self):
        return self.s.get("last_event", "System initialized.")

    @property
    def extra_state_attributes(self):
        return {"event_log": self.s.get("event_log", [])}


class AdGuardStatusSensor(Base):
    _attr_name = "AdGuard Status"
    _attr_unique_id = "family_defcon_adguard_status"
    _attr_suggested_object_id = "family_defcon_adguard_status"

    @property
    def native_value(self):
        return self.s.get("adguard_last_status", "unknown")

    @property
    def extra_state_attributes(self):
        return {
            "last_sync": self.s.get("adguard_last_sync", ""),
            "last_error": self.s.get("adguard_last_error", ""),
            "managed_rule_count": self.s.get("adguard_managed_rule_count", 0),
        }


class AdGuardLastSyncSensor(Base):
    _attr_name = "AdGuard Last Sync"
    _attr_unique_id = "family_defcon_adguard_last_sync"
    _attr_suggested_object_id = "family_defcon_adguard_last_sync"

    @property
    def native_value(self):
        return self.s.get("adguard_last_sync", "")


class AdGuardLastErrorSensor(Base):
    _attr_name = "AdGuard Last Error"
    _attr_unique_id = "family_defcon_adguard_last_error"
    _attr_suggested_object_id = "family_defcon_adguard_last_error"

    @property
    def native_value(self):
        return self.s.get("adguard_last_error", "")


class AdGuardManagedRuleCountSensor(Base):
    _attr_name = "AdGuard Managed Rule Count"
    _attr_unique_id = "family_defcon_adguard_managed_rule_count"
    _attr_suggested_object_id = "family_defcon_adguard_managed_rule_count"

    @property
    def native_value(self):
        return int(self.s.get("adguard_managed_rule_count", 0))


class DashboardPeopleSensor(Base):
    _attr_name = "Dashboard People"
    _attr_unique_id = "family_defcon_dashboard_people"
    _attr_suggested_object_id = "family_defcon_dashboard_people"

    @property
    def native_value(self):
        return len(self.c.get("people", []))

    @property
    def extra_state_attributes(self):
        people = []
        blocked_keys = sorted(str(key) for key in self.s.get("blocked_until", {}).keys())

        for raw_person in self.c.get("people", []):
            person = self._canonical_person_name(str(raw_person))
            slug = _entity_slug(person)
            status, blocked, minutes = self._person_snapshot(person)

            people.append({
                "name": person,
                "slug": slug,
                "status": status,
                "blocked": blocked,
                "minutes_remaining": minutes,
                "status_entity": f"sensor.family_defcon_{slug}_wifi_status",
                "minutes_entity": f"sensor.family_defcon_{slug}_wifi_minutes_remaining",
                "is_default_target": self._list_contains_person(self.c.get("default_targets", []), person),
                "is_parent_target": self._list_contains_person(self.c.get("parent_targets", []), person),
            })

        return {
            "people": people,
            "blocked_until_keys": blocked_keys,
            "active_block_count": sum(1 for item in people if item["blocked"]),
        }


class PersonWifiStatusSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass)
        self.person = str(person)
        slug = _entity_slug(person)
        self._attr_name = f"{person} WiFi Status"
        self._attr_unique_id = f"family_defcon_{slug}_wifi_status"
        self._attr_suggested_object_id = f"family_defcon_{slug}_wifi_status"

    @property
    def native_value(self):
        return self._person_snapshot(self.person)[0]

    @property
    def extra_state_attributes(self):
        status, blocked, minutes = self._person_snapshot(self.person)
        return {
            "blocked": blocked,
            "minutes_remaining": minutes,
            "status": status,
            "blocked_until_keys": sorted(str(key) for key in self.s.get("blocked_until", {}).keys()),
        }


class PersonMinutesRemainingSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass)
        self.person = str(person)
        slug = _entity_slug(person)
        self._attr_name = f"{person} WiFi Minutes Remaining"
        self._attr_unique_id = f"family_defcon_{slug}_wifi_minutes_remaining"
        self._attr_suggested_object_id = f"family_defcon_{slug}_wifi_minutes_remaining"
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self):
        return self._person_snapshot(self.person)[2]

    @property
    def extra_state_attributes(self):
        status, blocked, minutes = self._person_snapshot(self.person)
        return {
            "blocked": blocked,
            "minutes_remaining": minutes,
            "status": status,
        }


class ParentAdminConfirmedBySensor(Base):
    _attr_name = "parent_admin_confirmed_by"
    _attr_unique_id = "family_defcon_parent_admin_confirmed_by"
    _attr_suggested_object_id = "parent_admin_confirmed_by"
    _attr_icon = "mdi:account-shield"

    @property
    def native_value(self):
        expires = self.s.get("parent_admin_confirm_expires")
        if bool(self.s.get("parent_admin_confirm")) and isinstance(expires, datetime) and expires > datetime.now():
            return str(self.s.get("parent_admin_confirmed_by", "") or "Unknown")
        return "None"


class ParentAdminStatusSensor(Base):
    _attr_name = "parent_admin_status"
    _attr_unique_id = "family_defcon_parent_admin_status"
    _attr_suggested_object_id = "parent_admin_status"
    _attr_icon = "mdi:shield-account"

    @property
    def native_value(self):
        expires = self.s.get("parent_admin_confirm_expires")
        if bool(self.s.get("parent_admin_confirm")) and isinstance(expires, datetime) and expires > datetime.now():
            return "confirmed"
        return "not_confirmed"

    @property
    def extra_state_attributes(self):
        expires = self.s.get("parent_admin_confirm_expires")
        return {
            "confirmed_by": self.s.get("parent_admin_confirmed_by", ""),
            "expires": expires.isoformat() if isinstance(expires, datetime) else None,
        }
