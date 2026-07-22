"""Button entities for Family DEFCON dashboard launch interface.

Stable v5.8.5 note:
This file is based on the working v5.8 backend. It only improves dashboard button behavior:
- Confirm validates the PIN before turning target confirmation on.
- Wrong PIN keeps dashboard_confirm false.
- Launch button sends launch_with_pin non-blocking so the dashboard responds quickly.
- Newly saved UI PIN hashes use instant salted SHA256 for faster local dashboard response.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import re

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from .const import DOMAIN, SIGNAL_TARGET_BUTTONS_UPDATE, SIGNAL_UPDATE


def _slugify_target(value: str) -> str:
    """Create a safe entity id suffix from a configured target name."""
    slug = re.sub(r"[^a-z0-9_]+", "_", str(value).lower()).strip("_")
    return slug or "target"


def _dashboard_targets_from_config(config: dict) -> list[str]:
    """Return the same active dashboard targets used by the dashboard select entity."""
    dashboard = config.get("dashboard", {})
    configured = dashboard.get("targets") if isinstance(dashboard, dict) else None
    people = set(config.get("people", []))

    if isinstance(configured, list) and configured:
        return [str(item) for item in configured if not people or str(item) in people]

    fallback = list(dict.fromkeys(config.get("default_targets", []) + config.get("parent_targets", [])))
    return [str(item) for item in fallback if not people or str(item) in people]


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> None:
    config_data = hass.data[DOMAIN]["config"]
    target_buttons = hass.data[DOMAIN].setdefault("target_button_entities", {})
    entities = [
        DashboardConfirmButton(hass),
        DashboardLaunchButton(hass),
        DashboardCancelButton(hass),
        ParentAdminConfirmButton(hass),
        ParentAdminCancelButton(hass),
        ParentAdminClearAllButton(hass),
        ParentAdminEnforceNowButton(hass),
        ParentAdminArmButton(hass),
        ParentAdminDisarmButton(hass),
        ParentAdminCleanupTargetsButton(hass),
    ]

    for target in _dashboard_targets_from_config(config_data):
        button = DashboardSelectTargetButton(hass, target)
        target_buttons[button.target_slug] = button
        entities.append(button)

    async_add_entities(entities, True)

    def _sync_target_buttons() -> None:
        """Add or refresh dynamic target buttons after config/options reloads."""
        target_buttons = hass.data[DOMAIN].setdefault("target_button_entities", {})
        new_entities: list[DashboardSelectTargetButton] = []

        for target in _dashboard_targets_from_config(hass.data[DOMAIN]["config"]):
            target_name = str(target)
            target_slug = _slugify_target(target_name)
            existing = target_buttons.get(target_slug)

            if existing is not None:
                existing.update_target_name(target_name)
                existing.async_write_ha_state()
                continue

            button = DashboardSelectTargetButton(hass, target_name)
            target_buttons[target_slug] = button
            new_entities.append(button)

        if new_entities:
            async_add_entities(new_entities, True)

    remove_listener = hass.data[DOMAIN].get("remove_target_button_sync_listener")
    if remove_listener:
        remove_listener()
    hass.data[DOMAIN]["remove_target_button_sync_listener"] = async_dispatcher_connect(
        hass,
        SIGNAL_TARGET_BUTTONS_UPDATE,
        _sync_target_buttons,
    )


def _verify_pin_value(pin: str, user_data: dict) -> bool:
    """Verify fast SHA256 hashes, old PBKDF2 hashes, or legacy plain text PINs."""
    stored_hash = str(user_data.get("pin_hash", "") or "")
    if stored_hash:
        try:
            parts = stored_hash.split("$")
            algo = parts[0]

            if algo == "sha256" and len(parts) == 3:
                _, salt, expected = parts
                digest = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
                return hmac.compare_digest(digest, expected)

            if algo == "pbkdf2_sha256" and len(parts) == 4:
                _, iterations_raw, salt, expected = parts
                digest = hashlib.pbkdf2_hmac(
                    "sha256",
                    str(pin).encode(),
                    salt.encode(),
                    int(iterations_raw),
                ).hex()
                return hmac.compare_digest(digest, expected)

            return False
        except Exception:
            return False

    return hmac.compare_digest(str(user_data.get("pin", "")), str(pin))


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

    def dashboard_station(self) -> str:
        dashboard = self.config_data.get("dashboard", {})
        return str(dashboard.get("station_id", "dashboard")) if isinstance(dashboard, dict) else "dashboard"

    def _pin_locked_remaining(self, station: str) -> int:
        locked_raw = self.state_data.get("pin_locked_until", {}).get(station)
        if not locked_raw:
            return 0
        try:
            locked_until = datetime.fromisoformat(locked_raw)
            return max(int((locked_until - datetime.now()).total_seconds()), 0)
        except Exception:
            return 0

    def _verify_dashboard_pin(self, pin: str) -> tuple[bool, str]:
        for person, data in self.config_data.get("auth", {}).get("users", {}).items():
            if _verify_pin_value(pin, data if isinstance(data, dict) else {}):
                return True, str(person)
        return False, ""

    def _record_bad_pin(self, station: str) -> None:
        attempts = int(self.state_data.get("pin_bad_attempts", {}).get(station, 0)) + 1
        self.state_data.setdefault("pin_bad_attempts", {})[station] = attempts

        max_attempts = int(self.config_data.get("auth", {}).get("max_bad_pin_attempts", 3))
        remaining_attempts = max(max_attempts - attempts, 0)

        self.state_data["dashboard_confirm"] = False

        if attempts >= max_attempts:
            lockout_seconds = int(self.config_data.get("auth", {}).get("lockout_seconds_after_bad_pins", 120))
            until = datetime.now() + timedelta(seconds=lockout_seconds)
            self.state_data.setdefault("pin_locked_until", {})[station] = until.isoformat()
            self.state_data["pin_bad_attempts"][station] = 0
            self.state_data["last_event"] = f"Invalid PIN. Terminal locked until {until.strftime('%H:%M:%S')}."
        else:
            suffix = "s" if remaining_attempts != 1 else ""
            self.state_data["last_event"] = f"Invalid PIN. {remaining_attempts} attempt{suffix} left before lockout."

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )


class DashboardSelectTargetButton(BaseDashboardButton):
    """One dynamic target select button per configured dashboard target."""

    def __init__(self, hass: HomeAssistant, target_name: str) -> None:
        super().__init__(hass)
        self.target_name = str(target_name)
        self.target_slug = _slugify_target(self.target_name)
        object_id = f"family_defcon_select_target_{self.target_slug}"
        # Display the actual configured target name on dashboards, not the entity/object id.
        # Keep the object id and unique id stable so existing Lovelace cards keep working.
        self._attr_has_entity_name = False
        self._attr_name = self.target_name
        self._attr_unique_id = object_id
        self._attr_suggested_object_id = object_id
        self._attr_icon = "mdi:account-crosshairs"

    def update_target_name(self, target_name: str) -> None:
        """Refresh display metadata when a target is renamed but keeps the same slug."""
        self.target_name = str(target_name)
        self.target_slug = _slugify_target(self.target_name)
        self._attr_name = self.target_name

    @property
    def extra_state_attributes(self) -> dict:
        """Expose configured target metadata for dynamic dashboard cards."""
        return {
            "target": self.target_name,
            "display_name": self.target_name,
            "friendly_label": self.target_name,
            "target_slug": self.target_slug,
            "is_default_target": self.target_name in self.config_data.get("default_targets", []),
            "is_parent_target": self.target_name in self.config_data.get("parent_targets", []),
        }

    @property
    def available(self) -> bool:
        return self.target_name in _dashboard_targets_from_config(self.config_data)

    async def async_press(self) -> None:
        if not self.available:
            self.state_data["last_event"] = f"Dashboard target rejected. {self.target_name} is not configured."
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        self.state_data["dashboard_target"] = self.target_name
        self.state_data["dashboard_confirm"] = False
        self.state_data["last_event"] = f"Dashboard target selected: {self.target_name}. Enter PIN and confirm."
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardConfirmButton(BaseDashboardButton):
    _attr_name = "Dashboard Confirm Targeting"
    _attr_unique_id = "family_defcon_dashboard_confirm_targeting"
    _attr_suggested_object_id = "family_defcon_dashboard_confirm_targeting"
    _attr_icon = "mdi:target"

    async def async_press(self) -> None:
        pin = str(self.state_data.get("dashboard_pin", ""))
        target = str(self.state_data.get("dashboard_target", ""))
        station = self.dashboard_station()

        if not pin:
            self.state_data["last_event"] = "Dashboard confirm rejected. Missing PIN."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        if len(pin) > 4:
            self.state_data["last_event"] = "Dashboard confirm rejected. PIN must be 4 digits or fewer."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        if not target:
            self.state_data["last_event"] = "Dashboard confirm rejected. Missing target."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        remaining = self._pin_locked_remaining(station)
        if remaining > 0:
            self.state_data["last_event"] = f"PIN entry locked at {station} for {remaining} seconds."
            self.state_data["dashboard_confirm"] = False
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        valid, launcher = self._verify_dashboard_pin(pin)
        if not valid:
            self._record_bad_pin(station)
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        self.state_data.setdefault("pin_bad_attempts", {})[station] = 0
        self.state_data["dashboard_confirm"] = True
        self.state_data["last_event"] = f"Dashboard target confirmed by {launcher}. Target locked: {target}."
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardLaunchButton(BaseDashboardButton):
    _attr_name = "Dashboard Launch"
    _attr_unique_id = "family_defcon_dashboard_launch"
    _attr_suggested_object_id = "family_defcon_dashboard_launch"
    _attr_icon = "mdi:rocket-launch"

    async def async_press(self) -> None:
        pin = str(self.state_data.get("dashboard_pin", ""))
        target = str(self.state_data.get("dashboard_target", ""))
        station = self.dashboard_station()

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
            self.state_data["last_event"] = "Dashboard launch rejected. Confirm valid PIN before launch."
            async_dispatcher_send(self.hass, SIGNAL_UPDATE)
            return

        self.state_data["last_event"] = f"Launch sent for target {target}. Applying rules..."
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

        await self.hass.services.async_call(
            DOMAIN,
            "launch_with_pin",
            {"pin": pin, "target": target, "station": station},
            blocking=False,
        )

        self.state_data["dashboard_pin"] = ""
        self.state_data["dashboard_confirm"] = False
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class DashboardCancelButton(BaseDashboardButton):
    _attr_name = "Dashboard Cancel"
    _attr_unique_id = "family_defcon_dashboard_cancel"
    _attr_suggested_object_id = "family_defcon_dashboard_cancel"
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
        self.state_data["last_event"] = "Dashboard command cancelled."
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)


class ParentAdminServiceButton(BaseDashboardButton):
    """Base button for parent-admin PIN protected service actions."""

    service_name: str = ""
    icon_name: str = "mdi:shield-account"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)
        self._attr_icon = self.icon_name

    async def async_press(self) -> None:
        await self.hass.services.async_call(DOMAIN, self.service_name, {}, blocking=False)








class ParentAdminConfirmButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_confirm"
    _attr_unique_id = "family_defcon_parent_admin_confirm"
    _attr_suggested_object_id = "parent_admin_confirm"
    service_name = "parent_admin_confirm"
    icon_name = "mdi:shield-check"


class ParentAdminCancelButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_cancel"
    _attr_unique_id = "family_defcon_parent_admin_cancel"
    _attr_suggested_object_id = "parent_admin_cancel"
    service_name = "parent_admin_cancel"
    icon_name = "mdi:cancel"


class ParentAdminClearAllButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_clear_all"
    _attr_unique_id = "family_defcon_parent_admin_clear_all"
    _attr_suggested_object_id = "parent_admin_clear_all"
    service_name = "parent_admin_clear_all"
    icon_name = "mdi:restart"


class ParentAdminEnforceNowButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_enforce_now"
    _attr_unique_id = "family_defcon_parent_admin_enforce_now"
    _attr_suggested_object_id = "parent_admin_enforce_now"
    service_name = "parent_admin_enforce_now"
    icon_name = "mdi:shield-sync"


class ParentAdminArmButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_arm"
    _attr_unique_id = "family_defcon_parent_admin_arm"
    _attr_suggested_object_id = "parent_admin_arm"
    service_name = "parent_admin_arm"
    icon_name = "mdi:shield-lock"


class ParentAdminDisarmButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_disarm"
    _attr_unique_id = "family_defcon_parent_admin_disarm"
    _attr_suggested_object_id = "parent_admin_disarm"
    service_name = "parent_admin_disarm"
    icon_name = "mdi:shield-off"


class ParentAdminCleanupTargetsButton(ParentAdminServiceButton):
    _attr_name = "parent_admin_cleanup_targets"
    _attr_unique_id = "family_defcon_parent_admin_cleanup_targets"
    _attr_suggested_object_id = "parent_admin_cleanup_targets"
    service_name = "parent_admin_cleanup_targets"
    icon_name = "mdi:broom"
