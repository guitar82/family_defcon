# Family DEFCON v0.6 PIN Mode

GitHub ready Home Assistant custom integration for Family DEFCON.

## New in v0.6

- `family_defcon.launch_with_pin`
- Any person can use any terminal
- PINs identify the commander
- Shared station list
- AdGuard Home REST command examples
- Full scripts file

## Install

Copy `custom_components/family_defcon` to `/config/custom_components/family_defcon`.

Copy these files to `/config`:

- `family_defcon.yaml`
- `rest_commands.yaml`
- `scripts.yaml`

Add to `configuration.yaml`:

```yaml
family_defcon:
rest_command: !include rest_commands.yaml
script: !include scripts.yaml
```

Add to `secrets.yaml`:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

Create toggle helpers:

- `input_boolean.internet_block_mom`
- `input_boolean.internet_block_dad`
- `input_boolean.internet_block_henry`
- `input_boolean.internet_block_marc`
- `input_boolean.internet_block_maggie`
- `input_boolean.internet_block_all_kids`

Restart Home Assistant.

## Test

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
  target: Henry
  station: station_1
```

Default PINs:

- Mom: 1111
- Dad: 2222
- Henry: 3333
- Marc: 4444
- Maggie: 5555

Change these before real use.
