#!/usr/bin/env sh
set -e

ZIP_NAME="family_defcon_v1_1_3_github_release.zip"

cd /config 2>/dev/null || cd "$(pwd)"

echo "Family DEFCON v1.1.3 overwrite-safe installer"
echo "Working directory: $(pwd)"

if [ ! -f "$ZIP_NAME" ]; then
  echo "ERROR: $ZIP_NAME not found in this folder."
  echo "Upload $ZIP_NAME to the Home Assistant config root, then run this script again."
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="family_defcon_backups/preinstall_$TS"
mkdir -p "$BACKUP_DIR"

if [ -d custom_components/family_defcon ]; then
  echo "Backing up existing custom_components/family_defcon to $BACKUP_DIR"
  cp -a custom_components/family_defcon "$BACKUP_DIR/family_defcon"
fi

echo "Removing old installed Family DEFCON files..."
rm -rf custom_components/family_defcon
find custom_components -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Extracting release ZIP..."
unzip -o "$ZIP_NAME" -d .

echo "Verifying installed version..."
grep -n '"version"' custom_components/family_defcon/manifest.json
grep -n "people_set" custom_components/family_defcon/__init__.py >/dev/null && echo "people_set fix present"

echo "Done. Restart Home Assistant Core:"
echo "ha core restart"
