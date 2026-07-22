"""Switches for Family DEFCON."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE
from .entity import async_add_entry_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Family DEFCON switches from a config entry."""
    async_add_entry_entities(
        entry,
        async_add_entities,
        [ArmedSwitch(hass), AllowParentTargetsSwitch(hass)],
    )


class BaseSwitch(SwitchEntity):
    """Base class for Family DEFCON switches."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def s(self) -> dict:
        return self.hass.data[DOMAIN]["state"]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE,
                self.async_write_ha_state,
            )
        )


class ArmedSwitch(BaseSwitch):
    """Control whether the command system is armed."""

    _attr_name = "Command System Armed"
    _attr_unique_id = "family_defcon_command_system_armed"
    _attr_suggested_object_id = "family_defcon_command_system_armed"

    @property
    def is_on(self) -> bool:
        return bool(self.s["armed"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "set_armed",
            {"enabled": True},
            blocking=False,
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "set_armed",
            {"enabled": False},
            blocking=False,
        )


class AllowParentTargetsSwitch(BaseSwitch):
    """Control whether parents may be selected as targets."""

    _attr_name = "Allow Parent Targets"
    _attr_unique_id = "family_defcon_allow_parent_targets"
    _attr_suggested_object_id = "family_defcon_allow_parent_targets"

    @property
    def is_on(self) -> bool:
        return bool(self.s["allow_parent_targets"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "set_parent_targets",
            {"enabled": True},
            blocking=False,
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "set_parent_targets",
            {"enabled": False},
            blocking=False,
        )
