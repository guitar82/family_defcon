# Family DEFCON

Family DEFCON is a Home Assistant custom integration for a family dashboard that can apply temporary WiFi timeouts through AdGuard Home.

The normal setup path is through the Home Assistant UI. YAML is optional and should only be used as a backup or advanced configuration method.

## What this integration does

Family DEFCON lets you:

```text
Create a family member list
Assign parent and child roles
Set hidden 4 digit PINs
Select dashboard targets
Launch temporary WiFi timeouts
Track DEFCON level, daily launches, and conflict chain
Apply AdGuard Home blocking rules
Expose launch events for automations, TTS, and sound effects
```

## Required Home Assistant pieces

Install these custom Lovelace cards if you want to use the example dashboards:

```text
button-card
```

Optional but recommended:

```text
layout-card
card-mod
```

The integration itself creates the entities used by the dashboard.

## Recommended setup method

Use the Home Assistant UI.

Go to:

```text
Settings → Devices & services → Add integration → Family DEFCON
```

After adding it, open:

```text
Settings → Devices & services → Family DEFCON → Configure
```

Use the configuration pages described below.

## Main configuration

### General settings

Set the basic behavior:

```text
Use UI config: on
Cooldown seconds
Daily launches before Mutual WiFi Destruction
Conflict chain before Mutual WiFi Destruction
Daily reset time
Maximum event log entries
```

Recommended starting values:

```text
Cooldown seconds: 30
Daily launches before Mutual WiFi Destruction: 5
Conflict chain before Mutual WiFi Destruction: 4
Daily reset time: 05:00:00
Maximum event log entries: 25
```

## People, PINs, and AdGuard clients

Create one entry per person.

Example:

```text
Mom
Dad
Henry
Marc
Maggie
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

### Roles

Use:

```text
parent
child
```

Parents can be used for Mom and Dad.

Children can be used for normal dashboard targets.

### PINs

PINs should be 4 digits.

The PIN field is hidden. PINs are stored as hashes, not plain text.

After changing PIN settings, save the options and reload or restart Home Assistant.

### Important PIN note

If you update from an older version and confirm feels slow, re-enter each PIN in the UI once. New PIN hashes are optimized for local 4 digit dashboard PIN use.

## Targets

There are three target-related settings:

```text
Default target
Parent target
Dashboard target
```

Use them like this:

```text
Default target: normal child targets
Parent target: Mom or Dad, if you want them selectable
Dashboard target: appears on the dashboard target buttons/select
```

A typical setup is:

```text
Henry: default target on, dashboard target on
Marc: default target on, dashboard target on
Maggie: default target on, dashboard target on
Mom: parent target on, dashboard target on
Dad: parent target on, dashboard target on
```

If you do not want Mom or Dad selectable from the dashboard, leave their dashboard target setting off.

## Stations and dashboard

The dashboard uses a station ID.

Recommended:

```text
dashboard
```

Use:

```text
Dashboard station ID: dashboard
Dashboard default target: Henry
```

If using physical terminals later, create more stations such as:

```text
kitchen
living_room
henry_room
marc_room
maggie_room
```

For a normal Home Assistant dashboard only, one station named `dashboard` is enough.

## AdGuard Home configuration

Family DEFCON expects AdGuard Home to already be running.

In AdGuard Home, create persistent clients for each family member.

The client names must match the names configured in Family DEFCON unless you override them in the UI.

Example:

```text
Mom
Dad
Henry
Marc
Maggie
```

Each AdGuard client should include the correct device IPs, MACs, or client identifiers.

In Family DEFCON, configure:

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

Recommended secrets:

```text
adguard_username
adguard_password
```

Store those in Home Assistant `secrets.yaml`.

Example:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

## Dashboard entities

The dashboard uses these entities:

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
```

## Example dashboards

The package includes example dashboard YAML files:

```text
examples/dashboard_launch_console.yaml
examples/dashboard_status_overview.yaml
```

Use them as separate dashboard cards or separate dashboard views.

### Launch console dashboard

Use this for:

```text
Target selection
PIN entry
Confirm
Launch
Cancel
Launch status text
Bad PIN warning
Lockout warning
```

### Status overview dashboard

Use this for:

```text
Current DEFCON level
Armed status
Daily launches
Conflict chain
Current WiFi status by person
Last event text
```

## Confirm and launch behavior

The dashboard flow is:

```text
Select target
Enter PIN
Press CONFIRM
If PIN is valid, target locks
Press LAUNCH
```

Confirm should only turn green when the entered PIN is valid.

If the PIN is wrong, the dashboard remains unconfirmed and the last event will show an invalid PIN or lockout warning.

The launch button sends the launch command without waiting for the entire AdGuard enforcement process, so the dashboard should respond quickly.

## Native Home Assistant events

Family DEFCON fires native Home Assistant events for automations.

Available events:

```text
family_defcon_launch
family_defcon_launch_rejected
family_defcon_bad_pin
family_defcon_pin_lockout
family_defcon_mutual_destruction
family_defcon_clear_all
```

### Launch event data

A launch event includes data like:

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

## TTS and sound effect example

Example automation:

```yaml
alias: Family DEFCON Launch Announcement
description: Announce Family DEFCON launches
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

Example bad PIN automation:

```yaml
alias: Family DEFCON Bad PIN Warning
description: Announce invalid dashboard PIN attempts
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

## Optional YAML backup configuration

The UI is the recommended configuration method.

YAML can be used as a backup or advanced configuration option. If you use UI config, do not also maintain conflicting YAML values.

Recommended backup file:

```text
/config/family_defcon.yaml
```

Example YAML backup:

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

### YAML backup warning

If you use UI configuration, old YAML values can cause confusion if both are active.

Recommended approach:

```text
Use UI config as the active configuration
Keep YAML only as a backup/reference
Do not paste old YAML into advanced override fields unless you intentionally want it to override UI settings
```

## Troubleshooting

### Confirm does not turn green

Check:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
binary_sensor.family_defcon_dashboard_target_confirmed
sensor.family_defcon_last_event
```

A correct PIN should confirm the target.

A wrong PIN should leave confirmation off and update the last event with an invalid PIN message.

### Launch feels slow

Re-enter each person’s PIN in the UI so the faster PIN hashes are used.

Also confirm that the launch button is using the current dashboard example or the non-blocking launch button behavior.

### Person does not block in AdGuard

Check:

```text
AdGuard client exists
AdGuard client name matches Family DEFCON
AdGuard base URL is correct
AdGuard username/password secrets are correct
DNS enabled is on
Enforcement mode is active
```

Run:

```yaml
action: family_defcon.enforce_now
```

Then check AdGuard to verify the rules were applied.

### Dashboard people do not show

Check:

```text
sensor.family_defcon_dashboard_people
```

It should have a `people` attribute containing configured people.

### Home Assistant custom integration warning

Home Assistant shows a warning for all custom integrations:

```text
This component might cause stability problems
```

That warning is normal and does not mean the integration is broken.

## Recommended first test

After configuration:

```text
1. Confirm Family DEFCON is armed
2. Select a child target
3. Enter a parent PIN
4. Press CONFIRM
5. Confirm turns green
6. Press LAUNCH
7. Check last event
8. Check AdGuard rules
9. Check WiFi status on the dashboard
```
