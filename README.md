# Family DEFCON

Family DEFCON is a Home Assistant custom integration that creates a family WiFi timeout and escalation system with a DEFCON style command interface.

It is designed for families that want a playful, visible consequence system for arguments, retaliation, and repeated conflicts. It can connect to AdGuard Home and pause internet access for configured people using AdGuard custom filtering rules.

## Features

Family DEFCON supports:

- PIN based launch authentication
- Any person can use any configured station or dashboard terminal
- Config driven people, targets, PINs, stations, penalties, and AdGuard clients
- Optional parent target protection
- DEFCON level and peace status sensors
- Daily launch counter
- Conflict chain tracking
- Per person WiFi status and minutes remaining sensors
- Mutual WiFi Destruction escalation
- Daily automatic reset
- AdGuard Home custom filtering rule enforcement
- Built in dashboard launch entities
- Config driven dashboard people/status sensor
- Example Lovelace dashboard cards
- ESPHome starter example

## How the game works

Default rules:

1. A first strike gives the target a 30 minute internet timeout.
2. If the target retaliates, the retaliator gets an added 15 minute penalty and the other person gets 30 minutes.
3. If the other person attacks back, the attacker gets an added 15 minute penalty and the target gets 45 minutes.
4. If the next retaliation happens, Mutual WiFi Destruction activates.
5. Five total strikes in one day also activates Mutual WiFi Destruction.

These values are configurable in `family_defcon.yaml`.

## HACS installation

1. Open Home Assistant.
2. Open HACS.
3. Go to **Integrations**.
4. Open the three dot menu.
5. Choose **Custom repositories**.
6. Add your repository URL, for example:

```text
https://github.com/guitar82/family_defcon
```

7. Select category **Integration**.
8. Install **Family DEFCON**.
9. Restart Home Assistant.

## Home Assistant configuration

Add this to `configuration.yaml`:

```yaml
family_defcon:
```

Then copy the example config file from this repository:

```text
family_defcon.yaml
```

to:

```text
/config/family_defcon.yaml
```

Edit `/config/family_defcon.yaml` for your own people, PINs, stations, AdGuard URL, AdGuard client names, penalties, and dashboard targets.

## Secrets

Add your AdGuard credentials to `secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

The example config references those secrets here:

```yaml
dns:
  adguard_home:
    username_secret: adguard_username
    password_secret: adguard_password
```

## Example configuration

```yaml
people:
  - Parent 1
  - Parent 2
  - Child 1
  - Child 2
  - Child 3

default_targets:
  - Child 1
  - Child 2
  - Child 3

parent_targets:
  - Parent 1
  - Parent 2

allow_parent_targets_default: false

auth:
  mode: pin
  max_bad_pin_attempts: 3
  lockout_seconds_after_bad_pins: 120
  users:
    Parent 1:
      pin: "1111"
      role: parent
    Parent 2:
      pin: "2222"
      role: parent
    Child 1:
      pin: "3333"
      role: child
    Child 2:
      pin: "4444"
      role: child
    Child 3:
      pin: "5555"
      role: child

stations:
  dashboard:
    name: Home Assistant Dashboard
    enabled: true
    key_entity: ""

  station_1:
    name: Kitchen Terminal
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
    managed_start_marker: "! FAMILY DEFCON START"
    managed_end_marker: "! FAMILY DEFCON END"

    clients:
      Parent 1:
        client_name: Parent 1
        enabled: true
      Parent 2:
        client_name: Parent 2
        enabled: true
      Child 1:
        client_name: Child 1
        enabled: true
      Child 2:
        client_name: Child 2
        enabled: true
      Child 3:
        client_name: Child 3
        enabled: true

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

## AdGuard Home setup

Family DEFCON blocks internet access through AdGuard Home custom filtering rules.

For per person blocking to work, AdGuard must see each device or person as a separate client. The best setup is one AdGuard persistent client per person.

Example:

