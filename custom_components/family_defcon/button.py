"""Button entities for Family DEFCON dashboard launch interface."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    async_add_entities([
        DashboardConfirmButton(hass),
        DashboardLaunchButton(hass),
        DashboardCancelButton(hass),
    ])


class BaseDashboardButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state))


class DashboardConfirmButton(BaseDashboardButton):
    _attr_name = "Dashboard Confirm Targeting"
    _attr_unique_id = "family_defcon_dashboard_confirm_targeting"
    _attr_icon = "mdi:target"

    async def async_press(self) -> None:
        self.hass.data[DOMAIN]["state"]["dashboard_confirm"] = True


class DashboardLaunchButton(BaseDashboardButton):
    _attr_name = "Dashboard Launch"
    _attr_unique_id = "family_defcon_dashboard_launch"
    _attr_icon = "mdi:rocket-launch"

    async def async_press(self) -> None:
        state = self.hass.data[DOMAIN]["state"]
        config = self.hass.data[DOMAIN]["config"]
        pin = str(state.get("dashboard_pin", ""))
        target = str(state.get("dashboard_target", ""))
        dashboard = config.get("dashboard", {})
        station = str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"

        if not pin:
            await self.hass.services.async_call(DOMAIN, "reload_config", {}, blocking=False)
            state["last_event"] = "Dashboard launch rejected. Missing PIN."
            state["dashboard_confirm"] = False
            return

        await self.hass.services.async_call(
            DOMAIN,
            "launch_with_pin",
            {"pin": pin, "target": target, "station": station},
            blocking=True,
        )
        state["dashboard_pin"] = ""
        state["dashboard_confirm"] = False


class DashboardCancelButton(BaseDashboardButton):
    _attr_name = "Dashboard Cancel"
    _attr_unique_id = "family_defcon_dashboard_cancel"
    _attr_icon = "mdi:cancel"

    async def async_press(self) -> None:
        state = self.hass.data[DOMAIN]["state"]
        config = self.hass.data[DOMAIN]["config"]
        dashboard = config.get("dashboard", {})
        targets = dashboard.get("targets") if isinstance(dashboard, dict) else None
        if not isinstance(targets, list) or not targets:
            targets = list(dict.fromkeys(config["default_targets"] + config["parent_targets"]))
        state["dashboard_pin"] = ""
        state["dashboard_target"] = str(targets[0]) if targets else ""
        state["dashboard_confirm"] = False
