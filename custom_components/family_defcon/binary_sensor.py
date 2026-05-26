"""Binary sensors for Family DEFCON."""
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, SIGNAL_UPDATE

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([MutualDestructionBinarySensor(hass)])

class MutualDestructionBinarySensor(BinarySensorEntity):
    _attr_name = "Mutual WiFi Destruction"; _attr_unique_id = "family_defcon_mutual_wifi_destruction"; _attr_has_entity_name = True
    def __init__(self, hass): self.hass = hass
    @property
    def is_on(self): return bool(self.hass.data[DOMAIN]["state"]["mutual_destruction"])
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))
