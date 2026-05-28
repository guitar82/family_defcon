# Family DEFCON

Family DEFCON is a Home Assistant custom integration for a family dashboard that can apply temporary WiFi timeouts through AdGuard Home.

The recommended setup is through the Home Assistant UI. YAML is optional and should only be used as a backup or advanced configuration method.

## What it does

Family DEFCON lets you:

```text
Create family members from the UI
Assign parent and child roles
Set hidden 4 digit PINs
Select targets from a dashboard
Confirm a valid PIN before launch
Apply temporary AdGuard Home WiFi timeouts
Track DEFCON level, daily launches, and conflict chain
Trigger Home Assistant automations from native events
Play TTS or sound effects when launches happen
```

## Recommended install path

Use the UI.

```text
Settings → Devices & services → Add integration → Family DEFCON
```

Then configure it:

```text
Settings → Devices & services → Family DEFCON → Configure
```

## Required frontend cards

For the recommended dynamic dashboard, install these HACS frontend cards:

```text
button-card
auto-entities
```

Optional:

```text
layout-card
card-mod
```

## UI configuration checklist

### 1. General settings

Recommended starting values:

```text
Use UI config: on
Cooldown seconds: 30
Daily launches before Mutual WiFi Destruction: 5
Conflict chain before Mutual WiFi Destruction: 4
Daily reset time: 05:00:00
Maximum event log entries: 25
```

### 2. People, roles, PINs, and AdGuard clients

Create one entry per person.

Example:

```text
Parent 1
Parent 2
Child 1
Child 2
Child 3
```

For each person, configure:

```text
Name
Role
New PIN
AdGuard client name
Default target
Parent target
Dashboard target
```

Use roles:

```text
parent
child
```

PINs should be 4 digits.

PINs are hidden and saved as hashes. The dashboard PIN entity exposes masked bullets only, not the raw PIN.

### 3. Targets

Typical setup:

```text
Children: Default target on, Dashboard target on
Parents: Parent target on, Dashboard target optional
```

Only people marked as dashboard targets will appear as target buttons on the dynamic launch console.

### 4. Dashboard station

Recommended:

```text
Dashboard station ID: dashboard
Dashboard default target: Child 1
```

A single station named `dashboard` is enough for normal Home Assistant dashboard use.

### 5. AdGuard Home

Family DEFCON expects AdGuard Home to already be running.

In AdGuard Home, create persistent clients for each configured person. The AdGuard client names must match the names configured in Family DEFCON unless you override them in the UI.

Configure:

```text
DNS enabled: on
Provider: AdGuard Home
AdGuard base URL
Username secret
Password secret
Rule prefix
Enforcement mode
Mutual destruction scope
```

Example base URL:

```text
http://192.168.1.11:3000
```

Recommended `secrets.yaml` entries:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

## Recommended dashboard examples

Use these files from the `examples` folder:

```text
examples/dashboard_launch_console_dynamic_targets.yaml
examples/dashboard_status_overview.yaml
examples/automation_event_announcements.yaml
```

The dynamic launch console uses generated target entities:

```text
button.family_defcon_select_target_*
```

Those buttons are created from the UI dashboard target list. If you change people or dashboard targets, reload Family DEFCON or restart Home Assistant.

## Dashboard entities

Common entities used by the dashboards:

```text
sensor.family_defcon_level
sensor.family_defcon_peace_status
sensor.family_defcon_last_event
sensor.family_defcon_last_launcher
sensor.family_defcon_last_target
sensor.family_defcon_daily_launches
sensor.family_defcon_conflict_chain
sensor.family_defcon_dashboard_people
switch.family_defcon_command_system_armed
binary_sensor.family_defcon_dashboard_target_confirmed
binary_sensor.family_defcon_mutual_wifi_destruction
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
button.family_defcon_select_target_*
```

## Dashboard flow

```text
Select target
Enter PIN
Press CONFIRM
If PIN is valid, target locks
Press LAUNCH
```

Confirm should only turn green after a valid PIN.

If the PIN is wrong, the target remains unconfirmed and the last event shows an invalid PIN or lockout message.

## Native Home Assistant events

Family DEFCON fires these events:

```text
family_defcon_launch
family_defcon_launch_rejected
family_defcon_bad_pin
family_defcon_pin_lockout
family_defcon_mutual_destruction
family_defcon_clear_all
```

