# Family DEFCON Release Notes

## Unreleased

- Refreshed generated dashboard target buttons after options/config reloads.
- Added newly configured or renamed target buttons without requiring a clean Home Assistant startup.
- Kept stale renamed-away target buttons unavailable until cleanup/restart, matching the legacy platform limits.

## v1.1.5

- Fixed dashboard target select button labels.
- `DashboardSelectTargetButton` now displays the configured target name instead of the object ID.
- Preserved stable object IDs and unique IDs for existing cards.
- Preserved HACS compliant repository/release structure.
