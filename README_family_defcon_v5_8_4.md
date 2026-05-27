# Family DEFCON

**Current stable build: v5.8.4 Stable Events**

Family DEFCON is a Home Assistant custom integration that creates a playful DEFCON style family WiFi timeout system. It lets configured users enter a 4 digit PIN, choose a target, confirm the target, and launch a WiFi timeout. Enforcement is handled through AdGuard Home custom filtering rules.

This README reflects the current stable line:

```text
v5.8.4
Base: stable v5.8.x
Includes: fast PIN hashing from v5.8.3 and native Home Assistant events from v5.8.4
Does not include: v5.9 or v5.10 startup/service changes
```

---

## Important current build notes

v5.8.4 is intentionally based on the last stable v5.8 line.

Do not mix dashboard code or backend expectations from v5.9 or v5.10. Those builds added different dashboard auth sensors and startup changes that are not part of this stable branch.

Do not use these v5.9-only sensors in your dashboard:

```text
sensor.family_defcon_dashboard_auth_status
sensor.family_defcon_dashboard_auth_message
sensor.family_defcon_dashboard_confirmed_by
```

Use these stable v5.8.4 entities instead:

```text
binary_sensor.family_defcon_dashboard_target_confirmed
sensor.family_defcon_last_event
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
```

---

## What this integration does

Family DEFCON provides:

```text
PIN based dashboard launches
Configurable people and roles
Configurable child/default targets and parent targets
Dashboard target selection
Target confirmation before launch
Bad PIN attempt tracking and lockout
Daily launch counter
Conflict chain tracking
Escalation rules
Mutual WiFi Destruction
AdGuard Home rule enforcement
Per person WiFi status sensors
Native Home Assistant events for automations, sounds, and TTS
```

---

## Installation through HACS

1. Open Home Assistant.
2. Open HACS.
3. Go to **Integrations**.
4. Open the three dot menu.
5. Choose **Custom repositories**.
6. Add your repository URL:

```text
https://github.com/guitar82/family_defcon
```

7. Select category **Integration**.
8. Install **Family DEFCON**.
9. Restart Home Assistant.

After restarting:

```text
Settings → Devices & services → Add integration → Family DEFCON
```

When prompted for the config file name, leave the default unless you intentionally want another file:

```text
family_defcon.yaml
```

You normally do not need this in `configuration.yaml` when using the UI integration:

```yaml
family_defcon:
```

If you already added that manually and also added the UI integration, remove the manual `configuration.yaml` entry to avoid duplicate setup.

---

## Configuration options

Family DEFCON can be configured two ways:

```text
Recommended: UI configuration
Optional/advanced: /config/family_defcon.yaml
```

### Recommended UI configuration

Go to:

```text
Settings → Devices & services → Family DEFCON → Configure
```

The options menu includes:

```text
People, PINs, and AdGuard clients
System and escalation settings
Stations and dashboard
AdGuard enforcement settings
Penalty time settings
Advanced raw YAML import
```

For the current stable build, make sure this is enabled on the System page:

```text
Use UI configuration instead of YAML = on
```

Then configure the People page and save.

### Required People settings

Each person should have:

```text
Name
Role: parent or child
New PIN: 4 digits
AdGuard client name
Default target checkbox, for children
Parent target checkbox, for parents
Dashboard target checkbox, if they should show as selectable
```

PINs are hidden and stored as hashes. v5.8.4 uses the faster v5.8.3 PIN hash behavior for newly saved PINs.

If you upgraded from an older build and confirm is slow, re-enter each PIN once:

```text
Settings → Devices & services → Family DEFCON → Configure
People, PINs, and AdGuard clients
Re-enter each 4 digit PIN
Save
Restart Home Assistant or run family_defcon.reload_config
```

Old hashes stay slow until the PINs are re-entered.

### Required dashboard settings

Go to:

```text
Settings → Devices & services → Family DEFCON → Configure → Stations and dashboard
```

Recommended values:

```text
Dashboard station ID = dashboard
Dashboard default target = one of your child/default targets
```

You should also have a station with:

```text
Station ID = dashboard
Station name = Home Assistant Dashboard
Station enabled = on
Key entity = blank, unless you intentionally require a key
```

If you see this message:

