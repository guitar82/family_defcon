"""Shared entity helpers for Family DEFCON."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def async_add_entry_entities(
    entry: ConfigEntry,
    async_add_entities,
    entities: Iterable[Entity],
    *,
    update_before_add: bool = False,
) -> None:
    """Attach entities to the config entry's service device and add them."""
    entity_list = list(entities)
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or "Family DEFCON",
        manufacturer="Family DEFCON",
        model="Command System",
        configuration_url="https://github.com/guitar82/family_defcon",
    )

    for entity in entity_list:
        entity._attr_device_info = device_info

    async_add_entities(entity_list, update_before_add)


def async_remove_stale_entry_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    active_unique_ids: set[str],
    *,
    unique_id_prefixes: tuple[str, ...] = (),
    unique_id_suffixes: tuple[str, ...] = (),
) -> list[str]:
    """Remove obsolete generated entities owned by this config entry."""
    registry = er.async_get(hass)
    removed: list[str] = []

    for registry_entry in list(registry.entities.values()):
        if registry_entry.config_entry_id != entry.entry_id:
            continue
        if registry_entry.platform != DOMAIN:
            continue

        unique_id = str(registry_entry.unique_id)
        managed = unique_id.startswith(unique_id_prefixes) or unique_id.endswith(
            unique_id_suffixes
        )
        if not managed or unique_id in active_unique_ids:
            continue

        registry.async_remove(registry_entry.entity_id)
        removed.append(registry_entry.entity_id)

    return removed
