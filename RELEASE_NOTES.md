# Family DEFCON Release Notes

## v5.8.9 Clean Public Beta

- Built from the stable v5.8.x dynamic line.
- Removed active demo PINs from the YAML backup example.
- Replaced README with a UI-first new installer guide.
- Promoted the dynamic target dashboard as the primary launch console.
- Moved stale hard-coded dashboard examples into `examples/legacy` when present.
- Added privacy/recorder guidance for the masked PIN text entity.
- Preserved dynamic target buttons, hidden PIN state, instant PIN verification, and native HA events.

## v5.8.8

Clean dynamic installer package.

Changes:
- Built from stable v5.8.7.
- UI default people are generic: Parent 1, Parent 2, Child 1, Child 2, Child 3.
- Removed stale hard coded dashboard examples from the package.
- Kept the dynamic dashboard example based on generated target button entities.
- Kept hidden dashboard PIN state.
- Kept instant salted SHA256 PIN verification.
- Kept native Home Assistant events.
- Does not include v5.9 or v5.10 backend startup changes.
