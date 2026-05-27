# Family DEFCON Release Notes

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
