import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the misp-objects submodule
MISP_OBJECTS_PATH = os.environ.get(
    "MISP_OBJECTS_PATH",
    os.path.join(BASE_DIR, "..", "misp-objects"),
)

# Local describeTypes.json (updated via CI)
DESCRIBE_TYPES_PATH = os.path.join(BASE_DIR, "data", "describeTypes.json")

# Where user-created templates are saved
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
