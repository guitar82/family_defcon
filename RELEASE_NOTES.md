# Family DEFCON Release Notes

## Unreleased

- Modernized all entity platforms to use Home Assistant config-entry setup and unload.
- Reloaded the complete config entry after options or YAML configuration changes.
- Added newly configured or renamed people, sensors, selects, and target buttons without requiring a Home Assistant restart.
- Grouped entities under a Family DEFCON device in the device registry.
- Added redacted downloadable diagnostics for safer beta debugging.
- Simplified HACS metadata so HACS installs directly from the integration directory without a version-specific ZIP asset.
- Added automated HACS and Hassfest validation for pushes and pull requests.

## v1.1.5

- Fixed dashboard target select button labels.
- `DashboardSelectTargetButton` now displays the configured target name instead of the object ID.
- Preserved stable object IDs and unique IDs for existing cards.
- Preserved HACS compliant repository/release structure.
