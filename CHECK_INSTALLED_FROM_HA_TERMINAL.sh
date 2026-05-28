#!/usr/bin/env sh
cd /config 2>/dev/null || cd "$(pwd)"
echo "=== Family DEFCON installed version ==="
grep -n '"version"' custom_components/family_defcon/manifest.json 2>/dev/null || echo "manifest missing"
echo ""
echo "=== Required code checks ==="
grep -n "people_set" custom_components/family_defcon/__init__.py 2>/dev/null || echo "people_set missing"
grep -n "safe_register_service" custom_components/family_defcon/__init__.py 2>/dev/null || echo "safe_register_service missing"
grep -n "adguard_connection_test" custom_components/family_defcon/__init__.py 2>/dev/null || echo "adguard_connection_test missing"
grep -n "normalize_adguard_base_url" custom_components/family_defcon/__init__.py 2>/dev/null || echo "AdGuard URL normalizer missing"
echo ""
echo "=== Recent Family DEFCON logs ==="
grep -i "family_defcon\|family defcon" home-assistant.log 2>/dev/null | tail -80 || true
