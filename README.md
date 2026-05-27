# Family DEFCON

**Current release: v4.0 UI Install Ready**

Family DEFCON is a Home Assistant custom integration that creates a playful DEFCON style family WiFi timeout system.

It supports PIN based launches, configurable people and stations, AdGuard Home enforcement, a dashboard keypad, and escalation rules that can trigger Mutual WiFi Destruction.

## Features

- PIN based launch authentication
- Any person can use any configured station
- Config driven people, targets, PINs, stations, penalties, dashboard targets, and AdGuard clients
- Optional parent target protection
- DEFCON level and peace status sensors
- Daily launch counter
- Conflict chain tracking
- Per person WiFi status and minutes remaining sensors
- Mutual WiFi Destruction escalation
- Daily automatic reset
- AdGuard Home custom filtering rule enforcement
- Dashboard keypad services
- Built in dashboard PIN, target, confirm, launch, and cancel entities
- Config driven dashboard people/status sensor
- Polished `custom:button-card` dashboard example
- ESPHome starter example

## HACS installation

1. Open Home Assistant.
2. Open HACS.
3. Go to **Integrations**.
4. Open the three dot menu.
5. Choose **Custom repositories**.
6. Add your repository URL.
7. Select category **Integration**.
8. Install **Family DEFCON**.
9. Restart Home Assistant.

## Home Assistant configuration

After installing from HACS, add the integration from the UI:

```text
Settings → Devices & services → Add integration → Family DEFCON
```

The UI setup asks for the config file name. Leave it as:

```text
family_defcon.yaml
```

You no longer need to add `family_defcon:` to `configuration.yaml` for UI setup.

Copy the example `family_defcon.yaml` from this repo to:

```text
/config/family_defcon.yaml
```

Edit it for your family, PINs, stations, AdGuard URL, AdGuard client names, penalties, and dashboard targets.

## Secrets

Add your AdGuard credentials to `secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

## Required local config

Your `/config/family_defcon.yaml` needs a dashboard station and dashboard targets if you want the built in dashboard keypad.

```yaml
stations:
  dashboard:
    name: Home Assistant Dashboard
    enabled: true
    key_entity: ""

dashboard:
  station_id: dashboard
  default_target: Child 1
  targets:
    - Child 1
    - Child 2
    - Child 3
    - Parent 1
    - Parent 2
```

The target names must match your `people:` entries exactly.

## Example game rules

Default rules:

1. First strike gives the target a 30 minute timeout.
2. Retaliation adds 15 minutes to the retaliator and gives the other person 30 minutes.
3. Continued escalation adds penalties.
4. Too many strikes or too long of a retaliation chain activates Mutual WiFi Destruction.

These values are configurable.

## AdGuard Home setup

For per person blocking, AdGuard must see individual clients or persistent clients. If AdGuard only sees your router, per person rules will not work.

Good:

```text
Device -> AdGuard
```

Bad for per person blocking:

```text
Device -> Router DNS Forwarder -> AdGuard
```

The best setup is one AdGuard persistent client per person, with all of that person's devices listed under that client.

Family DEFCON manages custom filtering rules between:

```text
! FAMILY DEFCON START
! FAMILY DEFCON END
```

Example:

```text
! FAMILY DEFCON START
||*^$client='Child 1'
! FAMILY DEFCON END
```

## Main entities

```text
sensor.family_defcon_level
sensor.family_defcon_peace_status
sensor.family_defcon_daily_launches
sensor.family_defcon_conflict_chain
sensor.family_defcon_last_launcher
sensor.family_defcon_last_target
sensor.family_defcon_last_event
sensor.family_defcon_dashboard_people
switch.family_defcon_command_system_armed
switch.family_defcon_allow_parent_targets
binary_sensor.family_defcon_mutual_wifi_destruction
```

For each configured person:

```text
sensor.<person>_wifi_status
sensor.<person>_wifi_minutes_remaining
```

Built in dashboard entities:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
```

## Dashboard keypad services

```text
family_defcon.dashboard_keypress
family_defcon.dashboard_backspace
family_defcon.dashboard_clear_pin
family_defcon.dashboard_set_pin
```

## Dashboard

Install `custom:button-card` from HACS Frontend.

Then paste this card into a Manual Lovelace card:

```text
examples/button_card_keypad_dashboard.yaml
```

This dashboard pulls people and status rows from:

```text
sensor.family_defcon_dashboard_people
```

so it does not need hardcoded names.

## Common service calls

Arm:

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

Launch with PIN:

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "4444"
  target: Child 1
  station: dashboard
```

Clear all:

```yaml
action: family_defcon.clear_all
```

Enforce current AdGuard state:

```yaml
action: family_defcon.enforce_now
```

Reload config:

```yaml
action: family_defcon.reload_config
```

## Safety and limitations

Family DEFCON blocks DNS, not the physical WiFi radio.

It does not block direct IP traffic, cellular data, VPNs, Private DNS, or cached DNS until cache expires. For stronger enforcement, pair AdGuard with router firewall rules that force all DNS traffic to AdGuard.

## Upgrade notes

HACS updates the integration files under:

```text
custom_components/family_defcon/
```

It does not overwrite your local:

```text
/config/family_defcon.yaml
```

Your personal names, PINs, and AdGuard settings stay local.


## v4.0 UI installation

Family DEFCON now supports Home Assistant UI installation through a config flow.

Install path:

```text
Settings → Devices & services → Add integration → Family DEFCON
```

The large family/game configuration still lives in:

```text
/config/family_defcon.yaml
```

This keeps the UI setup simple while allowing advanced multi person configuration in YAML.

### Why keep family_defcon.yaml?

The config includes nested people, PINs, targets, stations, penalties, and AdGuard client mappings. Keeping that in YAML is easier to copy, back up, diff, and version while still letting the integration be installed from the UI.
