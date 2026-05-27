# Family DEFCON

**Current release: v4.6.0**

Family DEFCON is a Home Assistant custom integration that creates a playful DEFCON style family WiFi timeout system.

It supports PIN based launches, configurable people and targets, a polished Lovelace keypad dashboard, AdGuard Home enforcement, target confirmation, and escalation rules that can trigger Mutual WiFi Destruction.

## What this integration does

Family DEFCON lets configured users enter a 4 digit PIN, choose a target, confirm the target, and launch a WiFi timeout. Timeouts are enforced through AdGuard Home custom filtering rules.

The dashboard shows:

- Current DEFCON level
- Armed or disarmed status
- Daily launches
- Conflict chain
- PIN keypad
- Target buttons
- Target locked confirmation
- Current WiFi status per person
- Parent controls

## Main features

- Home Assistant UI install support through config flow
- Advanced configuration kept in `/config/family_defcon.yaml`
- 4 digit dashboard PIN entry
- Dashboard keypad with clear and backspace
- Configurable people, PINs, roles, stations, targets, and penalties
- Parent target protection with override switch
- Target confirmation state
- Direct target selection service
- Per person WiFi status sensors
- Per person minutes remaining sensors
- DEFCON level sensor
- Peace status sensor
- Daily launch counter
- Conflict chain counter
- Last launcher, last target, and last event sensors
- Mutual WiFi Destruction binary sensor
- AdGuard Home `set_rules` based enforcement
- Managed AdGuard rule block between start/end markers
- Polished `custom:button-card` dashboard example
- ESPHome starter example

## HACS installation

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

## Add the integration from the UI

After installing through HACS and restarting:

```text
Settings → Devices & services → Add integration → Family DEFCON
```

When prompted for the config file name, leave the default:

```text
family_defcon.yaml
```

You do **not** need this in `configuration.yaml` when using UI setup:

```yaml
family_defcon:
```

If you already added that earlier, remove it to avoid duplicate setup.

## Required local config file

Copy the included example file:

```text
family_defcon.yaml
```

to:

```text
/config/family_defcon.yaml
```

Edit it for your people, PINs, roles, AdGuard URL, AdGuard clients, stations, and dashboard targets.

## Secrets

Add your AdGuard credentials to `/config/secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

The example config references them here:

```yaml
dns:
  adguard_home:
    username_secret: adguard_username
    password_secret: adguard_password
```

## Required dashboard config

Your `/config/family_defcon.yaml` should include a dashboard station and dashboard targets:

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

The names under `dashboard.targets` must match your `people:` names exactly.

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

Family DEFCON blocks internet access by managing AdGuard Home custom filtering rules.

For per person blocking to work, AdGuard must see individual devices or persistent clients. The best setup is one AdGuard persistent client per person.

Good setup:

```text
Device → AdGuard
```

Bad setup for per person blocking:

```text
Device → Router DNS Forwarder → AdGuard
```

If AdGuard only sees your router as the client, client based rules such as this will not work correctly:

```text
||*^$client='Child 1'
```

Family DEFCON manages only the rule block between:

```text
! FAMILY DEFCON START
! FAMILY DEFCON END
```

Example managed block:

```text
! FAMILY DEFCON START
||*^$client='Child 1'
||*^$client='Child 2'
! FAMILY DEFCON END
```

## Entities created

Core entities:

```text
sensor.family_defcon_level
sensor.family_defcon_peace_status
sensor.family_defcon_daily_launches
sensor.family_defcon_conflict_chain
sensor.family_defcon_last_launcher
sensor.family_defcon_last_target
sensor.family_defcon_last_event
binary_sensor.family_defcon_mutual_wifi_destruction
switch.family_defcon_command_system_armed
switch.family_defcon_allow_parent_targets
```

Dashboard entities may appear as shorter entity IDs depending on Home Assistant naming:

```text
text.dashboard_pin
select.dashboard_target
button.dashboard_confirm_targeting
button.dashboard_launch
button.dashboard_cancel
sensor.dashboard_people
binary_sensor.dashboard_target_confirmed
```

or as longer entity IDs:

```text
text.family_defcon_dashboard_pin
select.family_defcon_dashboard_target
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
sensor.family_defcon_dashboard_people
binary_sensor.family_defcon_dashboard_target_confirmed
```

Use Developer Tools → States and search:

```text
dashboard
```

to confirm the exact entity IDs in your system.

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

## Services

Arm or disarm:

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

Launch with PIN:

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "3333"
  target: Child 1
  station: dashboard
```

Clear all timeouts:

```yaml
action: family_defcon.clear_all
```

Reapply AdGuard rules:

