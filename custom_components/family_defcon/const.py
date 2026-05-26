"""Constants for Family DEFCON."""

DOMAIN = "family_defcon"
SIGNAL_UPDATE = f"{DOMAIN}_update"
STORAGE_KEY = f"{DOMAIN}.state"
STORAGE_VERSION = 1
CONFIG_PATH = "family_defcon.yaml"
PLATFORMS = ["sensor", "binary_sensor", "switch"]

DEFAULT_CONFIG = {
    "people": ["Mom", "Dad", "Henry", "Marc", "Maggie"],
    "default_targets": ["Henry", "Marc", "Maggie"],
    "parent_targets": ["Mom", "Dad"],
    "allow_parent_targets_default": False,
    "launches_before_mutual_destruction": 5,
    "chain_before_mutual_destruction": 4,
    "daily_reset_time": "05:00:00",
    "cooldown_seconds": 30,
    "max_event_log": 25,
    "require_station_match": True,
    "require_key_for_launch": False,
    "penalties": {
        "first_strike_target_minutes": 30,
        "retaliator_extra_minutes": 15,
        "retaliation_target_minutes": 30,
        "reattacker_extra_minutes": 15,
        "reattack_target_minutes": 45,
    },
    "stations": {
        "station_1": {"name": "Mom Command", "commander": "Mom", "enabled": True, "key_entity": ""},
        "station_2": {"name": "Dad Command", "commander": "Dad", "enabled": True, "key_entity": ""},
        "station_3": {"name": "Henry Command", "commander": "Henry", "enabled": True, "key_entity": ""},
        "station_4": {"name": "Marc Command", "commander": "Marc", "enabled": True, "key_entity": ""},
        "station_5": {"name": "Maggie Command", "commander": "Maggie", "enabled": True, "key_entity": ""},
    },
    "dns": {
        "enabled": False,
        "provider": "custom_services",
        "enforcement_mode": "disabled",
        "mutual_destruction_scope": "default_targets",
        "custom_services": {"people": {}, "groups": {}},
    },
}
