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
    ], True)


class BaseDashboardButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def state_data(self) -> dict:
        return self.hass.data[DOMAIN]["state"]

    @property
    def config_data(self) -> dict:
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
        if not str(self.state_data.get("dashboard_pin", "")):
            self.state_data["last_event"] = "Dashboard confirm rejected. Missing PIN."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return
        if not str(self.state_data.get("dashboard_target", "")):
            self.state_data["last_event"] = "Dashboard confirm rejected. Missing target."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return
        self.state_data["dashboard_confirm"] = True
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardLaunchButton(BaseDashboardButton):
    _attr_name = "Dashboard Launch"
    _attr_unique_id = "family_defcon_dashboard_launch"
    _attr_icon = "mdi:rocket-launch"

    async def async_press(self) -> None:
        pin = str(self.state_data.get("dashboard_pin", ""))
        target = str(self.state_data.get("dashboard_target", ""))
        dashboard = self.config_data.get("dashboard", {})
        station = str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"

        if not pin:
            self.state_data["last_event"] = "Dashboard launch rejected. Missing PIN."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        if not target:
            self.state_data["last_event"] = "Dashboard launch rejected. Missing target."
            self.state_data["dashboard_pin"] = ""
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        if not bool(self.state_data.get("dashboard_confirm", False)):
            self.state_data["last_event"] = "Dashboard launch rejected. Confirm target before launch."
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        await self.hass.services.async_call(
            DOMAIN,
            "launch_with_pin",
            {"pin": pin, "target": target, "station": station},
            blocking=True,
        )

        self.state_data["dashboard_pin"] = ""
        self.state_data["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardCancelButton(BaseDashboardButton):
    _attr_name = "Dashboard Cancel"
    _attr_unique_id = "family_defcon_dashboard_cancel"
    _attr_icon = "mdi:cancel"

    async def async_press(self) -> None:
        dashboard = self.config_data.get("dashboard", {})
        targets = dashboard.get("targets") if isinstance(dashboard, dict) else None
        if not isinstance(targets, list) or not targets:
            targets = list(dict.fromkeys(self.config_data["default_targets"] + self.config_data["parent_targets"]))

        default_target = str(dashboard.get("default_target", "")) if isinstance(dashboard, dict) else ""
        self.state_data["dashboard_pin"] = ""
        self.state_data["dashboard_target"] = default_target if default_target in targets else (str(targets[0]) if targets else "")
        self.state_data["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
