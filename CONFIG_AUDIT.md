Family DEFCON v5.8 Config Variable Audit

Patch notes:
- Guided UI PIN fields reject PINs longer than 4 characters before hashing.
- Active config validates people, targets, auth users, AdGuard clients, dashboard targets, and station.
- Backend launch_with_pin rejects PINs longer than 4 characters before auth check.
- Added config_audit_status service for safe active config audit.
- Target select filters options through active config people/dashboard target list.

Static audit checks:
- config_flow.py: PIN UI is password/write-only and max 4 validation exists: OK
- __init__.py: Active config validates UI variables and dashboard station: OK
- __init__.py: Auth uses hashed PINs and has safe audit services: OK
- button.py: Dashboard launch uses active dashboard station id: OK
- select.py: Dashboard target select uses active config: OK
- sensor.py: Sensors use active config and severity settings: OK
- services.yaml: Config audit service exists: OK

Important behavior:
- UI PIN fields are hidden/write-only.
- UI PINs longer than 4 characters are rejected before hashing.
- Launch requests with PINs longer than 4 characters are rejected.
- Active config is validated after UI/YAML/advanced config is merged.
- Dashboard launch uses config.dashboard.station_id.
- Dashboard station is guaranteed to exist.
- Diagnostics do not expose PIN values.
