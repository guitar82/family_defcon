"""Text entities for Family DEFCON dashboard launch interface.

The raw dashboard PIN is intentionally not exposed as the Home Assistant entity state.
The real PIN is kept only in integration memory. The entity state shows masked bullets.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import DOMAIN, SIGNAL_UPDATE
from .entity import async_add_entry_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Family DEFCON text entities from a config entry."""
    async_add_entry_entities(
        entry,
        async_add_entities,
        [DashboardPinText(hass), ParentAdminPinText(hass)],
        update_before_add=True,
    )


class DashboardPinText(TextEntity):
    _attr_name = "Dashboard PIN"
    _attr_unique_id = "family_defcon_dashboard_pin"
    _attr_suggested_object_id = "family_defcon_dashboard_pin"
    _attr_has_entity_name = True
    _attr_mode = TextMode.PASSWORD
    _attr_native_max = 4
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def native_value(self) -> str:
        pin = str(self.hass.data[DOMAIN]["state"].get("dashboard_pin", ""))
        return "●" * min(len(pin), 4)

    async def async_set_value(self, value: str) -> None:
        clean = "".join(ch for ch in str(value) if ch.isdigit())[:4]
        self.hass.data[DOMAIN]["state"]["dashboard_pin"] = clean
        self.hass.data[DOMAIN]["state"]["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE, self.async_write_ha_state
            )
        )


class ParentAdminPinText(TextEntity):
    """Hidden parent admin PIN input. Raw value is not exposed as entity state."""

    _attr_name = "Parent Admin PIN"
    _attr_unique_id = "family_defcon_parent_admin_pin"
    _attr_suggested_object_id = "family_defcon_parent_admin_pin"
    _attr_has_entity_name = True
    _attr_mode = TextMode.PASSWORD
    _attr_native_max = 4
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def native_value(self) -> str:
        pin = str(self.hass.data[DOMAIN]["state"].get("parent_admin_pin", ""))
        return "●" * min(len(pin), 4)

    async def async_set_value(self, value: str) -> None:
        clean = "".join(ch for ch in str(value) if ch.isdigit())[:4]
        self.hass.data[DOMAIN]["state"]["parent_admin_pin"] = clean
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE, self.async_write_ha_state
            )
        )
