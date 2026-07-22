"""Shared entity helpers for Family DEFCON."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

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
