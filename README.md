Family DEFCON is a custom Home Assistant integration that turns household internet access into a controlled, game-style command system.

Family members can launch timed internet restrictions against configured targets. The integration tracks strikes, retaliation chains, daily launches, system readiness, and mutual Wi-Fi destruction while AdGuard Home applies the actual DNS blocking rules.

> Family DEFCON is intended for use by a household administrator on a Home Assistant and AdGuard Home installation they control.

## Features

- Guided Home Assistant configuration flow
- Up to eight configured people and eight command stations
- Parent and child roles
- Four-digit PIN authentication
- Timed first-strike, retaliation, and reattack penalties
- Configurable daily reset
- Mutual Wi-Fi destruction thresholds
- Optional targeting of parent accounts
- Optional station matching and commander-key requirements
- Home Assistant dashboard keypad and target controls
- Hidden parent administration controls
- Direct block and unblock services
- Persistent state across Home Assistant restarts
- AdGuard Home custom-rule enforcement
- Safe replacement of only the rules managed by Family DEFCON
- Diagnostic, configuration-audit, migration, and cleanup services
- Native config-entry setup, reload, and unload support
- Redacted Home Assistant diagnostics downloads
- HACS custom-repository installation

## Requirements

- Home Assistant 2024.6.0 or newer
- HACS 2.0.0 or newer for HACS installation
- AdGuard Home reachable from Home Assistant
- AdGuard Home clients configured with stable names, IP addresses, or identifiers that match the Family DEFCON person mappings
- Administrator access to Home Assistant and AdGuard Home

## Installation

### HACS custom repository

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=guitar82&repository=family_defcon&category=integration)

1. Open **HACS** in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add:

   ```text
   https://github.com/guitar82/family_defcon
   ```

5. Select **Integration** as the category.
6. Install **Family DEFCON**.
7. Restart Home Assistant.
8. Go to **Settings > Devices & services > Add integration**.
9. Search for **Family DEFCON**.

HACS installs the integration directly from `custom_components/family_defcon`.
No separately named release ZIP is required. Published GitHub releases provide
versioned upgrades; the default branch remains available for custom-repository
testing.

### Manual installation

Copy the integration directory into your Home Assistant configuration folder:

```text
custom_components/family_defcon
```

The final structure should look like:

```text
config/
└── custom_components/
    └── family_defcon/
        ├── __init__.py
        ├── binary_sensor.py
        ├── button.py
        ├── config_flow.py
        ├── const.py
        ├── diagnostics.py
        ├── entity.py
        ├── manifest.json
        ├── select.py
        ├── sensor.py
        ├── services.yaml
        ├── strings.json
        ├── switch.py
        ├── text.py
        └── translations/
```

Restart Home Assistant, then add the integration from **Settings > Devices & services**.

## Initial setup

The initial config flow creates one Family DEFCON instance with example entries for:

- Parent 1
- Parent 2
- Child 1
- Child 2
- Child 3
- Home Assistant Dashboard station

After setup, open the integration and select **Configure** to replace the example values.

### People

Each person can have:

- A display name
- A parent or child role
- A four-digit PIN
- An AdGuard Home client mapping
- Default-target eligibility
- Parent-target eligibility
- Dashboard-target visibility

Plain PINs entered through the options flow are write-only. The integration stores a salted hash rather than the entered PIN.

### Stations

A station represents a place from which a launch may originate, such as:

- Home Assistant dashboard
- Wall-mounted tablet
- ESP32 command station
- Parent control panel

Each station can have:

- Station ID
- Display name
- Enabled state
- Optional key entity

### AdGuard Home

Enter the base URL for the AdGuard Home server, without a `/control` suffix.

Examples:

```text
http://192.168.1.10:3000
http://homeassistant.local:3000
https://adguard.example.com
```

Do not enter:

```text
http://192.168.1.10:3000/control
```

