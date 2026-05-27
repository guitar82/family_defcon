"""Select entities for Family DEFCON dashboard launch interface."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([DashboardTargetSelect(hass)], True)


class DashboardTargetSelect(SelectEntity):
    _attr_name = "Dashboard Target"
    _attr_unique_id = "family_defcon_dashboard_target"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def options(self) -> list[str]:
        """Return active dashboard targets from normalized config."""
        config = self.hass.data[DOMAIN]["config"]
        dashboard = config.get("dashboard", {})
        configured = dashboard.get("targets") if isinstance(dashboard, dict) else None
        people = set(config.get("people", []))

        if isinstance(configured, list) and configured:
            return [str(item) for item in configured if not people or str(item) in people]

        fallback = list(dict.fromkeys(config.get("default_targets", []) + config.get("parent_targets", [])))
        return [str(item) for item in fallback if not people or str(item) in people]

    @property
    def current_option(self) -> str | None:
        current = str(self.hass.data[DOMAIN]["state"].get("dashboard_target", ""))
        if current in self.options:
            return current
        return self.options[0] if self.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            return
        self.hass.data[DOMAIN]["state"]["dashboard_target"] = str(option)
        self.hass.data[DOMAIN]["state"]["dashboard_confirm"] = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