```text
Child 1
  Child 1 phone
  Child 1 tablet
  Child 1 laptop

Child 2
  Child 2 phone
  Child 2 console
```

Then map those persistent client names in `family_defcon.yaml`:

```yaml
dns:
  adguard_home:
    clients:
      Child 1:
        client_name: Child 1
        enabled: true
```

When Child 1 is blocked, Family DEFCON manages a rule like:

```text
||*^$client='Child 1'
```

### Important DHCP note

If AdGuard only sees your router as the client, per person blocking will not work. AdGuard needs to see the actual device or persistent client.

Good:

```text
Device → AdGuard
```

Bad for per person rules:

```text
Device → Router DNS forwarder → AdGuard
```

If your router does not let you hand out AdGuard as the DNS server, you can use AdGuard as your DHCP server or manually set DNS on the devices.

## Managed AdGuard rules

Family DEFCON preserves existing AdGuard custom rules and only manages rules between:

```text
! FAMILY DEFCON START
! FAMILY DEFCON END
```

Example:

```text
! FAMILY DEFCON START
||*^$client='Child 1'
||*^$client='Child 2'
! FAMILY DEFCON END
```

## Created entities

Core entities include:

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

For each configured person, Family DEFCON creates:

```text
sensor.<person>_wifi_status
sensor.<person>_wifi_minutes_remaining
```

Example:

```text
sensor.child_1_wifi_status
sensor.child_1_wifi_minutes_remaining
```

Dashboard launch entities:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
```

## Services

### Arm or disarm the system

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

```yaml
action: family_defcon.set_armed
data:
  enabled: false
```

### Launch with PIN

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "4444"
  target: Child 1
  station: dashboard
```

### Clear all

```yaml
action: family_defcon.clear_all
```

### Stand down

Resets the conflict chain without clearing active timeouts.

```yaml
action: family_defcon.stand_down
```

### Enforce now

Reapplies the current Family DEFCON block/unblock state to AdGuard.

```yaml
action: family_defcon.enforce_now
```

### Reload config

Reloads `/config/family_defcon.yaml`.

```yaml
action: family_defcon.reload_config
```

## Dashboard

The recommended dashboard card is:

```text
examples/button_card_config_driven_dashboard.yaml
```

This card uses `custom:button-card` and reads the people/status rows from:

```text
sensor.family_defcon_dashboard_people
```

That means the dashboard does not need hardcoded person names.

Install `custom:button-card` from HACS Frontend first.

Then paste the YAML into a Manual dashboard card.

A simpler built in Lovelace example is also included:

```text
examples/compact_launch_dashboard_card.yaml
```

## ESPHome

A starter ESPHome example is included:

```text
examples/esphome_shared_terminal_starter.yaml
```

The ESPHome terminal can call:

```yaml
homeassistant.action:
  action: family_defcon.launch_with_pin
  data:
    pin: "4444"
    target: "Child 1"
    station: "station_1"
```

## Safety and limitations

Family DEFCON blocks DNS, not the physical WiFi connection.

It does not block:

- Direct IP traffic
- Cellular data
- VPN bypasses
- Private DNS that bypasses AdGuard
- Cached DNS until the cache expires

For a family consequence system, this is usually enough. For stronger enforcement, pair AdGuard with router firewall rules that prevent clients from using outside DNS.

## Repository structure

```text
custom_components/family_defcon/
  __init__.py
  binary_sensor.py
  button.py
  const.py
  manifest.json
  select.py
  sensor.py
  services.yaml
  switch.py
  text.py

examples/
  button_card_config_driven_dashboard.yaml
  compact_launch_dashboard_card.yaml
  esphome_shared_terminal_starter.yaml

family_defcon.yaml
configuration.yaml.example
secrets.yaml.example
hacs.json
README.md
info.md
```

## Upgrade notes

HACS installs and updates the integration files under:

```text
custom_components/family_defcon/
```

It does not automatically overwrite your local:

```text
/config/family_defcon.yaml
```

That means your personal people, PINs, stations, and AdGuard settings remain local.
