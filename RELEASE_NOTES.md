# Family DEFCON Release Notes

## v1.0.9 Loader Config Fix

- Fixed config-entry early return that could skip newly added service registrations after HACS/GitHub updates.
- Service registration is now idempotent and replaces old in-memory services.
- Platforms are loaded only once to avoid duplicate entities.
- Periodic timer is replaced on setup rerun.
- UI option updates re-run setup so AdGuard config mapping and actions refresh.

## v1.0.8 AdGuard Connection Fix

- Normalized AdGuard base URL from UI/YAML before API calls.
- Added support for literal or secret-based AdGuard credentials.
- Added `family_defcon.adguard_connection_test` action.
- Improved AdGuard GET/POST diagnostics with sanitized endpoint and HTTP response details.

## v1.0.7 Audit Patch

- Consolidated status logic across DEFCON level, dashboard people, and per person status sensors.
- Added status debug attributes: `active_block_count`, `blocked_until_keys`, `blocked`, `minutes_remaining`, and `status`.
- Avoided duplicate platform/timer setup on config entry reload when already loaded.
- Allowed AdGuard username/password UI secret fields to fall back to literal values when a matching secret is not found.
- Fixed debug notification logger typo.

## v1.0.6 Status State Fix

- Restores saved `blocked_until` values case-insensitively.
- Preserves active timeouts during config reload with case-safe matching.
- Canonicalizes launcher and target names during launch.
- Writes timeouts using configured person names.
- Per-person WiFi status/minutes sensors now use case-insensitive timeout lookup.

## v1.0.5 Case Safe Status Fix

- Fixed dashboard status lookup when person names differ by case.
- `sensor.family_defcon_dashboard_people` now checks `blocked_until` case-insensitively.
- Parent/default target role checks are now case-insensitive.
- Removed missing AdGuard diagnostic entity rows from the status dashboard example.

## v1.0.4 Dashboard Status Fix

- Added direct per-person status snapshot attributes to `sensor.family_defcon_dashboard_people`.
- Status dashboard now reads `p.blocked`, `p.status`, and `p.minutes_remaining` directly.
- Fixes dashboard showing ONLINE when the person is actually blocked.

## v1.0.3 UI AdGuard Mapping Fix

- Replaced partial UI AdGuard refresh with deterministic UI-to-runtime mapping.
- UI AdGuard config now builds the exact same `dns.adguard_home` structure as the working advanced YAML config.
- UI AdGuard URL wins over blank/default runtime config.
- `family_defcon.adguard_config_status` reports both UI and runtime URL status.

## v1.0.2 AdGuard Diagnostics

- Added `family_defcon.debug_status`.
- `debug_status` creates a persistent notification with UI/runtime AdGuard status.
- `adguard_config_status` now also creates a persistent notification.

## v1.0.1 UI AdGuard Fix

- Fixed UI-only AdGuard settings not being applied to active runtime enforcement config.
- Forces AdGuard URL, enabled state, enforcement mode, rule prefix, and client names from UI config before enforcement.
- Added `family_defcon.adguard_config_status` action.

## v1.0.0 Stable Clean Examples

- Removed old and duplicate examples.
- Kept only three dashboard examples and the automation announcement sample.

## v1.0.0 Stable

- Promoted the working v5.8.32 build to v1.0.0 stable.
- Launcher flow confirmed working.
- Parent command interface confirmed working.
- Parent confirm action confirmed working.
- Parent admin buttons confirmed working.
- Dynamic target buttons confirmed working.
- Old parent verify/keypad flows removed from current dashboards.

## v5.8.32

- GitHub/HACS-focused parent confirm fix.
- Registers `family_defcon.parent_admin_confirm` and `family_defcon.parent_admin_cancel` in the main async_setup block.
- Prevents setup_complete early return from skipping new service registrations after update.
- Parent dashboard CONFIRM calls `family_defcon.parent_admin_confirm` directly.

## v5.8.31

- Hard fix for missing `family_defcon.parent_admin_confirm` and `family_defcon.parent_admin_cancel` actions.
- Registers parent confirm/cancel in the same service registration block as the working dashboard keypad services.
- Forces async_setup_entry updates to rerun async_setup instead of returning early from setup_complete.
- Adds HA terminal installer script to prevent wrong folder extraction.

## v5.8.30

- Added reload-safe registration for `parent_admin_confirm` and `parent_admin_cancel`.
- Fixes the Home Assistant `setup_complete` reload path where new services could be skipped.
- CONFIRM still calls `family_defcon.parent_admin_confirm` directly.

