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
