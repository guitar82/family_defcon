# Family DEFCON v0.5

A Home Assistant custom integration for a family WiFi peace/retaliation simulator.

## What is included

- Home Assistant custom integration
- Config file at `/config/family_defcon.yaml`
- Unlimited station support
- Station IDs such as `station_3`
- Commander validation
- Optional key entity validation
- Parent target protection
- DEFCON level sensor
- Peace status sensor
- Per person status and minutes remaining sensors
- Persistent state
- Daily reset
- Cooldown protection
- Custom service based DNS/router hooks
- Fake blocking scripts for testing
- Starter ESPHome station template

## Install

1. Copy `custom_components/family_defcon/` to `/config/custom_components/family_defcon/`.
2. Copy `family_defcon.yaml` to `/config/family_defcon.yaml`.
3. Add this to `configuration.yaml`:

```yaml
family_defcon:
```

4. Restart Home Assistant.

## First test

Run this from Developer Tools > Actions:

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

Then:

```yaml
action: family_defcon.launch
data:
  launcher: Henry
  target: Marc
  station: station_3
```

Expected result: Marc becomes blocked for about 30 minutes and DEFCON becomes 4.

## DNS blocking

The integration does not hardcode AdGuard or Pi hole. It calls Home Assistant scripts from the config file. Start with `examples/scripts_fake_blocking.yaml`, then replace those scripts with your real DNS/router blocking actions later.

To activate enforcement after your scripts are ready, change this in `/config/family_defcon.yaml`:

```yaml
dns:
  enabled: true
  enforcement_mode: active
```

Then call:

```yaml
action: family_defcon.reload_config
```

## ESPHome

Use `examples/esphome_station_template.yaml` as the starting station config. It is intentionally display hardware neutral because the exact display and touchscreen driver depend on the screen you buy.
