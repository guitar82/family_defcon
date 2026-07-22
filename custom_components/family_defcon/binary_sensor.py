"""Binary sensors for Family DEFCON."""
from __future__ import annotations
from datetime import datetime
from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up Family DEFCON binary sensors from a config entry."""
    async_add_entry_entities(entry, async_add_entities, [
        MutualDestructionBinarySensor(hass),
        DashboardTargetConfirmedSensor(hass),
        ParentAdminConfirmedBinarySensor(hass),
    ])

class MutualDestructionBinarySensor(BinarySensorEntity):
    _attr_name = "Mutual WiFi Destruction"; _attr_unique_id = "family_defcon_mutual_wifi_destruction"; _attr_suggested_object_id = "family_defcon_mutual_wifi_destruction"; _attr_has_entity_name = True
    def __init__(self, hass): self.hass = hass
    @property
    def is_on(self): return bool(self.hass.data[DOMAIN]["state"]["mutual_destruction"])
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))


class DashboardTargetConfirmedSensor(BinarySensorEntity):
    """Dashboard target confirmed state."""

    _attr_name = "Dashboard Target Confirmed"
    _attr_unique_id = "family_defcon_dashboard_target_confirmed"
    _attr_suggested_object_id = "family_defcon_dashboard_target_confirmed"
    _attr_has_entity_name = True
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




class ParentAdminConfirmedBinarySensor(BinarySensorEntity):
    """Parent admin confirmation session state."""

    _attr_name = "parent_admin_confirmed"
    _attr_unique_id = "family_defcon_parent_admin_confirmed"
    _attr_suggested_object_id = "parent_admin_confirmed"
    _attr_icon = "mdi:shield-check"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def is_on(self) -> bool:
        state = self.hass.data[DOMAIN]["state"]
        expires = state.get("parent_admin_confirm_expires")
        return bool(state.get("parent_admin_confirm")) and isinstance(expires, datetime) and expires > datetime.now()

    @property
    def extra_state_attributes(self) -> dict:
        state = self.hass.data[DOMAIN]["state"]
        expires = state.get("parent_admin_confirm_expires")
        return {
            "confirmed_by": state.get("parent_admin_confirmed_by", ""),
            "expires": expires.isoformat() if isinstance(expires, datetime) else None,
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
