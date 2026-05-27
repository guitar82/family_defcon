"""Binary sensors for Family DEFCON."""
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, SIGNAL_UPDATE

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([
        MutualDestructionBinarySensor(hass),
        DashboardTargetConfirmedSensor(hass),
    ])

class MutualDestructionBinarySensor(BinarySensorEntity):
    _attr_name = "Mutual WiFi Destruction"; _attr_unique_id = "family_defcon_mutual_wifi_destruction"; _attr_has_entity_name = True
    def __init__(self, hass): self.hass = hass
    @property
    def is_on(self): return bool(self.hass.data[DOMAIN]["state"]["mutual_destruction"])
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))


class DashboardTargetConfirmedSensor(BinarySensorEntity):
    """Dashboard target confirmed state."""

    _attr_name = "Family DEFCON Dashboard Target Confirmed"
    _attr_unique_id = "family_defcon_dashboard_target_confirmed"
    _attr_has_entity_name = False
    _attr_icon = "mdi:target-account"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def is_on(self) -> bool:
        return bool(self.hass.data[DOMAIN]["state"].get("dashboard_confirm", False))

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