```yaml
action: family_defcon.enforce_now
```

Reload `/config/family_defcon.yaml`:

```yaml
action: family_defcon.reload_config
```

Dashboard keypad services:

```text
family_defcon.dashboard_keypress
family_defcon.dashboard_backspace
family_defcon.dashboard_clear_pin
family_defcon.dashboard_set_pin
```

Dashboard target service:

```yaml
action: family_defcon.dashboard_select_target
data:
  target: Child 1
```

Selecting a target clears the target confirmed state so the user must confirm again before launching.

## Dashboard

Install this HACS frontend card first:

```text
Button Card
```

The dashboard example is here:

```text
examples/button_card_keypad_dashboard.yaml
```

Paste the YAML into a Manual Lovelace card.

This dashboard includes:

- DEFCON header
- 4 digit PIN display
- keypad
- target buttons
- selected kid target turns blue
- selected parent target turns yellow
- target locked status after confirm
- WiFi status per person
- parent controls

## 4 digit PIN behavior

Dashboard PIN entry is limited to 4 digits.

- Keypad stops accepting digits after 4
- Text entity maximum is 4
- `dashboard_set_pin` only keeps the first 4 digits
- Clear and backspace reset target confirmation
- Selecting a new target resets target confirmation

## Game flow

Typical dashboard flow:

```text
Select target
Enter 4 digit PIN
Press CONFIRM
Status changes to TARGET LOCKED
Press LAUNCH
```

Launch or cancel clears the confirmation state.

## Troubleshooting

### The dashboard target service is missing

If this service is missing:

```text
family_defcon.dashboard_select_target
```

then Home Assistant is not running v4.5 or newer.

Check installed files:

```bash
cat /config/custom_components/family_defcon/manifest.json | grep version
grep -R "dashboard_select_target" /config/custom_components/family_defcon
```

### Confirm does not change to TARGET LOCKED

Search Developer Tools → States for:

```text
target_confirmed
```

You should see one of these:

```text
binary_sensor.dashboard_target_confirmed
binary_sensor.family_defcon_dashboard_target_confirmed
```

If not, Home Assistant is not running v4.3 or newer.

### PIN still allows more than 4 digits

Check the text entity:

```text
text.dashboard_pin
```

It should show:

```text
max: 4
```

If it shows:

```text
max: 12
```

then Home Assistant is not running v4.4 or newer.

### Force reinstall from GitHub

After uploading this package to GitHub:

```bash
cd /config

tar -czf family_defcon_before_update_$(date +%Y%m%d_%H%M%S).tar.gz \
  custom_components/family_defcon \
  family_defcon.yaml \
  2>/dev/null || true

rm -rf /config/family_defcon_download
git clone https://github.com/guitar82/family_defcon.git /config/family_defcon_download

cat /config/family_defcon_download/custom_components/family_defcon/manifest.json | grep version
grep -R "dashboard_select_target" /config/family_defcon_download/custom_components/family_defcon
grep -R "DashboardTargetConfirmedSensor\|dashboard_target_confirmed" /config/family_defcon_download/custom_components/family_defcon
grep -R "_attr_native_max = 4\|len(current) >= 4" /config/family_defcon_download/custom_components/family_defcon

rm -rf /config/custom_components/family_defcon
mkdir -p /config/custom_components
cp -r /config/family_defcon_download/custom_components/family_defcon /config/custom_components/family_defcon

rm -rf /config/custom_components/family_defcon/__pycache__
rm -rf /config/family_defcon_download

ha core restart
```

## Safety and limitations

Family DEFCON blocks DNS. It does not physically turn off WiFi.

It does not block:

- cellular data
- direct IP traffic
- VPN bypasses
- Private DNS bypasses
- cached DNS until cache expires

For stronger enforcement, configure the router/firewall to force all DNS traffic to AdGuard.

## Repository structure

```text
custom_components/family_defcon/
  __init__.py
  binary_sensor.py
  button.py
  config_flow.py
  const.py
  manifest.json
  select.py
  sensor.py
  services.yaml
  strings.json
  switch.py
  text.py
  translations/en.json

examples/
  button_card_keypad_dashboard.yaml
  button_card_config_driven_dashboard.yaml
  esphome_shared_terminal_starter.yaml

family_defcon.yaml
configuration.yaml.example
secrets.yaml.example
hacs.json
info.md
README.md
RELEASE_NOTES.md
VERIFY.txt
```

## Upgrade notes

HACS updates files under:

```text
/config/custom_components/family_defcon/
```

It does not overwrite your local:

```text
/config/family_defcon.yaml
```

Your personal people, PINs, targets, and AdGuard settings remain local.
