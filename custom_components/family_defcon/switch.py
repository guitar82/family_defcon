"""Switches for Family DEFCON."""
from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, SIGNAL_UPDATE

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([ArmedSwitch(hass), AllowParentTargetsSwitch(hass)])

class BaseSwitch(SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, hass): self.hass = hass
    @property
    def s(self): return self.hass.data[DOMAIN]["state"]
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))

class ArmedSwitch(BaseSwitch):
    _attr_name = "Command System Armed"; _attr_unique_id = "family_defcon_command_system_armed"
    @property
    def is_on(self): return bool(self.s["armed"])
    async def async_turn_on(self, **kwargs): await self.hass.services.async_call(DOMAIN, "set_armed", {"enabled": True}, blocking=False)
    async def async_turn_off(self, **kwargs): await self.hass.services.async_call(DOMAIN, "set_armed", {"enabled": False}, blocking=False)

class AllowParentTargetsSwitch(BaseSwitch):
    _attr_name = "Allow Mom and Dad Targets"; _attr_unique_id = "family_defcon_allow_parent_targets"
    @property
    def is_on(self): return bool(self.s["allow_parent_targets"])
    async def async_turn_on(self, **kwargs): await self.hass.services.async_call(DOMAIN, "set_parent_targets", {"enabled": True}, blocking=False)
    async def async_turn_off(self, **kwargs): await self.hass.services.async_call(DOMAIN, "set_parent_targets", {"enabled": False}, blocking=False)
