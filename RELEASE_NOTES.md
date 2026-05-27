# Family DEFCON Release Notes

## v5.8.15

- Fixed dynamic target button entity IDs by making the entity name deterministic.
- Added display_name target metadata for dynamic dashboard rendering.
- Added `examples/dashboard_dynamic_target_buttons_only.yaml` that supports both old and new target entity IDs.
- Preserved cleanup service, startup cleanup, fallback dashboard, hidden PIN state, instant PIN verification, and native HA events.

## v5.8.14

- Fixed cleanup service registration so `family_defcon.cleanup_target_button_entities` loads correctly.
- Added startup cleanup of stale `button.select_target_*` entity registry entries.
- Dynamic dashboard now includes both `button.family_defcon_select_target_*` and `button.select_target_*` filters.
- Added `examples/dashboard_launch_console_basic_no_auto_entities.yaml` as a fallback dashboard.
- Preserved v5.8.12 privacy fixes, hidden PIN state, instant PIN verification, dynamic target buttons, and native HA events.

## v5.8.13

- Added `family_defcon.cleanup_target_button_entities` service.
- The service removes stale target button entity registry entries from old builds.
- The cleanup can be run from Developer Tools > Actions without terminal scripts or tokens.
- Preserved dynamic target buttons, hidden PIN state, instant PIN verification, native HA events, and v5.8.12 privacy fixes.

## v5.8.12

- Fixed privacy issue where internal dashboard PIN could be saved to persistent storage.
- Dashboard confirmation is now always cleared on restart and reload.
- UI options update listener now calls reload_config instead of a no-op config entry reload.
- Fixed People options form so dashboard target checkboxes respect saved settings.
- Legacy dashboard launch helper now supports hashed PIN verification.
- Updated hash_pin service description for fast SHA256 hashes.
- Preserved dynamic target buttons, hidden PIN entity state, instant PIN verification, and native HA events.

## v5.8.11 Pre-release audit fixes

- Added deterministic suggested object IDs to core dashboard entities.
- Added deterministic family_defcon-prefixed entity IDs for person WiFi sensors.
- Updated dashboard people sensor attributes to point to deterministic person sensor IDs.
- Added target metadata attributes to dynamic target buttons.
- Updated dynamic dashboard example to use target attributes instead of parsing friendly names.
- Added dispatcher update when selecting dashboard target from the select dropdown.
- Preserved v5.8.10 dynamic button ID fix and stable v5.8.x backend.

## v5.8.10

- Fixed generated target button entity IDs by adding suggested object IDs.
- Dynamic target buttons now reliably appear as `button.family_defcon_select_target_*` on new installs.
- Added deterministic suggested object IDs to core dashboard buttons too.
- Preserved v5.8.9 public beta cleanup, hidden PIN state, instant PIN verification, and native HA events.

## v5.8.9 Clean Public Beta

- Built from the stable v5.8.x dynamic line.
- Removed active demo PINs from the YAML backup example.
- Replaced README with a UI-first new installer guide.
- Promoted the dynamic target dashboard as the primary launch console.
- Moved stale hard-coded dashboard examples into `examples/legacy` when present.
- Added privacy/recorder guidance for the masked PIN text entity.
- Preserved dynamic target buttons, hidden PIN state, instant PIN verification, and native HA events.

## v5.8.8

Clean dynamic installer package.

Changes:
- Built from stable v5.8.7.
- UI default people are generic: Parent 1, Parent 2, Child 1, Child 2, Child 3.
- Removed stale hard coded dashboard examples from the package.
- Kept the dynamic dashboard example based on generated target button entities.
- Kept hidden dashboard PIN state.
- Kept instant salted SHA256 PIN verification.
- Kept native Home Assistant events.
- Does not include v5.9 or v5.10 backend startup changes.
