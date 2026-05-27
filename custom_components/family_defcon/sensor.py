"""Sensors for Family DEFCON."""
from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, SIGNAL_UPDATE

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    entities = [
        DefconLevelSensor(hass),
        PeaceStatusSensor(hass),
        DailyLaunchesSensor(hass),
        ConflictChainSensor(hass),
        LastLauncherSensor(hass),
        LastTargetSensor(hass),
        LastEventSensor(hass),
        DashboardPeopleSensor(hass),
        AdGuardStatusSensor(hass),
        AdGuardLastSyncSensor(hass),
        AdGuardLastErrorSensor(hass),
        AdGuardManagedRuleCountSensor(hass),
    ]
    for person in hass.data[DOMAIN]["config"]["people"]:
        entities.append(PersonWifiStatusSensor(hass, person))
        entities.append(PersonMinutesRemainingSensor(hass, person))
    async_add_entities(entities)

class Base(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, hass): self.hass = hass
    @property
    def s(self): return self.hass.data[DOMAIN]["state"]
    @property
    def c(self): return self.hass.data[DOMAIN]["config"]
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))

class DefconLevelSensor(Base):
    _attr_name = "Level"; _attr_unique_id = "family_defcon_level"; _attr_suggested_object_id = "family_defcon_level"

    def _is_person_blocked(self, person: str) -> bool:
        if self.s["mutual_destruction"]:
            scope = str(self.c.get("dns", {}).get("mutual_destruction_scope", "default_targets")).lower()
            if scope in ("all", "everyone", "people", "all_people"):
                return person in self.c["people"]
            return person in self.c["default_targets"]
        until = self.s["blocked_until"].get(person)
        return isinstance(until, datetime) and until > datetime.now()

    @property
    def native_value(self):
        # DEFCON is calculated from the worst active condition, not only the latest launch.
        # This prevents downgrades such as DEFCON 3 back to DEFCON 4 while multiple people are still blocked.
        if self.s["mutual_destruction"]:
            return 1

        daily_launches = int(self.s.get("daily_launches", 0))
        conflict_chain = int(self.s.get("conflict_chain", 0))
        launch_limit = int(self.c.get("launches_before_mutual_destruction", 5))
        chain_limit = int(self.c.get("chain_before_mutual_destruction", 4))
        active_block_count = sum(1 for person in self.c["people"] if self._is_person_blocked(person))

        # DEFCON 2 is the warning state immediately before Mutual WiFi Destruction.
        if (launch_limit > 1 and daily_launches >= launch_limit - 1) or (chain_limit > 1 and conflict_chain >= chain_limit - 1):
            return 2

        # DEFCON 3 means active conflict, retaliation, or multiple people currently blocked.
        if conflict_chain >= 2 or active_block_count >= 2:
            return 3

        # DEFCON 4 means a single active timeout or first strike condition.
        if active_block_count >= 1 or conflict_chain >= 1:
            return 4

        return 5

class PeaceStatusSensor(Base):
    _attr_name = "Peace Status"; _attr_unique_id = "family_defcon_peace_status"; _attr_suggested_object_id = "family_defcon_peace_status"
    @property
    def native_value(self): return {1:"Mutual WiFi Destruction",2:"Red",3:"Yellow",4:"Watch",5:"Green"}.get(DefconLevelSensor(self.hass).native_value, "Unknown")

class DailyLaunchesSensor(Base):
    _attr_name = "Daily Launches"; _attr_unique_id = "family_defcon_daily_launches"; _attr_suggested_object_id = "family_defcon_daily_launches"
    @property
    def native_value(self): return int(self.s["daily_launches"])

class ConflictChainSensor(Base):
    _attr_name = "Conflict Chain"; _attr_unique_id = "family_defcon_conflict_chain"; _attr_suggested_object_id = "family_defcon_conflict_chain"
    @property
    def native_value(self): return int(self.s["conflict_chain"])

class LastLauncherSensor(Base):
    _attr_name = "Last Launcher"; _attr_unique_id = "family_defcon_last_launcher"; _attr_suggested_object_id = "family_defcon_last_launcher"
    @property
    def native_value(self): return self.s["last_launcher"]

class LastTargetSensor(Base):
    _attr_name = "Last Target"; _attr_unique_id = "family_defcon_last_target"; _attr_suggested_object_id = "family_defcon_last_target"
    @property
    def native_value(self): return self.s["last_target"]

