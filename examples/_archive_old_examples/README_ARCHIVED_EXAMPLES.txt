Archived Family DEFCON dashboard examples

These files are older dashboard examples kept only for reference.
Do not use these for a new install unless you are intentionally troubleshooting an older build.

Use these current examples from the main examples folder instead:

dashboard_parent_interface_launcher_style.yaml
dashboard_parent_interface_working.yaml
dashboard_parent_interface.yaml
dashboard_launch_console_dynamic_targets.yaml
dashboard_dynamic_target_buttons_only.yaml
dashboard_status_overview.yaml

The current parent dashboard flow is:

Enter PIN with the existing dashboard keypad
Press CONFIRM
binary_sensor.parent_admin_confirmed turns on
Use parent controls
Press CANCEL to clear confirmation

The archived examples may reference old parent verify buttons, old parent keypad services, or stale entity IDs.
