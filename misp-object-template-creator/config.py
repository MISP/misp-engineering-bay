import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Load settings from config.json (not exposed via API/UI)
# ---------------------------------------------------------------------------

_CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

_defaults = {
    "mode": "public",  # "public" or "private"
}

_file_config = {}
if os.path.isfile(_CONFIG_FILE):
    with open(_CONFIG_FILE) as _f:
        _file_config = json.load(_f)


def _cfg(key: str) -> str:
    """Resolve a config value: env var > config.json > default."""
    env_key = key.upper().replace("-", "_")
    if env_key in os.environ:
        return os.environ[env_key]
    if key in _file_config:
        return str(_file_config[key])
    return _defaults.get(key, "")


# ---------------------------------------------------------------------------
# Mode: "public" (default) or "private"
#   public  — save to output/ only
#   private — also allows persisting directly to the misp-objects repo
# ---------------------------------------------------------------------------

MODE = _cfg("mode").lower()
if MODE not in ("public", "private"):
    MODE = "public"

# Path to the misp-objects submodule
MISP_OBJECTS_PATH = os.environ.get(
    "MISP_OBJECTS_PATH",
    os.path.join(BASE_DIR, "..", "misp-objects"),
)

# Local describeTypes.json (updated via CI)
DESCRIBE_TYPES_PATH = os.path.join(BASE_DIR, "data", "describeTypes.json")

# Where user-created templates are saved (public mode output)
OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH",
    os.path.join(BASE_DIR, "output"),
)

# Schema file for validation
SCHEMA_OBJECTS_PATH = os.path.join(MISP_OBJECTS_PATH, "schema_objects.json")

# Flask settings
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5050"))
DEBUG = os.environ.get("DEBUG", "1") == "1"