Example launch event data:

```yaml
launcher: Parent 1
target: Child 1
station: dashboard
defcon_level: 4
daily_launches: 1
conflict_chain: 1
kind: launch
minutes: 30
mutual_destruction: false
message: DEFCON 4. Parent 1 launched at Child 1. Child 1 receives 30 minute timeout.
```

## TTS example

```yaml
alias: Family DEFCON Launch Announcement
mode: queued

trigger:
  - platform: event
    event_type: family_defcon_launch

action:
  - service: tts.cloud_say
    target:
      entity_id: media_player.kitchen_speaker
    data:
      message: >
        Family DEFCON {{ trigger.event.data.defcon_level }}.
        {{ trigger.event.data.launcher }} launched at {{ trigger.event.data.target }}.
        {{ trigger.event.data.target }} receives {{ trigger.event.data.minutes }} minutes.
```

## Optional YAML backup

The UI is the recommended configuration method.

A YAML backup example is included here:

```text
docs/family_defcon_yaml_backup_example.yaml
family_defcon.yaml
```

The example YAML does not include active demo PINs. Configure PINs in the UI.

Do not keep conflicting UI config and YAML overrides active at the same time unless you intentionally want one to override the other.

## Privacy note

The dashboard PIN text entity exposes masked bullets only.

Recommended recorder exclusion:

```yaml
recorder:
  exclude:
    entities:
      - text.family_defcon_dashboard_pin
```

## First test checklist

```text
1. Confirm Family DEFCON is armed
2. Select a child target from the dynamic target buttons
3. Enter a parent PIN
4. Press CONFIRM
5. Confirm turns green
6. Press LAUNCH
7. Check sensor.family_defcon_last_event
8. Check AdGuard rules
9. Check WiFi status on the dashboard
```

## Troubleshooting

### Dynamic target buttons do not show

Check that `auto-entities` is installed.

Then verify entities exist:

```text
button.family_defcon_select_target_*
```

If not, reload Family DEFCON or restart Home Assistant after changing dashboard targets.

### Confirm does not turn green

Check:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
binary_sensor.family_defcon_dashboard_target_confirmed
sensor.family_defcon_last_event
```

### Confirm feels slow

Re-enter each person’s PIN in the UI so the fast hash format is used.

### AdGuard does not block a person

Check:

```text
AdGuard persistent client exists
AdGuard client name matches Family DEFCON
AdGuard base URL is correct
AdGuard secrets are correct
DNS enabled is on
Enforcement mode is active
```

Run:

```yaml
action: family_defcon.enforce_now
```

### Home Assistant custom integration warning

Home Assistant shows a warning for custom integrations. That warning is normal and does not mean Family DEFCON is broken.


## v5.8.10 Dynamic Button Entity ID Fix

v5.8.10 fixes dynamic target button entity IDs for new installs.

The generated target buttons now explicitly request entity IDs like:

```text
button.family_defcon_select_target_child_1
button.family_defcon_select_target_parent_1
```

This makes the dynamic dashboard filter reliable:

```text
button.family_defcon_select_target_*
```

After installing or updating:

```text
Restart Home Assistant
Search Developer Tools → States for family_defcon_select_target
```

If Home Assistant previously created different entity IDs for the same unique IDs, delete the old Family DEFCON target button entities from the entity registry or remove/re-add the integration.


## v5.8.11 Pre-release audit fixes

This build fixes issues found during a full package audit before UI polish work.

Fixes:

```text
Deterministic suggested_object_id added to core dashboard entities
Person WiFi status/minutes sensors now use deterministic family_defcon-prefixed entity IDs
sensor.family_defcon_dashboard_people now points to those deterministic person sensor IDs
Dynamic target button entities expose target metadata as attributes
Dynamic target dashboard uses entity.attributes.target instead of parsing friendly names
select.family_defcon_dashboard_target now dispatches updates when changed from the dropdown
```

Expected entity IDs on a clean install include:

```text
sensor.family_defcon_dashboard_people
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_select_target_child_1
sensor.family_defcon_child_1_wifi_status
sensor.family_defcon_child_1_wifi_minutes_remaining
```

If upgrading from an older test build, old entity IDs may remain in Home Assistant's entity registry. Remove the old Family DEFCON entities from Settings → Devices & services → Entities, or remove/re-add the integration, then restart Home Assistant.


## v5.8.12 Privacy and Config Reload Fixes

v5.8.12 fixes several pre-release audit items:

```text
Live dashboard PIN is never saved to persistent storage
Dashboard confirmed state is never restored after restart
UI options save now applies reload_config when possible
People/target changes still require restart so generated entities can be recreated
Dashboard target checkbox defaults now respect saved UI settings
Legacy dashboard PIN helper now supports hashed PINs
hash_pin service description now matches the current fast SHA256 hash format
```

After changing people names or dashboard target membership in the UI, restart Home Assistant.


## v5.8.13 Cleanup Service

v5.8.13 adds a built in cleanup service for old generated target button entity IDs.

Run from Developer Tools → Actions:

```yaml
action: family_defcon.cleanup_target_button_entities
data:
  remove_old_select_target: true
  remove_family_defcon_target_buttons: true
