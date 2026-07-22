# Family DEFCON Release Notes

## v2.0.0 beta 1 (draft)

- Modernized all entity platforms to use Home Assistant config-entry setup and unload.
- Reloaded the complete config entry after options or YAML configuration changes.
- Added newly configured or renamed people, sensors, selects, and target buttons without requiring a Home Assistant restart.
- Grouped entities under a Family DEFCON device in the device registry.
- Added redacted downloadable diagnostics for safer beta debugging.
- Simplified HACS metadata so HACS installs directly from the integration directory without a version-specific ZIP asset.
- Added automated HACS and Hassfest validation for pushes and pull requests.
- Rebuilt Configure pages with native Home Assistant URL, time, number, entity,
  and translated select controls.
- Added validation for duplicate people, colliding generated entity IDs,
  duplicate or missing stations, invalid dashboard targets, AdGuard URLs, and
  advanced YAML structures.
- Preserved PIN hashes automatically when people are renamed and removed saved
  PIN hashes from the visible options form; added an explicit clear saved PIN
  control for each person.
- Migrated legacy plaintext option PINs to responsive PBKDF2-SHA256 hashes while
  retaining compatibility with hashes from earlier releases.
- Rejected empty PIN authentication for users without a configured PIN and
  bounded imported PBKDF2 work factors to prevent accidental verification stalls.
- Removed stale renamed target-button and person-sensor registry entries during
  config-entry reloads.
- Added focused tests for configuration defaults, validation, PIN compatibility,
  URL and time normalization, person renames, and station references.

## v1.1.5

- Fixed dashboard target select button labels.
- `DashboardSelectTargetButton` now displays the configured target name instead of the object ID.
- Preserved stable object IDs and unique IDs for existing cards.
- Preserved HACS compliant repository/release structure.
