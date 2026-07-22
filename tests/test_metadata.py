"""Repository metadata consistency tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "family_defcon"
SPEC = importlib.util.spec_from_file_location(
    "family_defcon_config_helpers",
    INTEGRATION / "config_helpers.py",
)
assert SPEC is not None and SPEC.loader is not None
helpers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helpers)


class MetadataTests(unittest.TestCase):
    """Keep release and Home Assistant metadata synchronized."""

    def test_manifest_matches_runtime_version(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text())

        self.assertEqual("family_defcon", manifest["domain"])
        self.assertEqual(helpers.INTEGRATION_VERSION, manifest["version"])
        self.assertTrue(manifest["config_flow"])
        self.assertTrue(manifest["single_config_entry"])

    def test_hacs_minimum_matches_current_options_flow_api(self) -> None:
        hacs = json.loads((ROOT / "hacs.json").read_text())

        self.assertEqual("2024.12.0", hacs["homeassistant"])
        self.assertEqual("2.0.0", hacs["hacs"])

    def test_english_translation_matches_source_strings(self) -> None:
        strings = json.loads((INTEGRATION / "strings.json").read_text())
        english = json.loads((INTEGRATION / "translations" / "en.json").read_text())

        self.assertEqual(strings, english)

    def test_saved_pin_hashes_are_not_exposed_in_options_form(self) -> None:
        strings = json.loads((INTEGRATION / "strings.json").read_text())
        people_fields = strings["options"]["step"]["people"]["data"]

        self.assertFalse(any(field.endswith("_pin_hash") for field in people_fields))


if __name__ == "__main__":
    unittest.main()
