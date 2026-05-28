# Family DEFCON

**Current release: v1.1.4 HACS Compliant Release**

Family DEFCON is a Home Assistant custom integration for parent controlled DEFCON style WiFi enforcement using AdGuard Home.

## HACS repository structure

This repository is HACS compliant for a custom integration. The repo root contains:

```text
custom_components/family_defcon/manifest.json
custom_components/family_defcon/__init__.py
custom_components/family_defcon/config_flow.py
custom_components/family_defcon/services.yaml
README.md
hacs.json
```

For release based HACS installs, `hacs.json` uses:

```json
{
  "zip_release": true,
  "filename": "family_defcon_v1_1_4.zip"
}
```

Upload the matching release asset ZIP named:

```text
family_defcon_v1_1_4.zip
```

## Post install checks

After HACS install or redownload and Home Assistant Core restart, Developer Tools > Actions should include:

```text
family_defcon.adguard_config_status
family_defcon.adguard_connection_test
family_defcon.parent_admin_confirm
```

Run:

```yaml
action: family_defcon.config_audit_status
```

Then:

```yaml
action: family_defcon.adguard_config_status
```

Then:

```yaml
action: family_defcon.adguard_connection_test
```
