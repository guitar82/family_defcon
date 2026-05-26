# Family DEFCON

Family DEFCON is a Home Assistant custom integration for a family WiFi timeout and escalation simulator.

It supports:

- PIN mode so any person can use any terminal
- Shared ESPHome or dashboard terminals
- Config driven people, stations, PINs, targets, AdGuard URL, and AdGuard clients
- Optional Parent 1 and Parent 2 target protection
- DEFCON level, peace status, daily launches, conflict chain, and event log sensors
- AdGuard Home custom filtering rules for DNS based internet pause
- Mutual WiFi Destruction rules

## HACS install

1. In Home Assistant, open **HACS**.
2. Go to **Integrations**.
3. Open the three dot menu.
4. Choose **Custom repositories**.
5. Add this repository URL:

```text
https://github.com/guitar82/family_defcon
```

6. Select category **Integration**.
7. Install **Family DEFCON**.
8. Restart Home Assistant.

HACS custom integration repositories need a root `hacs.json` file and the integration files under `custom_components/<domain>/`. This repository follows that structure.

## Home Assistant configuration

Add this to `configuration.yaml`:

```yaml
family_defcon:
```

Copy the example config file from this repository:

```text
family_defcon.yaml
```

to:

```text
/config/family_defcon.yaml
```

Edit that file for your own people, PINs, stations, AdGuard URL, AdGuard client names, penalties, and reset rules.

## Secrets

Add your AdGuard credentials to `secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

## Required AdGuard setup

Create persistent clients in AdGuard Home. The default example expects:

```text
Parent 1
Parent 2
Child 1
Child 2
Child 3
```

The names can be changed in `family_defcon.yaml`:

```yaml
dns:
  adguard_home:
    clients:
      Child 1:
        client_name: Child 1
```

The `client_name` must match the persistent client name in AdGuard Home.

## AdGuard rule behavior

Family DEFCON uses AdGuard Home custom filtering rules. It reads existing custom rules, preserves anything outside the managed block, and writes the current DEFCON rules between:

```text
! FAMILY DEFCON START
! FAMILY DEFCON END
```

Example when Child 1 is blocked:

```text
! FAMILY DEFCON START
||*^$client='Child 1'
! FAMILY DEFCON END
```

## Default PINs

Change these before real use:

```text
Parent 1: 1111
Parent 2: 2222
Child 1: 3333
Child 2: 4444
Child 3: 5555
```

## Test service call

After restart, go to **Developer Tools → Actions** and run:

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

Then:

```yaml
action: family_defcon.launch_with_pin
data:
  pin: "4444"
  target: Child 1
  station: station_1
```

With the default config, PIN `4444` is Child 2.

## Dashboard

A starter dashboard card is included at:

```text
examples/dashboard_card.yaml
```

Paste it into a Home Assistant manual card.

## ESPHome

A starter ESPHome example is included at:

```text
examples/esphome_shared_terminal_starter.yaml
```

This is only a service call starter. A full touchscreen UI can be built on top of it.

## Repository structure

```text
custom_components/family_defcon/
  __init__.py
  binary_sensor.py
  const.py
  manifest.json
  sensor.py
  services.yaml
  switch.py

hacs.json
README.md
family_defcon.yaml
configuration.yaml.example
secrets.yaml.example
examples/
```

## Upgrade notes

HACS installs and updates only the integration files under:

```text
custom_components/family_defcon/
```

It will not automatically overwrite your local `/config/family_defcon.yaml`, which is good. Your personal settings stay local.


## v1.5 Generic examples

The public HACS package uses generic example people:

```text
Parent 1
Parent 2
Child 1
Child 2
Child 3
```

Put your real family names only in your local `/config/family_defcon.yaml`.
