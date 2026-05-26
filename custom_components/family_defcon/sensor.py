"""Sensors for Family DEFCON."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    manager = hass.data[DOMAIN]
    entities = [DefconLevelSensor(hass), PeaceStatusSensor(hass), DailyLaunchesSensor(hass), ConflictChainSensor(hass), LastLauncherSensor(hass), LastTargetSensor(hass), LastEventSensor(hass)]
    for person in manager.people:
        entities.append(PersonWifiStatusSensor(hass, person))
        entities.append(PersonMinutesRemainingSensor(hass, person))
    async_add_entities(entities)


class FamilyDefconBaseSensor(SensorEntity):
    _attr_should_poll = False
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
    @property
    def manager(self):
        return self.hass.data[DOMAIN]
    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))


class DefconLevelSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Level"
    _attr_unique_id = "family_defcon_level"
    @property
    def native_value(self) -> int:
        return self.manager.defcon_level()


class PeaceStatusSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Peace Status"
    _attr_unique_id = "family_defcon_peace_status"
    @property
    def native_value(self) -> str:
        return self.manager.peace_status()


class DailyLaunchesSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Daily Launches"
    _attr_unique_id = "family_defcon_daily_launches"
    @property
    def native_value(self) -> int:
        return int(self.manager.state.get("daily_launches", 0))


class ConflictChainSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Conflict Chain"
    _attr_unique_id = "family_defcon_conflict_chain"
    @property
    def native_value(self) -> int:
        return int(self.manager.state.get("conflict_chain", 0))


class LastLauncherSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Last Launcher"
    _attr_unique_id = "family_defcon_last_launcher"
    @property
    def native_value(self) -> str:
        return self.manager.state.get("last_launcher", "")


class LastTargetSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Last Target"
    _attr_unique_id = "family_defcon_last_target"
    @property
    def native_value(self) -> str:
        return self.manager.state.get("last_target", "")


class LastEventSensor(FamilyDefconBaseSensor):
    _attr_name = "Family DEFCON Last Event"
    _attr_unique_id = "family_defcon_last_event"
    @property
    def native_value(self) -> str:
        return self.manager.state.get("last_event", "")
    @property
    def extra_state_attributes(self) -> dict:
        return {"event_log": self.manager.state.get("event_log", [])}


class PersonWifiStatusSensor(FamilyDefconBaseSensor):
    def __init__(self, hass: HomeAssistant, person: str) -> None:
        super().__init__(hass)
        self.person = person
        slug = person.lower().replace(" ", "_")
        self._attr_name = f"{person} WiFi Status"
        self._attr_unique_id = f"family_defcon_{slug}_wifi_status"
    @property
    def native_value(self) -> str:
        return "blocked" if self.manager.person_blocked(self.person) else "allowed"


class PersonMinutesRemainingSensor(FamilyDefconBaseSensor):
    _attr_native_unit_of_measurement = "min"
    def __init__(self, hass: HomeAssistant, person: str) -> None:
        super().__init__(hass)
        self.person = person
        slug = person.lower().replace(" ", "_")
        self._attr_name = f"{person} WiFi Minutes Remaining"
        self._attr_unique_id = f"family_defcon_{slug}_wifi_minutes_remaining"
    @property
    def native_value(self) -> int:
        return self.manager.minutes_remaining(self.person)
