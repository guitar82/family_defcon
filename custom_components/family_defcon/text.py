"""Text entities for Family DEFCON dashboard launch interface."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([DashboardPinText(hass)], True)


class DashboardPinText(TextEntity):
    _attr_name = "Dashboard PIN"
    _attr_unique_id = "family_defcon_dashboard_pin"
    _attr_has_entity_name = True
    _attr_mode = "password"
    _attr_native_max = 12
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def native_value(self) -> str:
        return str(self.hass.data[DOMAIN]["state"].get("dashboard_pin", ""))

    async def async_set_value(self, value: str) -> None:
        clean = "".join(ch for ch in str(value) if ch.isdigit())[-12:]
        self.hass.data[DOMAIN]["state"]["dashboard_pin"] = clean
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