Store the AdGuard credentials in `secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

The default secret names are:

```text
adguard_username
adguard_password
```

Family DEFCON reads the current AdGuard filtering rules, removes its previously managed rule block, and writes the updated rule set between dedicated Family DEFCON markers. Existing unrelated custom filtering rules are preserved.

## Recommended AdGuard client mapping

Use a stable AdGuard client value for each person.

Preferred mapping order:

1. Reserved IP address
2. MAC-based AdGuard client
3. Stable AdGuard client identifier
4. Friendly client name

Avoid mappings that can change frequently, such as a temporary DHCP address or a generic device name shared by several devices.

A person may need multiple device identifiers to fully restrict internet access. Verify the resulting rules in AdGuard Home before relying on enforcement.

## How the game works

The exact timing values are configurable.

The default behavior is based on:

- First strike: target receives a timed restriction
- Retaliation: the original launcher receives an additional penalty and the new target receives a restriction
- Reattack: conflict penalties increase
- Daily launch threshold: triggers mutual Wi-Fi destruction
- Conflict-chain threshold: triggers mutual Wi-Fi destruction
- Daily reset: clears the conflict state at the configured time

The default daily reset time is:

```text
05:00:00
```

The default mutual-destruction thresholds are:

```text
Daily launches: 5
Conflict chain: 4
```

## Dashboard controls

The integration creates entities for command-system state, dashboard target selection, PIN entry, target confirmation, launch controls, and per-person status.

Common entities include:

```text
sensor.family_defcon_level
sensor.family_defcon_last_event
switch.family_defcon_command_system_armed
binary_sensor.family_defcon_dashboard_target_confirmed
select.family_defcon_dashboard_target
text.family_defcon_dashboard_pin
button.family_defcon_dashboard_confirm_targeting
button.family_defcon_dashboard_launch
button.family_defcon_dashboard_cancel
```

Configured target buttons use the Family DEFCON namespace and display the configured target name.

Example:

```text
button.family_defcon_select_target_child_1
```

The button name shown in the dashboard should be the configured label, such as `Bart`, `Lisa`, `Maggie`, `Mom`, or `Dad`.

### Basic dashboard example

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Family DEFCON
    entities:
      - entity: sensor.family_defcon_level
      - entity: sensor.family_defcon_last_event
      - entity: switch.family_defcon_command_system_armed
      - entity: select.family_defcon_dashboard_target
      - entity: binary_sensor.family_defcon_dashboard_target_confirmed

  - type: grid
    columns: 3
    square: false
    cards:
      - type: button
        name: "1"
        tap_action:
          action: perform-action
          perform_action: family_defcon.dashboard_keypress
          data:
            digit: "1"

      - type: button
        name: "2"
        tap_action:
          action: perform-action
          perform_action: family_defcon.dashboard_keypress
          data:
            digit: "2"

      - type: button
        name: "3"
        tap_action:
          action: perform-action
          perform_action: family_defcon.dashboard_keypress
          data:
            digit: "3"

  - type: entities
    entities:
      - entity: button.family_defcon_dashboard_confirm_targeting
      - entity: button.family_defcon_dashboard_launch
      - entity: button.family_defcon_dashboard_cancel
```

Extend the keypad example with digits `0` through `9`, backspace, and clear controls.

## Services

Family DEFCON registers Home Assistant services under the `family_defcon` domain.

### Launch and command services

```text
family_defcon.launch
family_defcon.launch_with_pin
family_defcon.clear_all
family_defcon.stand_down
family_defcon.set_armed
family_defcon.set_parent_targets
family_defcon.enforce_now
family_defcon.reload_config
```

Example launch:

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "1234"
  target: "Child 1"
  station: "dashboard"
```

### Direct enforcement services

```text
family_defcon.block_person
family_defcon.unblock_person
```

Example:

```yaml
action: family_defcon.block_person
data:
  person: "Child 1"
```

### Dashboard services

```text
family_defcon.dashboard_keypress
family_defcon.dashboard_backspace
family_defcon.dashboard_clear_pin
family_defcon.dashboard_set_pin
family_defcon.dashboard_select_target
```

### Parent administration services

```text
family_defcon.parent_admin_keypress
family_defcon.parent_admin_backspace
family_defcon.parent_admin_clear_pin
family_defcon.parent_admin_confirm
family_defcon.parent_admin_cancel
family_defcon.parent_admin_clear_all
family_defcon.parent_admin_enforce_now
family_defcon.parent_admin_arm
family_defcon.parent_admin_disarm
family_defcon.parent_admin_cleanup_targets
```

### Diagnostics and maintenance

```text
family_defcon.adguard_config_status
family_defcon.adguard_connection_test
family_defcon.auth_config_status
family_defcon.config_audit_status
family_defcon.debug_status
family_defcon.hash_pin
family_defcon.migrate_entity_ids
family_defcon.cleanup_target_button_entities
```

Diagnostic results are written to the Home Assistant log, Family DEFCON event state, or a persistent notification depending on the service.

## Updating configuration

Saving options reloads the Family DEFCON config entry. Home Assistant cleanly
unloads and rebuilds all six entity platforms, so newly added or renamed people,
person sensors, selects, and target buttons appear without restarting Home
Assistant.

The entity registry may retain unavailable entries for names that no longer
exist. If those old entries remain, run
`family_defcon.cleanup_target_button_entities` and reload the integration.

## Cleaning stale target buttons

Earlier test versions may have created target buttons with old entity IDs such as:

```text
button.select_target_*
```

Run:

```yaml
action: family_defcon.cleanup_target_button_entities
data:
  remove_old_select_target: true
  remove_family_defcon_target_buttons: false