```text
Launch rejected. Unknown station dashboard.
```

check that the dashboard station exists and the dashboard station ID is exactly:

```text
dashboard
```

### AdGuard settings

Go to:

```text
Settings → Devices & services → Family DEFCON → Configure → AdGuard enforcement settings
```

Recommended values:

```text
Enable DNS enforcement = on
AdGuard Home URL = http://YOUR_ADGUARD_IP:3000
Enforcement mode = active
Mutual destruction scope = default_targets
AdGuard username secret = adguard_username
AdGuard password secret = adguard_password
AdGuard rule prefix = Family DEFCON Block
```

Add credentials to `/config/secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

AdGuard client names on the People page must match persistent client names in AdGuard Home.

---

## Optional YAML configuration

UI configuration is recommended. YAML can still be used as a portable backup or advanced configuration.

If using YAML, create:

```text
/config/family_defcon.yaml
```

Example:

```yaml
people:
  - Mom
  - Dad
  - Henry
  - Marc
  - Maggie

default_targets:
  - Henry
  - Marc
  - Maggie

parent_targets:
  - Mom
  - Dad

allow_parent_targets_default: false

auth:
  mode: pin
  pin_timeout_seconds: 60
  max_bad_pin_attempts: 3
  lockout_seconds_after_bad_pins: 120
  users:
    Mom:
      pin: "1111"
      role: parent
    Dad:
      pin: "2222"
      role: parent
    Henry:
      pin: "3333"
      role: child
    Marc:
      pin: "4444"
      role: child
    Maggie:
      pin: "5555"
      role: child

stations:
  dashboard:
    name: Home Assistant Dashboard
    enabled: true
    key_entity: ""

require_station_match: false
require_key_for_launch: false
cooldown_seconds: 30

launches_before_mutual_destruction: 5
chain_before_mutual_destruction: 4
daily_reset_time: "05:00:00"
max_event_log: 25

penalties:
  first_strike_target_minutes: 30
  retaliator_extra_minutes: 15
  retaliation_target_minutes: 30
  reattacker_extra_minutes: 15
  reattack_target_minutes: 45

dns:
  enabled: true
  provider: adguard_home
  enforcement_mode: active
  mutual_destruction_scope: default_targets

  adguard_home:
    base_url: "http://192.168.1.11:3000"
    username_secret: adguard_username
    password_secret: adguard_password
    username: ""
    password: ""
    rule_prefix: "Family DEFCON Block"
    clients:
      Mom:
        client_name: Mom
        enabled: true
      Dad:
        client_name: Dad
        enabled: true
      Henry:
        client_name: Henry
        enabled: true
      Marc:
        client_name: Marc
        enabled: true
      Maggie:
        client_name: Maggie
        enabled: true

dashboard:
  station_id: dashboard
  default_target: Henry
  targets:
    - Henry
    - Marc
    - Maggie
    - Mom
    - Dad
```

When using UI config, YAML can be empty or only used as a backup, but the UI option must be enabled:

```text
Use UI configuration instead of YAML = on
```

---

## Dashboard examples

The current ZIP includes these dashboard examples:

```text
examples/dashboard_launch_console.yaml
examples/dashboard_status_overview.yaml
examples/automation_event_announcements.yaml
```

The launch console example uses stable v5.8.4 entities only:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
binary_sensor.family_defcon_dashboard_target_confirmed
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
sensor.family_defcon_last_event
```

Recommended Lovelace dependencies:

```text
custom:button-card
```

Optional, depending on your layout:

```text
layout-card
```

---

## Entity reference

### Core sensors

```text
sensor.family_defcon_level
sensor.family_defcon_peace_status
sensor.family_defcon_daily_launches
sensor.family_defcon_conflict_chain
sensor.family_defcon_last_launcher
sensor.family_defcon_last_target
sensor.family_defcon_last_event
sensor.family_defcon_dashboard_people
```

### AdGuard health sensors

```text
sensor.family_defcon_adguard_status
sensor.family_defcon_adguard_last_sync
sensor.family_defcon_adguard_last_error
sensor.family_defcon_adguard_managed_rule_count
```

### Per person sensors

For each configured person, Family DEFCON creates WiFi status and minutes remaining sensors. The exact entity IDs are based on the person names.

