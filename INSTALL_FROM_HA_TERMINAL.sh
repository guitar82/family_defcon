#!/usr/bin/env bash
set -e

ZIP="/config/family_defcon_hacs_ready_v5_8_31_confirm_hard_fix.zip"

echo "Family DEFCON v5.8.31 hard installer"
echo "Expected zip: $ZIP"

if [ ! -f "$ZIP" ]; then
  echo "ERROR: Upload family_defcon_hacs_ready_v5_8_31_confirm_hard_fix.zip to /config first."
  exit 1
fi

mkdir -p /config/family_defcon_backups
if [ -d /config/custom_components/family_defcon ]; then
  cp -a /config/custom_components/family_defcon "/config/family_defcon_backups/family_defcon_backup_$(date +%Y%m%d_%H%M%S)"
fi

rm -rf /config/custom_components/family_defcon
rm -rf /config/family_defcon_extract
mkdir -p /config/custom_components

unzip -o "$ZIP" -d /config/family_defcon_extract >/tmp/family_defcon_unzip.log

if [ ! -d /config/family_defcon_extract/custom_components/family_defcon ]; then
  echo "ERROR: Extracted package does not contain custom_components/family_defcon"
  find /config/family_defcon_extract -maxdepth 4 -type d
  exit 1
fi

cp -a /config/family_defcon_extract/custom_components/family_defcon /config/custom_components/family_defcon

echo "Installed version:"
grep -n '"version"' /config/custom_components/family_defcon/manifest.json

echo "Confirm services in code:"
grep -n 'parent_admin_confirm' /config/custom_components/family_defcon/__init__.py
grep -n 'parent_admin_confirm' /config/custom_components/family_defcon/services.yaml

rm -rf /config/family_defcon_extract

echo "Now run: ha core restart"
