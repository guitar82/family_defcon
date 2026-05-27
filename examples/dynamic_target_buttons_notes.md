# Dynamic Target Buttons

Family DEFCON creates one button entity for each configured dashboard target.

Example entity format:

```text
button.family_defcon_select_target_<target_name>
```

Examples with generic setup names:

```text
button.family_defcon_select_target_parent_1
button.family_defcon_select_target_child_1
```

The list is based on Dashboard Targets configured in the Family DEFCON UI.

To use the fully dynamic dashboard example, install these HACS frontend cards:

```text
button-card
auto-entities
```

Then use:

```text
examples/dashboard_launch_console_dynamic_targets.yaml
```

If you change people or dashboard targets in the UI, reload Family DEFCON or restart Home Assistant so the target button entities are recreated.