```

This removes stale registry entries such as:

```text
button.select_target_dad
button.select_target_child_1
button.family_defcon_select_target_child_1
```

Then restart Home Assistant so the current dynamic target buttons are recreated as:

```text
button.family_defcon_select_target_*
```

The service does not delete Family DEFCON configuration.


## v5.8.14 Clean Install Fix

v5.8.14 fixes cleanup action registration and makes install/upgrade behavior less fragile.

Changes:

```text
cleanup_target_button_entities action registers correctly during setup
Old button.select_target_* entries are cleaned automatically on startup
Manual cleanup action is available from Developer Tools > Actions
Dynamic dashboard matches both button.family_defcon_select_target_* and old button.select_target_* IDs
Added a basic fallback dashboard that does not require auto-entities
```

Manual cleanup action:

```yaml
action: family_defcon.cleanup_target_button_entities
data:
  remove_old_select_target: true
  remove_family_defcon_target_buttons: false
```

Use this fallback dashboard if auto-entities is not installed:

```text
examples/dashboard_launch_console_basic_no_auto_entities.yaml
```


## v5.8.15 Target Button Entity Name Fix

v5.8.15 fixes generated target button entity IDs on clean installs by making the dynamic target button entity name deterministic, not just the suggested object ID.

Expected clean install target buttons:

```text
button.family_defcon_select_target_child_1
button.family_defcon_select_target_parent_1
```

For upgraded/test installs that still have old IDs, the dynamic target button example supports:

```text
button.select_target_*
button.family_defcon_select_target_*
```

New helper example:

```text
examples/dashboard_dynamic_target_buttons_only.yaml
```


## v5.8.16 Parent PIN Admin Controls

v5.8.16 adds a separate parent/admin interface protected by parent PIN validation.

New hidden parent PIN entity:

```text
text.family_defcon_parent_admin_pin
```

New parent-admin buttons:

```text
button.family_defcon_parent_admin_clear_all
button.family_defcon_parent_admin_enforce_now
button.family_defcon_parent_admin_arm
button.family_defcon_parent_admin_disarm
button.family_defcon_parent_admin_cleanup_targets
```

These buttons only work if the entered PIN belongs to a configured user with role `parent`.

New example dashboard:

```text
examples/dashboard_parent_interface.yaml
```

The parent admin PIN is masked as entity state and is never persisted to storage.


## v5.8.17 Parent Interface Keypad

v5.8.17 adds keypad services for the parent interface and updates the parent dashboard.

New services:

```text
family_defcon.parent_admin_keypress
family_defcon.parent_admin_backspace
family_defcon.parent_admin_clear_pin
```

The parent dashboard now includes:

```text
Launcher-style DEFCON status card
Parent PIN display
Parent PIN keypad
PIN-protected parent control buttons
Status summary
```

Updated example:

```text
examples/dashboard_parent_interface.yaml
```


## v5.8.18 Parent Admin Service Registration Fix

v5.8.18 fixes service registration for parent admin controls.

This makes these actions available in Home Assistant:

```text
family_defcon.parent_admin_keypress
family_defcon.parent_admin_backspace
family_defcon.parent_admin_clear_pin
family_defcon.parent_admin_arm
family_defcon.parent_admin_disarm
family_defcon.parent_admin_clear_all
family_defcon.parent_admin_enforce_now
family_defcon.parent_admin_cleanup_targets
```

Install the package and restart Home Assistant Core.


## v5.8.19 Parent Uses Existing Keypad

v5.8.19 simplifies the parent dashboard by reusing the existing working dashboard keypad.

Parent dashboard now uses:

```text
text.family_defcon_dashboard_pin
family_defcon.dashboard_keypress
family_defcon.dashboard_backspace
family_defcon.dashboard_clear_pin
```

Parent admin actions verify that the entered dashboard PIN belongs to a configured user with role `parent`.

This avoids needing separate parent keypad services.

Updated examples:

```text
examples/dashboard_parent_interface.yaml
examples/dashboard_parent_interface_existing_keypad.yaml
```


## v5.8.20 Parent PIN Verify Step

v5.8.20 adds an explicit parent PIN verification step.

Flow:

```text
Enter PIN with the existing dashboard keypad
Press VERIFY PARENT PIN
Backend validates the PIN belongs to a parent role user
Parent admin is verified for 60 seconds
Press Clear All / Enforce / Arm / Disarm / Cleanup
```

New action and button:

```text
family_defcon.parent_admin_verify
button.family_defcon_parent_admin_verify
```

Updated dashboard:

```text
examples/dashboard_parent_interface_with_verify.yaml
```


## v5.8.21 Parent Verify Button Fix

v5.8.21 registers the parent verify action and updates the dashboard to press the verify button entity.

Use this dashboard flow:

```text
Enter PIN
Press VERIFY PARENT PIN
Use parent controls within 60 seconds
```

The dashboard calls:

```text
button.press -> button.family_defcon_parent_admin_verify
```

instead of directly calling `family_defcon.parent_admin_verify`.


## v5.8.22 Verified Parent Fix

v5.8.22 fixes the parent verify runtime bug and normalizes the verify button name.

Fixes:

```text
Replaced undefined now() calls with datetime.now()
Verify button name now trims to button.parent_admin_verify
Parent verify service registration verified
Parent admin actions use the existing dashboard PIN first
Updated working parent dashboard example
```

Use:

```text
examples/dashboard_parent_interface_working.yaml
```


## v5.8.23 Final Parent Audit

Use this parent dashboard only:

```text
examples/dashboard_parent_interface_working.yaml
```

The parent dashboard intentionally uses the existing working launch keypad:

```text
text.family_defcon_dashboard_pin
family_defcon.dashboard_keypress
family_defcon.dashboard_backspace
family_defcon.dashboard_clear_pin
```

It uses trimmed parent admin button entity IDs, matching Home Assistant behavior on the current install:

```text
button.parent_admin_verify
button.parent_admin_arm
button.parent_admin_disarm
button.parent_admin_clear_all
button.parent_admin_enforce_now
button.parent_admin_cleanup_targets
```

Flow:

```text
Enter parent PIN
Press VERIFY PARENT PIN
Use parent controls within 60 seconds
```


## v5.8.24 Parent Launcher Style Rebuild

v5.8.24 rebuilds the parent terminal to mirror the working launcher flow.

Flow:

```text
Enter PIN with existing dashboard keypad
Press CONFIRM
binary_sensor.parent_admin_confirmed turns on
Use parent controls for the configured PIN timeout window
Press CANCEL to clear confirmation
```

New parent confirmation entities:

```text
button.parent_admin_confirm
button.parent_admin_cancel
binary_sensor.parent_admin_confirmed
sensor.parent_admin_confirmed_by
sensor.parent_admin_status
```

The parent terminal no longer uses the separate parent keypad system or the old verify button flow.


## v5.8.25 Parent Import Fix

v5.8.25 fixes the parent launcher-style rebuild so Home Assistant can actually load the new parent status entities.

Fixes:

```text
ParentAdminConfirmedBinarySensor now extends BinarySensorEntity directly
binary_sensor.py imports datetime
ParentAdminConfirmedBinarySensor is added to async_setup_platform
ParentAdminConfirmedBySensor and ParentAdminStatusSensor now extend existing Base
Parent admin sensors are added to sensor async_setup_platform
Dashboard keeps launcher-style flow: PIN -> CONFIRM -> admin buttons
```


## v5.8.26 Examples Archived

v5.8.26 archives older dashboard examples that referenced stale parent keypad, verify, or entity naming flows.

Use the current parent dashboard:

```text
examples/dashboard_parent_interface_launcher_style.yaml
```

Compatibility copies are also kept visible:

```text
examples/dashboard_parent_interface.yaml
examples/dashboard_parent_interface_working.yaml
```

Older examples are moved to:

```text
examples/_archive_old_examples/
```


## v5.8.27 Parent Terminal Fixed

This rebuild fixes the parent terminal by using the launcher pattern exactly.

Expected entity IDs:

```text
button.parent_admin_confirm
button.parent_admin_cancel
button.parent_admin_arm
button.parent_admin_disarm
button.parent_admin_clear_all
button.parent_admin_enforce_now
button.parent_admin_cleanup_targets
binary_sensor.parent_admin_confirmed
sensor.parent_admin_confirmed_by
sensor.parent_admin_status
```

Flow:

```text
Enter PIN with existing dashboard keypad
Press CONFIRM
binary_sensor.parent_admin_confirmed turns on
Use parent admin buttons
```


## v5.8.28 Parent Confirm Direct Service

This build makes the parent CONFIRM button call the integration service directly:

```text
family_defcon.parent_admin_confirm
```

This bypasses the Home Assistant button entity layer for confirm/cancel, while keeping the parent action buttons as normal button entities.

Flow:

```text
Enter PIN
Press CONFIRM
Dashboard calls family_defcon.parent_admin_confirm directly
Parent session is set
Use parent admin buttons
```


## v5.8.29 Confirm Registration Fix

v5.8.29 fixes the missing `family_defcon.parent_admin_confirm` action.

Fixes:

```text
Registers parent_admin_confirm beside the existing working dashboard keypad services
Registers parent_admin_cancel beside the existing working dashboard keypad services
CONFIRM dashboard button calls family_defcon.parent_admin_confirm directly
CANCEL dashboard button calls family_defcon.parent_admin_cancel directly
Scans registered parent services against services.yaml
Scans dashboard examples for stale parent verify/keypad references
```


## v5.8.30 Confirm Reload Safe

v5.8.30 fixes the case where Home Assistant reloads the config entry while
`hass.data[DOMAIN]["setup_complete"]` is already true. In that case the full
`async_setup` service registration block can be skipped, causing new actions like
`family_defcon.parent_admin_confirm` and `family_defcon.parent_admin_cancel` to be missing.

This build registers those two actions from a module-level fallback during both:

```text
async_setup_entry reload path
full async_setup path
```


## v5.8.31 Confirm Hard Fix

v5.8.31 rebuilds parent confirm registration in the same async_setup service block as the working dashboard keypad services.

It also changes async_setup_entry so an existing setup_complete flag does not skip the new service registration after an update.

Use the included installer script from HA Terminal to avoid extracting the zip into the wrong folder:

```bash
bash /config/INSTALL_FROM_HA_TERMINAL.sh
ha core restart
```


## v5.8.32 GitHub Confirm Fix

This build is intended for GitHub/HACS loading.

The parent confirm/cancel actions are registered directly in the same async_setup service registration block as the working dashboard keypad services:

```text
family_defcon.parent_admin_confirm
family_defcon.parent_admin_cancel
```

The config-entry setup path no longer returns early when `setup_complete` is already true. This allows updated GitHub code to register newly added services after a HACS update and HA restart.


## v1.0.0 Stable

This is the first stable release of Family DEFCON.

Stable baseline:

```text
Launcher dashboard works
Parent command interface works
Parent CONFIRM action works
Parent admin buttons work
Dynamic target buttons work
Existing dashboard keypad is used for launcher and parent PIN entry
Old parent verify flow removed
Old parent_admin_keypress dashboard dependency removed
Parent dashboard uses family_defcon.parent_admin_confirm directly
```

Recommended parent dashboard:

```text
examples/dashboard_parent_interface.yaml
```

Recommended launcher dashboard:

```text
examples/dashboard_launch_console_dynamic_targets.yaml
```


## v1.0.0 Stable Examples

The examples folder is intentionally limited to four files:

```text
dashboard_parent_interface.yaml
dashboard_launch_console_dynamic_targets.yaml
dashboard_status_overview.yaml
automation_event_announcements.yaml
```


## v1.0.1 UI AdGuard Fix

Fixes UI-only AdGuard configuration not reaching the active runtime enforcement config.

What changed:

```text
AdGuard base URL is forced from UI options before every enforcement run
AdGuard provider is set to adguard_home when AdGuard URL is configured
AdGuard enabled/mode are refreshed from UI options
AdGuard client names are refreshed from UI options
Added family_defcon.adguard_config_status action
```

To test:

```yaml
action: family_defcon.adguard_config_status
```

Then check:

```text
sensor.family_defcon_last_event
```


## v1.0.2 AdGuard Diagnostics

Adds a backup diagnostic action that creates a Home Assistant persistent notification:

```yaml
action: family_defcon.debug_status
```

This is useful if `sensor.family_defcon_last_event` is blank or not updating.


## v1.0.3 UI AdGuard Mapping Fix

Fixes UI AdGuard settings by mapping them into the exact same runtime structure as the working advanced YAML `dns:` block.

If `adguard_base_url` is set in the UI, the integration now builds:

```yaml
dns:
  enabled: true
  provider: adguard_home
  enforcement_mode: active
  adguard_home:
    base_url: ...
    username_secret: ...
    password_secret: ...
    rule_prefix: ...
    clients:
      Person:
        client_name: ...
        enabled: true
