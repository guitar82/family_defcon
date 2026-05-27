# Family DEFCON Examples

Recommended examples for new installers:

```text
dashboard_launch_console_dynamic_targets.yaml
dashboard_status_overview.yaml
automation_event_announcements.yaml
```

Required HACS frontend cards for the dynamic launch console:

```text
button-card
auto-entities
```

The dynamic launch console uses generated target buttons:

```text
button.family_defcon_select_target_*
```

Do not start with legacy examples unless you specifically want hard coded target names.
