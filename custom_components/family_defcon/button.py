"""Button entities for Family DEFCON dashboard launch interface."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([
        DashboardConfirmButton(hass),
        DashboardLaunchButton(hass),
        DashboardCancelButton(hass),
    ])


class BaseDashboardButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def _state(self) -> dict:
        return self.hass.data[DOMAIN]["state"]

    @property
    def _config(self) -> dict:
        return self.hass.data[DOMAIN]["config"]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )


class DashboardConfirmButton(BaseDashboardButton):
    _attr_name = "Dashboard Confirm Targeting"
    _attr_unique_id = "family_defcon_dashboard_confirm_targeting"
    _attr_icon = "mdi:target"

    async def async_press(self) -> None:
        self._state["dashboard_confirm"] = True
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardLaunchButton(BaseDashboardButton):
    _attr_name = "Dashboard Launch"
    _attr_unique_id = "family_defcon_dashboard_launch"
    _attr_icon = "mdi:rocket-launch"

    async def async_press(self) -> None:
        pin = str(self._state.get("dashboard_pin", ""))
        target = str(self._state.get("dashboard_target", ""))
        dashboard = self._config.get("dashboard", {})
        station = str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"

        if not pin:
            self._state["last_event"] = "Dashboard launch rejected. Missing PIN."
            self._state["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        await self.hass.services.async_call(
            DOMAIN,
            "launch_with_pin",
            {"pin": pin, "target": target, "station": station},
            blocking=True,
        )

        self._state["dashboard_pin"] = ""
        self._state["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardCancelButton(BaseDashboardButton):
    _attr_name = "Dashboard Cancel"
    _attr_unique_id = "family_defcon_dashboard_cancel"
    _attr_icon = "mdi:cancel"

    async def async_press(self) -> None:
        dashboard = self._config.get("dashboard", {})
        targets = dashboard.get("targets") if isinstance(dashboard, dict) else None
        if not isinstance(targets, list) or not targets:
            targets = list(dict.fromkeys(self._config["default_targets"] + self._config["parent_targets"]))

        self._state["dashboard_pin"] = ""
        self._state["dashboard_target"] = str(targets[0]) if targets else ""
        self._state["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
