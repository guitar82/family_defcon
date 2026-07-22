DOMAIN = "family_defcon"

# Empty defaults keep all real family/person data in family_defcon.yaml.
DEFAULT_PEOPLE = []
DEFAULT_TARGETS = []
DEFAULT_PARENTS = []

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.state"
SIGNAL_UPDATE = f"{DOMAIN}_update"
SIGNAL_TARGET_BUTTONS_UPDATE = f"{DOMAIN}_target_buttons_update"