Examples:

```text
sensor.henry_wifi_status
sensor.henry_wifi_minutes_remaining
sensor.marc_wifi_status
sensor.marc_wifi_minutes_remaining
```

### Switches

```text
switch.family_defcon_command_system_armed
switch.family_defcon_allow_parent_targets
```

### Binary sensors

```text
binary_sensor.family_defcon_mutual_wifi_destruction
binary_sensor.family_defcon_dashboard_target_confirmed
```

### Dashboard entities

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
```

---

## Services

### Launch services

```yaml
action: family_defcon.launch
data:
  launcher: Dad
  target: Henry
  station: dashboard
```

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "2222"
  target: Henry
  station: dashboard
```

### Dashboard keypad services

```yaml
action: family_defcon.dashboard_keypress
data:
  digit: "1"
```

```yaml
action: family_defcon.dashboard_backspace
```

```yaml
action: family_defcon.dashboard_clear_pin
```

```yaml
action: family_defcon.dashboard_set_pin
data:
  pin: "2222"
```

```yaml
action: family_defcon.dashboard_select_target
data:
  target: Henry
```

### Control services

```yaml
action: family_defcon.clear_all
```

```yaml
action: family_defcon.stand_down
```

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

```yaml
action: family_defcon.set_parent_targets
data:
  enabled: true
```

```yaml
action: family_defcon.enforce_now
```

```yaml
action: family_defcon.reload_config
```

```yaml
action: family_defcon.block_person
data:
  person: Henry
```

```yaml
action: family_defcon.unblock_person
data:
  person: Henry
```

### Diagnostic services

```yaml
action: family_defcon.auth_config_status
```

```yaml
action: family_defcon.config_audit_status
```

These diagnostics log useful information to `sensor.family_defcon_last_event` without exposing the actual PIN values.

---

## Native Home Assistant events

v5.8.4 adds native Home Assistant events for automations.

### Events exposed

```text
family_defcon_launch
family_defcon_launch_rejected
family_defcon_bad_pin
family_defcon_pin_lockout
family_defcon_mutual_destruction
family_defcon_clear_all
```

### Launch event data

A `family_defcon_launch` event includes data like:

```yaml
launcher: Dad
target: Henry
station: dashboard
defcon_level: 4
daily_launches: 1
conflict_chain: 1
kind: launch
minutes: 30
mutual_destruction: false
message: DEFCON 4. Dad launched at Henry. Henry receives 30 minute timeout.
```

Possible `kind` values:

```text
launch
retaliation
escalation
```

### Example launch announcement automation

```yaml
alias: Family DEFCON Launch Event Announcement
description: Announce Family DEFCON launches from the native event.
mode: queued

trigger:
  - platform: event
    event_type: family_defcon_launch

action:
  - service: media_player.play_media
    target:
      entity_id: media_player.kitchen_speaker
    data:
      media_content_id: media-source://media_source/local/defcon_launch.mp3
      media_content_type: audio/mpeg

  - delay: "00:00:02"

  - service: tts.cloud_say
    target:
      entity_id: media_player.kitchen_speaker
    data:
      message: >
        Family DEFCON {{ trigger.event.data.defcon_level }}.
        {{ trigger.event.data.launcher }} launched at {{ trigger.event.data.target }}.
        {{ trigger.event.data.target }} receives {{ trigger.event.data.minutes }} minutes.
```

Put your sound file in Home Assistant media, or adjust the media path for your setup.

### Example bad PIN warning

```yaml
alias: Family DEFCON Bad PIN Warning
mode: single

trigger:
  - platform: event
    event_type: family_defcon_bad_pin

action:
  - service: tts.cloud_say
    target:
      entity_id: media_player.kitchen_speaker
    data:
      message: >
        Invalid Family DEFCON PIN.
        Attempt {{ trigger.event.data.attempts }} of {{ trigger.event.data.max_attempts }}.
```

### Example mutual destruction announcement

```yaml
alias: Family DEFCON Mutual Destruction Announcement
mode: single

trigger:
  - platform: event
    event_type: family_defcon_mutual_destruction

action:
  - service: tts.cloud_say
    target:
      entity_id: media_player.kitchen_speaker
    data:
      message: >
        Warning. Mutual WiFi destruction has been activated.
```