```

Reload the Family DEFCON integration afterward.

If you intentionally want to remove current generated Family DEFCON target-button
registry entries too, set `remove_family_defcon_target_buttons: true`. Use that
when cleaning up renamed-away `button.family_defcon_select_target_*` entities.
The active buttons will be recreated after a config-entry reload or restart.

The current generated target buttons should use:

```text
button.family_defcon_select_target_*
```

## Troubleshooting

### AdGuard connection fails

1. Confirm the base URL does not include `/control`.
2. Confirm Home Assistant can reach the AdGuard host and port.
3. Verify `adguard_username` and `adguard_password` in `secrets.yaml`.
4. Run:

   ```yaml
   action: family_defcon.adguard_connection_test
   ```

5. Review the resulting persistent notification and Home Assistant logs.

### Rules do not block the intended device

- Verify the Family DEFCON person-to-client mapping.
- Confirm the target device is using AdGuard Home for DNS.
- Confirm the device is not using encrypted DNS, a VPN, cellular data, or another DNS server.
- Check the Family DEFCON managed block in AdGuard custom filtering rules.
- Run `family_defcon.enforce_now`.

### New target buttons do not appear

Save the Family DEFCON options again or run `family_defcon.reload_config`.
Both actions now perform a full config-entry reload and rebuild the generated
entities.

### Duplicate or stale buttons remain

Run `family_defcon.cleanup_target_button_entities` with
`remove_family_defcon_target_buttons: true`, then reload the Family DEFCON
integration. Active target buttons are recreated from the current config.

### Services are missing after an update

Restart Home Assistant and confirm the installed integration version under **Settings > Devices & services > Family DEFCON**.

### View safe runtime diagnostics

Open **Settings > Devices & services > Family DEFCON**, open the integration's
menu, and select **Download diagnostics**. PINs, PIN hashes, and AdGuard
credentials are redacted from the downloaded file.

For a quick on-screen status report, run:

```yaml
action: family_defcon.debug_status
```

The diagnostic output is designed to report configuration state without exposing PIN values.

## Security notes

- Use unique parent PINs.
- Do not expose PIN text entities or service data in a public dashboard.
- Restrict dashboard editing and Developer Tools access to trusted Home Assistant users.
- Use HTTPS when AdGuard Home is accessed across an untrusted network.
- Keep AdGuard credentials in `secrets.yaml`.
- Do not expose the AdGuard Home administration interface directly to the public internet.
- Treat direct block, unblock, clear, and administrative services as privileged actions.
- DNS enforcement is not a complete network firewall. Devices using alternate DNS, VPNs, proxies, cellular service, or hard-coded encrypted DNS may bypass DNS filtering.

## State and reset behavior

Family DEFCON stores operational state using Home Assistant storage. This includes game state such as active restrictions, launch counters, conflict state, and recent events.

The integration checks enforcement periodically and performs the configured daily reset once the reset time is reached.

For safety, confirm dashboard PIN and target-confirmation behavior after restarting or reloading the integration.

## Advanced YAML overrides

The guided UI configuration is recommended.

Advanced YAML override fields are retained for compatibility with earlier builds but are disabled by default. Enable them only when you understand which values override the guided options.

The default legacy configuration filename is:

```text
family_defcon.yaml
```

## Events and automation ideas

Family DEFCON can be paired with Home Assistant automations for:

- Mobile notifications when a strike is launched
- Wall-panel sound effects
- DEFCON indicator lighting
- Parent approval workflows
- Station key switches
- Daily or weekly launch summaries
- AdGuard connectivity alerts

Keep real launch and administrative logic in Home Assistant services or scripts rather than relying only on dashboard actions.

## Release notes

### v2.0.0 beta 1

- Modern Home Assistant config-entry platform lifecycle
- Full entity rebuild after options or YAML reloads
- Native HACS custom-repository layout without a release ZIP dependency
- Redacted downloadable diagnostics
- Automated HACS and Hassfest validation

## Support

Use the repository issue tracker for reproducible bugs and feature requests.

Include:

- Home Assistant version
- Family DEFCON version
- AdGuard Home version
- Relevant Home Assistant log entries with secrets removed
- Whether the issue persists after a full Home Assistant restart
- The service or entity involved
- Expected and actual behavior

## Disclaimer

Family DEFCON is a personal household automation project. Test all rules and recovery actions before depending on it. The project is not a substitute for router-level access control, firewall policy, mobile-device management, or professional network administration.