```

Test after restart:

```yaml
action: family_defcon.adguard_config_status
```

Then check `sensor.family_defcon_last_event` or Notifications.


## v1.0.4 Dashboard Status Fix

Fixes the status overview dashboard showing users online when they are blocked.

The backend `sensor.family_defcon_dashboard_people` now includes direct snapshot values for each person:

```text
status
blocked
minutes_remaining
```

The dashboard no longer has to guess or look up per-person status entity IDs.


## v1.0.5 Case Safe Status Fix

Fixes the dashboard showing users online when a timeout exists under a differently cased name.

Example fixed:

```text
Last event: Dad launched at Henry
Dashboard people list: henry
blocked_until key: Henry
```

The dashboard people sensor now matches blocked status case-insensitively.


## v1.0.6 Status State Fix

Fixes remaining status issues where launch/enforcement works but dashboard people still show online.

Changes:

```text
Restores saved blocked_until values case-insensitively
Preserves active timeouts during reload_config even when name case changed
Canonicalizes launcher and target names during launch
Writes timeouts using configured person names
Person WiFi Status and Minutes Remaining sensors now use case-insensitive blocked_until lookup
Dashboard People still exposes direct blocked/status/minutes_remaining attributes
```


## v1.0.7 Audit Patch

This audit patch hardens the current release candidate after reviewing the service registration, status sensors, reload behavior, AdGuard UI mapping, and diagnostics.

Fixes included:

```text
All status sensors now share the same case safe blocked/allowed calculation
DEFCON level now uses the same case safe status calculation as the people dashboard
Dashboard People attributes include active_block_count and blocked_until_keys for debugging
Per person status sensors expose blocked/minutes/status attributes
Config entry reload no longer reruns full platform setup when already loaded
AdGuard username/password secret fields can also work as literal values if no matching secret exists
Fixed a LOGGER typo in debug notification error handling
Updated stale debug version text
```


## v1.0.8 AdGuard Connection Fix

Focused patch for UI to AdGuard connection handling.

Fixes and hardening:

```text
Normalizes AdGuard URL from UI or YAML
Accepts IP/host without http:// by assuming http://
Strips accidental /control path from the base URL
Allows UI credential fields to work as secrets or literal values
Adds family_defcon.adguard_connection_test action
Improves AdGuard error messages with sanitized endpoint and HTTP status
```

Test after restart:

```yaml
action: family_defcon.adguard_config_status
```

Then:

```yaml
action: family_defcon.adguard_connection_test
```


## v1.0.9 Loader Config Fix

Fixes new actions not appearing after HACS/GitHub updates and UI config changes not applying.

Changes:

```text
async_setup_entry always runs async_setup after config entry load
Service registration is idempotent and replaces old in-memory services
Periodic timer is replaced instead of duplicated
Entity platforms are loaded only once
Option saves re-run setup so services and UI config mapping refresh
Live blocked_until state is preserved during in-process setup reruns
```

This directly addresses actions such as:

```text
family_defcon.adguard_connection_test
family_defcon.adguard_config_status
```

not appearing after an update.
