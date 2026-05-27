# Family DEFCON Release Notes

## v5.8.4

- Built from the stable v5.8.3 line.
- Added native Home Assistant events for launches, rejected launches, bad PINs, PIN lockouts, mutual destruction, and clear all.
- Added `examples/automation_event_announcements.yaml` for TTS and sound effects.
- Does not include v5.9 or v5.10 backend startup changes.

## v5.8.3

- Built from the stable v5.8.2 line.
- Reduced new UI PIN hash iterations from 200,000 to 10,000 for faster dashboard confirm and launch.
- Keeps PINs hidden and hashed in options.
- Requires re-entering each PIN in the UI to replace old slow hashes.
- Does not include v5.9 or v5.10 backend startup changes.

## v5.8.2

- Built directly from stable v5.8.
- Added example launch console and status overview dashboards.
- Fixed confirm button so it validates PIN before setting confirmed state.
- Wrong PIN now keeps dashboard confirmed state false.
- Launch button now calls launch_with_pin non-blocking for faster dashboard response.
- Does not include v5.9 or v5.10 backend startup changes.

## v5.8.0

- Added 4 character max validation for guided UI PIN entry.
- Added backend rejection for launch PINs longer than 4 characters.
- Added active config validation for people, targets, auth users, AdGuard clients, dashboard targets, and dashboard station.
- Dashboard launch button now uses configured dashboard station ID.
- Target select now filters through active config dashboard targets and people.
- Added `family_defcon.config_audit_status` diagnostic service.

## v5.7.0

- Fixed dashboard launches rejected as unknown station dashboard.
- Guaranteed dashboard station record exists during config normalization.
- Added station_record fallback for dashboard station.
- Migration now backfills the dashboard station into stations_list.
- Improved bad PIN diagnostics without exposing PIN values.

## v5.6.0

- Fixed Advanced raw YAML fields repopulating and overriding guided UI settings.
- Added `use_advanced_yaml_overrides` option.
- Added `clear_advanced_yaml_overrides` option.
- Advanced YAML is ignored unless explicitly enabled.
- `auth_config_status` now reports advanced override status.

## v5.5.0

- Fixed UI PIN changes not applying until manual reload/restart.
- Options updates now reload the integration automatically.
- Added `family_defcon.auth_config_status` diagnostic service.
- Reload config event now reports whether source is UI options or YAML.
- Changed daily launch limit, conflict chain limit, max event log, and max bad PIN attempts to number box selectors.

## v5.4.0

- Added `async_migrate_entry` to fix Home Assistant config entry migration errors.
- Migration preserves existing settings and adds missing guided UI defaults.
- Keeps hidden hashed PIN behavior from v5.3.
- Keeps config flow version stable at 4 for the guided UI series.

## v5.3.0

- Made guided UI PIN fields password/hidden fields.
- Plain PINs entered in the UI are hashed immediately and not stored.
- Existing PIN hashes are preserved when the new PIN field is left blank.
- Default demo PINs are stored as hashes in options instead of plain PINs.
- Updated labels to make the PIN field clearly write-only.

## v5.2.0

- Replaced confusing YAML-only config pages with guided fields.
- Added separate fields for each person, role, PIN, PIN hash, and AdGuard client name.
- Added per-person checkboxes for default target, parent target, and dashboard visibility.
- Added guided station fields.
- Fixed options menu labels so section names show properly.
- Kept Advanced raw YAML import as a power-user fallback.

## v5.1.0

- Moved almost all remaining variable settings into the UI Options flow.
- Added options menu sections for system, people/targets, PINs/roles, stations/dashboard, AdGuard, and penalties.
- Added UI YAML snippet support for people, auth users, stations, AdGuard clients, dashboard targets, and penalties.
- family_defcon.yaml remains as a fallback/backup config.
- UI config overrides YAML when `use_ui_config` is enabled.

## v5.0.0

- Added Options Flow for common settings.
- Added cooldown time as a UI editable option.
- Added PBKDF2-SHA256 hashed PIN support with legacy plain PIN fallback.
- Added `family_defcon.hash_pin` service.
- Added AdGuard status, last sync, last error, and managed rule count sensors.
- Added `family_defcon.migrate_entity_ids` service to rename old dashboard entity IDs when possible.
- Cleaned entity names for new installs while keeping unique IDs stable.
- Dashboard launch button now requires target confirmation before launch.
- Target selection clears confirmation.

## v4.9.0

- Fixed launch event messages to match the DEFCON severity calculation.
- Messages now use `current_defcon_level()` after timeouts are applied.
- Prevents messages like `DEFCON 4` when the active system condition is really DEFCON 3.
- Added helper functions in `__init__.py`: `active_block_count()` and `current_defcon_level()`.

## v4.8.0

- Fixed DEFCON level severity calculation.
- DEFCON level is now calculated from the worst active condition instead of the latest event only.
- Prevents DEFCON 3 from dropping back to DEFCON 4 while multiple people are still blocked.
- DEFCON 2 now acts as the warning state one step before Mutual WiFi Destruction.
- Person WiFi status sensors now respect `dns.mutual_destruction_scope: all`.

## v4.7.0

- Fixed `binary_sensor.dashboard_target_confirmed` not being created.
- `binary_sensor.py` now adds both Mutual WiFi Destruction and Dashboard Target Confirmed sensors during setup.
- This fixes the dashboard TARGET LOCKED visual state after pressing CONFIRM.

## v4.6.0

Documentation and package cleanup release.

- Rebuilt README from scratch for the current feature set.
- Updated HACS info page.
- Added release notes.
- Confirmed example dashboard references v4.5 target service.
- Confirmed dashboard PIN behavior is documented as 4 digits.
- Confirmed target confirmation state is documented.
- Confirmed troubleshooting section explains how to verify installed backend features.
- Confirmed repository structure documentation matches current files.

## v4.5.0

- Added `family_defcon.dashboard_select_target`.
- Target buttons call Family DEFCON directly instead of `select.select_option`.
- Selecting a target clears target confirmation.
- Dashboard target buttons remain visually polished with selected child targets blue and selected parent targets yellow.

## v4.4.0

- Dashboard PIN limited to 4 digits.
- Keypad stops accepting digits after 4.
- Manual PIN entry keeps first 4 digits.
- Clear, backspace, and set PIN reset target confirmation.
- Dashboard PIN tile updated to avoid clipping.

## v4.3.0

- Added dashboard target confirmed binary sensor.
- Confirm button sets the target confirmed state.
- Launch and cancel clear target confirmation.
- Dashboard can show TARGET LOCKED after confirm.

## v4.2.0

- Improved dashboard entity names.
- Dashboard entities use stable friendly names.

## v4.1.0

- Simplified config flow to fix UI setup errors.

## v4.0.0

- Added Home Assistant UI install support through config flow.

## Earlier v1 through v3

- Added HACS structure.
- Added dashboard entities.
- Added config driven dashboard people sensor.
- Added AdGuard Home set_rules enforcement.
