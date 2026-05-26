"""Switches for Family DEFCON."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([ArmedSwitch(hass), AllowParentTargetsSwitch(hass)])


class FamilyDefconBaseSwitch(SwitchEntity):
    _attr_should_poll = False
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
    @property
    def manager(self):
        return self.hass.data[DOMAIN]
    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))


class ArmedSwitch(FamilyDefconBaseSwitch):
    _attr_name = "Family DEFCON Command System Armed"
    _attr_unique_id = "family_defcon_command_system_armed"
    @property
    def is_on(self) -> bool:
        return bool(self.manager.state.get("armed", False))
    async def async_turn_on(self, **kwargs) -> None:
        await self.manager.async_set_armed(True)
    async def async_turn_off(self, **kwargs) -> None:
        await self.manager.async_set_armed(False)


class AllowParentTargetsSwitch(FamilyDefconBaseSwitch):
    _attr_name = "Family DEFCON Allow Mom and Dad Targets"
    _attr_unique_id = "family_defcon_allow_parent_targets"
    @property
    def is_on(self) -> bool:
        return bool(self.manager.state.get("allow_parent_targets", False))
    async def async_turn_on(self, **kwargs) -> None:
        await self.manager.async_set_parent_targets(True)
    async def async_turn_off(self, **kwargs) -> None:
        await self.manager.async_set_parent_targets(False)