class LastEventSensor(Base):
    _attr_name = "Last Event"; _attr_unique_id = "family_defcon_last_event"; _attr_suggested_object_id = "family_defcon_last_event"
    @property
    def native_value(self): return self.s["last_event"]
    @property
    def extra_state_attributes(self): return {"event_log": self.s.get("event_log", [])}


def _entity_slug(name: str) -> str:
    """Build the entity slug used by the generated person sensors."""
    import re
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower())
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")




class AdGuardStatusSensor(Base):
    _attr_name = "AdGuard Status"; _attr_unique_id = "family_defcon_adguard_status"; _attr_suggested_object_id = "family_defcon_adguard_status"
    @property
    def native_value(self): return self.s.get("adguard_last_status", "unknown")
    @property
    def extra_state_attributes(self):
        return {
            "last_sync": self.s.get("adguard_last_sync", ""),
            "last_error": self.s.get("adguard_last_error", ""),
            "managed_rule_count": self.s.get("adguard_managed_rule_count", 0),
        }

class AdGuardLastSyncSensor(Base):
    _attr_name = "AdGuard Last Sync"; _attr_unique_id = "family_defcon_adguard_last_sync"; _attr_suggested_object_id = "family_defcon_adguard_last_sync"
    @property
    def native_value(self): return self.s.get("adguard_last_sync", "")

class AdGuardLastErrorSensor(Base):
    _attr_name = "AdGuard Last Error"; _attr_unique_id = "family_defcon_adguard_last_error"; _attr_suggested_object_id = "family_defcon_adguard_last_error"
    @property
    def native_value(self): return self.s.get("adguard_last_error", "")

class AdGuardManagedRuleCountSensor(Base):
    _attr_name = "AdGuard Managed Rule Count"; _attr_unique_id = "family_defcon_adguard_managed_rule_count"; _attr_suggested_object_id = "family_defcon_adguard_managed_rule_count"
    @property
    def native_value(self): return int(self.s.get("adguard_managed_rule_count", 0))


class DashboardPeopleSensor(Base):
    _attr_name = "Dashboard People"
    _attr_unique_id = "family_defcon_dashboard_people"
    _attr_suggested_object_id = "family_defcon_dashboard_people"

    @property
    def native_value(self):
        return len(self.c["people"])

    @property
    def extra_state_attributes(self):
        people = []
        for person in self.c["people"]:
            slug = _entity_slug(person)
            people.append({
                "name": person,
                "status_entity": f"sensor.family_defcon_{slug}_wifi_status",
                "minutes_entity": f"sensor.family_defcon_{slug}_wifi_minutes_remaining",
                "is_default_target": person in self.c.get("default_targets", []),
                "is_parent_target": person in self.c.get("parent_targets", []),
            })
        return {"people": people}


class PersonWifiStatusSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass); self.person = person
        slug = _entity_slug(person)
        self._attr_name = f"{person} WiFi Status"; self._attr_unique_id = f"family_defcon_{slug}_wifi_status"; self._attr_suggested_object_id = f"family_defcon_{slug}_wifi_status"
    def _mutual_blocks_person(self) -> bool:
        if not self.s["mutual_destruction"]:
            return False
        scope = str(self.c.get("dns", {}).get("mutual_destruction_scope", "default_targets")).lower()
        if scope in ("all", "everyone", "people", "all_people"):
            return self.person in self.c["people"]
        return self.person in self.c["default_targets"]

    @property
    def native_value(self):
        if self._mutual_blocks_person(): return "blocked"
        until = self.s["blocked_until"].get(self.person)
        return "blocked" if isinstance(until, datetime) and until > datetime.now() else "allowed"

class PersonMinutesRemainingSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass); self.person = person
        slug = _entity_slug(person)
        self._attr_name = f"{person} WiFi Minutes Remaining"; self._attr_unique_id = f"family_defcon_{slug}_wifi_minutes_remaining"; self._attr_suggested_object_id = f"family_defcon_{slug}_wifi_minutes_remaining"; self._attr_native_unit_of_measurement = "min"
    def _mutual_blocks_person(self) -> bool:
        if not self.s["mutual_destruction"]:
            return False
        scope = str(self.c.get("dns", {}).get("mutual_destruction_scope", "default_targets")).lower()
        if scope in ("all", "everyone", "people", "all_people"):
            return self.person in self.c["people"]
        return self.person in self.c["default_targets"]

    @property
    def native_value(self):
        if self._mutual_blocks_person(): return 999
        until = self.s["blocked_until"].get(self.person)
        return max(int((until - datetime.now()).total_seconds() / 60), 0) if isinstance(until, datetime) else 0