## v5.8.29

- Fixed missing `family_defcon.parent_admin_confirm` registration.
- Fixed missing `family_defcon.parent_admin_cancel` registration.
- Parent confirm/cancel services are now registered beside the working dashboard keypad services.
- Added validation for service registration, services.yaml, button classes, and dashboard references.

## v5.8.28

- Parent CONFIRM now calls `family_defcon.parent_admin_confirm` directly from the dashboard.
- Parent CANCEL calls `family_defcon.parent_admin_cancel` directly.
- Dashboard no longer depends on parent confirm status entities to show success.
- This bypasses the fragile `button.press -> custom service` path for confirm/cancel.

## v5.8.27

- Final parent terminal fix using launcher-style confirm flow.
- Deterministic parent button and sensor entity IDs.
- No old verify button or parent keypad services in current examples.

## v5.8.26

- Archived old dashboard examples into `examples/_archive_old_examples/`.
- Kept only current working examples visible in the main examples folder.
- Made `dashboard_parent_interface.yaml`, `dashboard_parent_interface_working.yaml`, and `dashboard_parent_interface_launcher_style.yaml` identical to prevent stale parent dashboard confusion.
- Added README files explaining which examples to use.

## v5.8.25

- Fixed parent admin confirmed binary sensor import/load issue.
- Fixed parent admin status sensor base class and registration.
- Parent launcher-style dashboard remains the recommended dashboard.
- This build specifically fixes HA import/runtime issues that py_compile alone would not catch.

## v5.8.24

- Rebuilt parent terminal to mirror launcher structure.
- Added `parent_admin_confirm` and `parent_admin_cancel` buttons.
- Added `binary_sensor.parent_admin_confirmed`, `sensor.parent_admin_confirmed_by`, and `sensor.parent_admin_status`.
- Parent admin actions now require an active parent confirmation session instead of trying to verify PIN directly every time.
- Parent dashboard uses existing dashboard keypad only.
- Removed old parent verify button flow from examples.

## v5.8.23

- Final audit pass for parent verify and parent dashboard.
- Replaced all parent dashboard examples with the same working trimmed-entity dashboard.
- Confirmed parent verify uses `datetime.now()` and existing dashboard PIN.
- Confirmed service registration, button entity class, services.yaml, and dashboard entity IDs agree.
- Fixed example automation YAML multi-document formatting into a YAML list.

## v5.8.22

- Fixed parent verify runtime bug by replacing undefined `now()` calls with `datetime.now()`.
- Renamed parent verify button to trim cleanly as `button.parent_admin_verify`.
- Verified parent verify service registration and dashboard button press path.
- Added `examples/dashboard_parent_interface_working.yaml`.

## v5.8.21

- Fixed parent verify registration path.
- Updated parent dashboard to press `button.family_defcon_parent_admin_verify` instead of directly calling the service.
- Preserved 60 second parent verification window and existing dashboard keypad.

## v5.8.20

- Added explicit parent admin PIN verification step.
- Added `family_defcon.parent_admin_verify` service and `button.family_defcon_parent_admin_verify`.
- Parent admin verification lasts 60 seconds.
- Parent admin controls can now be used after pressing VERIFY PARENT PIN.
- Parent dashboard uses the existing working dashboard keypad.

## v5.8.19

- Parent admin actions now use the existing dashboard PIN as the primary PIN source.
- Parent dashboard reuses the existing working dashboard keypad services.
- Separate parent keypad services are no longer required for the recommended parent dashboard.
- Parent admin actions still require the entered PIN to belong to a configured parent role user.

## v5.8.18

- Fixed parent admin service registration so `family_defcon.parent_admin_keypress` and related services actually load.
- Preserved parent admin PIN keypad, parent role validation, hidden PIN state, and parent dashboard example.

## v5.8.17

- Added parent admin keypad services.
- Updated parent interface dashboard with launcher-style DEFCON status card.
- Parent interface now has PIN display, keypad, admin controls, and status summary.
- Preserved parent role PIN validation from v5.8.16.

## v5.8.16

- Added parent/admin hidden PIN entity.
- Added parent/admin PIN-protected control buttons for arm, disarm, clear all, enforce now, and cleanup targets.
- Added `examples/dashboard_parent_interface.yaml`.
- Parent admin actions require a configured user with role `parent`.
- Parent admin PIN is masked and not persisted.
- Preserved dynamic target fixes, cleanup service, hidden launch PIN state, instant PIN verification, and native HA events.

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
