# MISP Galaxy Editor

A web application and REST API for creating, editing, validating, and exporting [MISP galaxy](https://www.misp-project.org/galaxy.html) definitions and their associated cluster collections. Provides a guided authoring experience for both simple galaxies and matrix-style kill chain galaxies (like ATT&CK).

Each MISP galaxy consists of two paired files: a **galaxy definition** (metadata, icon, namespace, kill chain layout) and a **cluster collection** (the actual clusters — entries with values, descriptions, meta fields, and relationships). The editor treats these as a single entity — you fill in the galaxy metadata once and the cluster collection file is populated automatically.

## Features

- **Unified editor** — galaxy metadata (name, description, category, source, authors, icon, namespace) is entered once and shared across both the galaxy definition and cluster collection files
- **Cluster editor** with search, pagination, and inline editing — each cluster entry supports freeform meta fields and relationships
- **Matrix editor** with drag-and-drop for kill chain galaxies — assign clusters to phases across multiple scopes/tabs (e.g., ATT&CK matrices per platform)
- **Freeform meta editor** with autocomplete for 80+ known meta keys
- **Relationship editor** for managing cluster-to-cluster links (50+ known relationship types)
- **Real-time validation** with live JSON preview (Galaxy / Cluster Collection tabs)
- **Galaxy browser** — explore all 112+ existing galaxies with search and filtering
- **REST API** — full CRUD for programmatic galaxy management
- **Import/export** — upload, paste, or download galaxy bundles
- **Light/dark theme** with persistent toggle
- **Swagger UI** at `/docs` for interactive API documentation

## Prerequisites

- Python 3.10+
- The `misp-galaxy` submodule checked out (included in this repo)

## Quick Start

```bash
# Clone the repo (with submodules)
git clone --recurse-submodules <repo-url>
cd misp-engineering-bay/misp-galaxy-editor

# Run (creates venv, installs deps, starts server)
./run.sh
```

The app starts at **http://127.0.0.1:5051**.

### Manual Setup

```bash
cd misp-galaxy-editor

# Create virtual environment
python3 -m venv venv

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Start the server
./venv/bin/python app.py
```

## Configuration

Copy the default configuration file and edit as needed:

```bash
cp config.json.default config.json
```

`config.json` is git-ignored so your local settings won't be committed. Available options:

| Key | Default | Description |
|-----|---------|-------------|
| `mode` | `"public"` | `"public"` — save to output/ only. `"private"` — also allows persisting directly to the misp-galaxy repo. |

Environment variables override `config.json`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODE` | `public` | Same as `config.json` `mode` |
| `MISP_GALAXY_PATH` | `../misp-galaxy` | Path to the misp-galaxy repository |
| `OUTPUT_PATH` | `./output` | Where user-created galaxies are saved |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `5051` | Bind port |
| `DEBUG` | `1` | Enable Flask debug mode (`1` or `0`) |

Example:

```bash
PORT=8080 HOST=0.0.0.0 ./run.sh
```

## Usage

### Web UI

- **/** — Galaxy editor. Create new galaxies or load/clone existing ones.
- **/browse** — Browse all existing MISP galaxies with search and filtering.
- **/docs** — Interactive Swagger UI for the REST API.

#### Creating a Galaxy

1. Set the **Type** field (the binding key between galaxy and cluster collection, used as the filename for both).
2. Fill in the **Galaxy Definition** — name, description, category, source, authors, UUID, version, icon, namespace. These fields are shared: the cluster collection file is populated from them automatically.
3. Optionally enable **Matrix galaxy** to define kill chain scopes and phases.
4. Add **Clusters** — each cluster entry can have a value (name), description, UUID, freeform meta fields, and relationships to other clusters.
5. For matrix galaxies, use **Matrix View** to drag-and-drop clusters onto kill chain phases.
6. Review the live JSON preview (Galaxy / Cluster Collection tabs) and validation status.
7. Click **Save Galaxy** or **Export JSON**.

#### Matrix Editor

For galaxies with kill chain order:
- Switch between scopes using the **tab bar** (e.g., "attack-Windows", "attack-Linux")
- **Drag** clusters from the unplaced panel into matrix columns (phases)
- **Ctrl+drag** to assign a cluster to multiple phases without removing it from others
- Click a card to expand and edit the cluster inline

### REST API

Base URL: `http://127.0.0.1:5051/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config` | Non-sensitive configuration |
| `GET` | `/api/galaxies` | List all galaxies (filterable by `name`, `namespace`, `has_kill_chain`) |
| `GET` | `/api/galaxies/<type>` | Get a galaxy bundle (galaxy + cluster) |
| `POST` | `/api/galaxies` | Create a new galaxy |
| `PUT` | `/api/galaxies/<type>` | Update a galaxy |
| `DELETE` | `/api/galaxies/<type>` | Delete a user-created galaxy |
| `POST` | `/api/galaxies/validate` | Validate without saving |
| `POST` | `/api/galaxies/persist` | Write to misp-galaxy repo (private mode) |
| `GET` | `/api/meta-suggestions` | Reference data for autocomplete |
| `GET` | `/api/uuid` | Generate a new UUIDv4 |

See `/docs` for the full OpenAPI specification with request/response examples.

## Running Tests

```bash
./venv/bin/python -m pytest tests/ -v
```

## Project Structure

```
misp-galaxy-editor/
├── app.py                 # Flask application and API routes
├── config.py              # Configuration
├── galaxy_store.py        # Galaxy+cluster file I/O
├── galaxy_meta.py         # Reference data (meta keys, namespaces, icons, etc.)
├── validator.py           # Bundle validation engine
├── run.sh                 # Quick-start script (creates venv, runs app)
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/style.css      # Application styles (light + dark themes)
│   ├── js/
│   │   ├── utils.js       # Shared utilities
│   │   ├── editor.js      # Main editor logic
│   │   ├── values-editor.js # Cluster list management
│   │   ├── meta-editor.js # Freeform key-value meta editor
│   │   ├── related-editor.js # Relationship editor
│   │   ├── matrix-editor.js # Kill chain matrix drag-and-drop
│   │   └── preview.js     # Live JSON preview + validation
│   └── openapi.json       # OpenAPI 3.0 specification
├── templates/             # Jinja2 HTML templates
├── tests/                 # API test suite (73 tests)
└── output/                # User-created galaxies (git-ignored)
    ├── galaxies/
    └── clusters/
```

## License

See the repository root for license information.
