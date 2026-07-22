"""Tests for Family DEFCON configuration validation and migration helpers."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import unittest


HELPERS_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "family_defcon"
    / "config_helpers.py"
)
SPEC = importlib.util.spec_from_file_location(
    "family_defcon_config_helpers", HELPERS_PATH
)
assert SPEC is not None and SPEC.loader is not None
helpers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helpers)


def people_form(*names: str) -> dict:
    """Return a minimally valid flattened people form."""
    data = {}
    for index, name in enumerate(names, start=1):
        prefix = f"person_{index}"
        data[f"{prefix}_name"] = name
        data[f"{prefix}_role"] = "child"
        data[f"{prefix}_pin"] = ""
        data[f"{prefix}_adguard_client"] = name
        data[f"{prefix}_default_target"] = True
        data[f"{prefix}_parent_target"] = False
        data[f"{prefix}_dashboard_target"] = True
    return data


def station_form(*station_ids: str, dashboard_station: str = "dashboard") -> dict:
    """Return a minimally valid flattened station form."""
    data = {
        "dashboard_station_id": dashboard_station,
        "dashboard_default_target": "Child 1",
    }
    for index, station_id in enumerate(station_ids, start=1):
        prefix = f"station_{index}"
        data[f"{prefix}_id"] = station_id
        data[f"{prefix}_name"] = station_id.title()
        data[f"{prefix}_enabled"] = True
        data[f"{prefix}_key_entity"] = ""
    return data


class DefaultOptionsTests(unittest.TestCase):
    """Validate default option construction."""

    def test_default_options_returns_independent_collections(self) -> None:
        first = helpers.default_options()
        second = helpers.default_options()

        first["people_list"].append("Someone Else")
        first["stations_list"][0]["id"] = "changed"

        self.assertNotIn("Someone Else", second["people_list"])
        self.assertEqual("dashboard", second["stations_list"][0]["id"])


class PinTests(unittest.TestCase):
    """Validate current and backward-compatible PIN handling."""

    def test_default_hash_work_factor_is_dashboard_friendly(self) -> None:
        self.assertEqual(20_000, helpers.PIN_HASH_ITERATIONS)

    def test_pbkdf2_hash_round_trip(self) -> None:
        pin_hash = helpers.hash_pin_value("1234", salt="fixed", iterations=100)

        self.assertTrue(helpers.verify_pin_value("1234", {"pin_hash": pin_hash}))
        self.assertFalse(helpers.verify_pin_value("4321", {"pin_hash": pin_hash}))

    def test_legacy_sha256_hash_still_verifies(self) -> None:
        digest = hashlib.sha256("salt:1234".encode()).hexdigest()
        user = {"pin_hash": f"sha256$salt${digest}"}

        self.assertTrue(helpers.verify_pin_value("1234", user))
        self.assertFalse(helpers.verify_pin_value("9999", user))

    def test_legacy_plaintext_pin_still_verifies(self) -> None:
        self.assertTrue(helpers.verify_pin_value("1234", {"pin": "1234"}))

    def test_empty_pin_never_authenticates_an_unconfigured_user(self) -> None:
        self.assertFalse(helpers.verify_pin_value("", {}))
        self.assertFalse(helpers.verify_pin_value("", {"pin": ""}))

    def test_unreasonable_pbkdf2_work_factor_is_rejected(self) -> None:
        user = {"pin_hash": "pbkdf2_sha256$120001$salt$not-a-real-digest"}

        self.assertFalse(helpers.verify_pin_value("1234", user))

    def test_hash_generation_rejects_a_stalling_work_factor(self) -> None:
        with self.assertRaises(ValueError):
            helpers.hash_pin_value("1234", iterations=120_001)

    def test_legacy_auth_mapping_plaintext_pin_is_migrated(self) -> None:
        migrated = helpers.migrate_auth_users_mapping(
            {
                "Parent": {"role": "parent", "pin": "1234"},
                "Child": {"role": "child", "pin_hash": "existing"},
            }
        )

        self.assertNotIn("pin", migrated["Parent"])
        self.assertTrue(
            helpers.verify_pin_value(
                "1234", {"pin_hash": migrated["Parent"]["pin_hash"]}
            )
        )
        self.assertEqual("existing", migrated["Child"]["pin_hash"])


class NormalizationTests(unittest.TestCase):
    """Validate URL and time normalization."""

    def test_adguard_url_normalization(self) -> None:
        self.assertEqual(
            "http://192.168.1.10:3000",
            helpers.normalize_adguard_url("192.168.1.10:3000/control/"),
        )
        self.assertEqual(
            "https://adguard.example.com",
            helpers.normalize_adguard_url("https://adguard.example.com/"),
        )

    def test_adguard_url_rejects_unsafe_or_unsupported_parts(self) -> None:
        invalid_urls = (
            "ftp://adguard.example.com",
            "http://:3000",
            "http://adguard.example.com:99999",
            "http://ad guard.example.com",
            "https://user:password@adguard.example.com",
            "https://adguard.example.com/custom/path",
            "https://adguard.example.com?debug=true",
        )
        for value in invalid_urls:
            with self.subTest(value=value), self.assertRaises(ValueError):
                helpers.normalize_adguard_url(value)

    def test_daily_reset_time_normalization(self) -> None:
        self.assertEqual("05:00:00", helpers.normalize_daily_reset_time("05:00"))
        with self.assertRaises(ValueError):
            helpers.normalize_daily_reset_time("25:00")


class PeopleTests(unittest.TestCase):
    """Validate people form rules and safe PIN preservation."""

    def test_people_validation_accepts_valid_form(self) -> None:
        form = people_form("Parent", "Child")
        form["person_1_pin"] = "1234"

        self.assertEqual({}, helpers.validate_people_input(form))

    def test_people_validation_rejects_duplicate_names_and_entity_slugs(self) -> None:
        duplicate_name = people_form("Child", "child")
        duplicate_slug = people_form("John Smith", "John-Smith")

        self.assertEqual(
            "duplicate_person",
            helpers.validate_people_input(duplicate_name)["person_2_name"],
        )
        self.assertEqual(
            "duplicate_person_identifier",
            helpers.validate_people_input(duplicate_slug)["person_2_name"],
        )

    def test_people_validation_requires_four_digits(self) -> None:
        form = people_form("Child")
        form["person_1_pin"] = "12ab"

        self.assertEqual(
            "invalid_pin",
            helpers.validate_people_input(form)["person_1_pin"],
        )

    def test_people_validation_requires_people_and_dashboard_target(self) -> None:
        self.assertEqual(
            "people_required",
            helpers.validate_people_input({})["base"],
        )
        form = people_form("Child")
        form["person_1_dashboard_target"] = False
        self.assertEqual(
            "dashboard_target_required",
            helpers.validate_people_input(form)["base"],
        )

    def test_rename_preserves_hash_by_slot_without_exposing_it(self) -> None:
        existing_hash = helpers.hash_pin_value("1234", salt="fixed", iterations=100)
        existing = {
            **helpers.default_options(),
            "people_list": ["Old Name"],
            "people_pin_hashes": {"Old Name": existing_hash},
            "dashboard_default_target": "Old Name",
        }
        form = people_form("New Name")

        result = helpers.build_people_options(form, existing)

        self.assertEqual(existing_hash, result["people_pin_hashes"]["New Name"])
        self.assertEqual({}, result["people_pins"])
        self.assertEqual("New Name", result["dashboard_default_target"])
        self.assertEqual("Old Name", existing["people_list"][0])

    def test_new_pin_is_hashed_and_never_persisted_plaintext(self) -> None:
        form = people_form("Child")
        form["person_1_pin"] = "1234"

        result = helpers.build_people_options(form, helpers.default_options())

        self.assertEqual({}, result["people_pins"])
        self.assertNotIn("1234", result["people_pin_hashes"]["Child"])
        self.assertTrue(
            helpers.verify_pin_value(
                "1234", {"pin_hash": result["people_pin_hashes"]["Child"]}
            )
        )

    def test_clear_pin_removes_the_saved_hash(self) -> None:
        existing = {
            **helpers.default_options(),
            "people_list": ["Child"],
            "people_pin_hashes": {
                "Child": helpers.hash_pin_value("1234", salt="fixed", iterations=100)
            },
        }
        form = people_form("Child")
        form["person_1_clear_pin"] = True

        result = helpers.build_people_options(form, existing)

        self.assertEqual({}, result["people_pin_hashes"])


class StationTests(unittest.TestCase):
    """Validate station references and duplicate protection."""

    def test_station_validation_rejects_duplicates_and_unknown_dashboard(self) -> None:
        duplicate = station_form("dashboard", "DASHBOARD")
        unknown = station_form("kitchen", dashboard_station="dashboard")

        self.assertEqual(
            "duplicate_station",
            helpers.validate_station_input(duplicate)["station_2_id"],
        )
        self.assertEqual(
            "unknown_station",
            helpers.validate_station_input(unknown)["dashboard_station_id"],
        )

    def test_station_builder_repairs_unknown_default_target(self) -> None:
        existing = {
            **helpers.default_options(),
            "dashboard_targets_list": ["Child 1", "Child 2"],
        }
        form = station_form("Dashboard", dashboard_station="dashboard")
        form["dashboard_default_target"] = "Removed Person"

        result = helpers.build_station_options(form, existing)

        self.assertEqual("Dashboard", result["dashboard_station_id"])
        self.assertEqual("Child 1", result["dashboard_default_target"])


if __name__ == "__main__":
    unittest.main()