---

## Confirm and launch behavior

The stable v5.8.4 dashboard flow is:

```text
Select target
Enter 4 digit PIN
Press CONFIRM
If PIN is valid, binary_sensor.family_defcon_dashboard_target_confirmed turns on
Press LAUNCH
Launch is sent non-blocking so the dashboard responds quickly
```

Confirm should only turn green when:

```text
binary_sensor.family_defcon_dashboard_target_confirmed = on
```

Wrong PIN behavior:

```text
Confirm does not turn green
sensor.family_defcon_last_event shows invalid PIN or lockout warning
Bad PIN attempts increment
Terminal locks after the configured number of bad attempts
```

---

## Fast PIN behavior

v5.8.4 includes the v5.8.3 fast PIN update.

New PINs saved in the UI use:

```text
PBKDF2-SHA256 with 10,000 iterations
```

This is intentionally faster than the earlier 200,000 iteration setting because dashboard PINs are only 4 digits and the goal is to hide them from casual viewing, not provide high-security password storage.

After upgrading from an older build, re-enter each PIN once in the UI to replace old slow hashes.

---

## AdGuard Home requirements

Family DEFCON expects AdGuard Home persistent clients to exist.

Example client names:

```text
Mom
Dad
Henry
Marc
Maggie
```

These names must match the AdGuard client names configured on the Family DEFCON People page.

Family DEFCON manages custom filtering rules using a marked block. Do not manually edit inside the managed block.

---

## Common troubleshooting

### Custom integration warning

This Home Assistant warning is normal for custom integrations:

```text
We found a custom integration family_defcon which has not been tested by Home Assistant.
```

It is not an error.

### Confirm is slow

Re-enter each PIN in the UI so it gets a new v5.8.3/v5.8.4 fast hash.

### Confirm does not turn green

Check:

```text
binary_sensor.family_defcon_dashboard_target_confirmed
sensor.family_defcon_last_event
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
```

Common causes:

```text
Wrong PIN
PIN was not re-entered after upgrade
Target is protected
Dashboard station mismatch
Command system is disarmed
```

### Launch rejected, unknown station dashboard

Set this in the UI:

```text
Dashboard station ID = dashboard
```

And make sure a station exists with ID:

```text
dashboard
```

### AdGuard does not block

Check:

```text
sensor.family_defcon_adguard_status
sensor.family_defcon_adguard_last_error
sensor.family_defcon_adguard_last_sync
sensor.family_defcon_adguard_managed_rule_count
```

Then run:

```yaml
action: family_defcon.enforce_now
```

### UI config not applying

Run:

```yaml
action: family_defcon.config_audit_status
```

Then check:

```text
sensor.family_defcon_last_event
```

Make sure:

```text
Use UI configuration instead of YAML = on
Advanced YAML overrides = off
```

---

## Backup recommendation

Before replacing the custom integration folder, back up:

```text
/config/custom_components/family_defcon
/config/family_defcon.yaml
/config/secrets.yaml
```

Example terminal backup:

```bash
cd /config
mkdir -p family_defcon_backups
tar -czf family_defcon_backups/family_defcon_backup_$(date +%Y%m%d_%H%M%S).tar.gz custom_components/family_defcon family_defcon.yaml secrets.yaml
```

---

## Current stable file list

Important files in this build:

```text
custom_components/family_defcon/__init__.py
custom_components/family_defcon/config_flow.py
custom_components/family_defcon/sensor.py
custom_components/family_defcon/switch.py
custom_components/family_defcon/binary_sensor.py
custom_components/family_defcon/text.py
custom_components/family_defcon/select.py
custom_components/family_defcon/button.py
custom_components/family_defcon/services.yaml
examples/dashboard_launch_console.yaml
examples/dashboard_status_overview.yaml
examples/automation_event_announcements.yaml
```

---

## Version history summary

```text
v5.8.2
Stable Plus. Confirm validates PIN before turning green. Launch is non-blocking.

v5.8.3
Stable Fast PINs. New UI PIN hashes use 10,000 PBKDF2 iterations.

v5.8.4
Stable Events. Adds native Home Assistant events for launch, bad PIN, lockout, mutual destruction, and clear all.
```

v5.8.4 is the current recommended stable build.
