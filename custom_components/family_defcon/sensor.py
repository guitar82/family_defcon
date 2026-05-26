"""Sensors for Family DEFCON."""
from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, SIGNAL_UPDATE

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    entities = [DefconLevelSensor(hass), PeaceStatusSensor(hass), DailyLaunchesSensor(hass), ConflictChainSensor(hass), LastLauncherSensor(hass), LastTargetSensor(hass), LastEventSensor(hass)]
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
    _attr_name = "Level"; _attr_unique_id = "family_defcon_level"
    @property
    def native_value(self):
        if self.s["mutual_destruction"]: return 1
        chain = int(self.s["conflict_chain"])
        return 2 if chain >= 3 else 3 if chain == 2 else 4 if chain == 1 else 5

class PeaceStatusSensor(Base):
    _attr_name = "Peace Status"; _attr_unique_id = "family_defcon_peace_status"
    @property
    def native_value(self): return {1:"Mutual WiFi Destruction",2:"Red",3:"Yellow",4:"Watch",5:"Green"}.get(DefconLevelSensor(self.hass).native_value, "Unknown")

class DailyLaunchesSensor(Base):
    _attr_name = "Daily Launches"; _attr_unique_id = "family_defcon_daily_launches"
    @property
    def native_value(self): return int(self.s["daily_launches"])

class ConflictChainSensor(Base):
    _attr_name = "Conflict Chain"; _attr_unique_id = "family_defcon_conflict_chain"
    @property
    def native_value(self): return int(self.s["conflict_chain"])

class LastLauncherSensor(Base):
    _attr_name = "Last Launcher"; _attr_unique_id = "family_defcon_last_launcher"
    @property
    def native_value(self): return self.s["last_launcher"]

class LastTargetSensor(Base):
    _attr_name = "Last Target"; _attr_unique_id = "family_defcon_last_target"
    @property
    def native_value(self): return self.s["last_target"]

class LastEventSensor(Base):
    _attr_name = "Last Event"; _attr_unique_id = "family_defcon_last_event"
    @property
    def native_value(self): return self.s["last_event"]
    @property
    def extra_state_attributes(self): return {"event_log": self.s.get("event_log", [])}

class PersonWifiStatusSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass); self.person = person
        self._attr_name = f"{person} WiFi Status"; self._attr_unique_id = f"family_defcon_{person.lower()}_wifi_status"
    @property
    def native_value(self):
        if self.s["mutual_destruction"] and self.person in self.c["default_targets"]: return "blocked"
        until = self.s["blocked_until"].get(self.person)
        return "blocked" if isinstance(until, datetime) and until > datetime.now() else "allowed"

class PersonMinutesRemainingSensor(Base):
    def __init__(self, hass, person):
        super().__init__(hass); self.person = person
        self._attr_name = f"{person} WiFi Minutes Remaining"; self._attr_unique_id = f"family_defcon_{person.lower()}_wifi_minutes_remaining"; self._attr_native_unit_of_measurement = "min"
    @property
    def native_value(self):
        if self.s["mutual_destruction"] and self.person in self.c["default_targets"]: return 999
        until = self.s["blocked_until"].get(self.person)
        return max(int((until - datetime.now()).total_seconds() / 60), 0) if isinstance(until, datetime) else 0
