# Family DEFCON v0.8

All variable data is now in `family_defcon.yaml`. v0.8 also fixes Home Assistant blocking I/O warnings by loading YAML files through the executor.

You no longer need `rest_commands.yaml` or `scripts.yaml` for AdGuard Home blocking.

## Configuration

Edit only:

```text
/config/family_defcon.yaml
```

It contains:

- people
- default targets
- parent targets
- PINs
- station names
- AdGuard base URL
- AdGuard client names
- timeout penalties
- escalation rules
- daily reset time

## Home Assistant configuration.yaml

Add:

```yaml
family_defcon:
```

## secrets.yaml

Add:

```yaml
adguard_username: your_adguard_username
adguard_password: your_adguard_password
```

## Test

```yaml
action: family_defcon.set_armed
data:
  enabled: true
```

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

Change these before using.

## AdGuard

Create persistent clients in AdGuard Home:

- Mom
- Dad
- Henry
- Marc
- Maggie

The integration creates/removes client specific block rules like:

```text
||*^$client='Henry'
```

## Upgrade note

If you used v0.6 with `rest_commands.yaml` and block scripts, you can leave those files alone, but they are no longer required when:

```yaml
dns:
  provider: adguard_home
```
