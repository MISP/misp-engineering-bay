# MISP Galaxy Editor — Implementation Plan

## Context

The misp-engineering-bay repository already contains a MISP Object Template Creator. The user wants a second tool — a **Galaxy Editor** — that lets users create and edit MISP galaxy definitions and their associated clusters through a web UI and REST API. Galaxies come in two flavours: simple (flat list of values) and matrix-based (values assigned to kill chain phases, visualised as a matrix with tabs/scopes). The misp-galaxy submodule has been added at the repo root.

## Directory

`/home/iglocska/git/misp-engineering-bay/misp-galaxy-editor/`

## File Structure

```
misp-galaxy-editor/
├── app.py                  # Flask routes (UI + API)
├── config.py               # Config: env > config.json > defaults (port 5051)
├── config.json.default     # {"mode": "public"}
├── galaxy_store.py         # Read/write galaxy+cluster file pairs
├── validator.py            # Validation engine
├── galaxy_meta.py          # Reference data: meta keys, namespaces, categories, icons
├── requirements.txt        # flask, jsonschema, pytest
├── run.sh                  # Venv bootstrap + run
├── .gitignore              # venv/, __pycache__/, output/, config.json
├── static/
│   ├── css/style.css       # Full CSS with dark/light themes + matrix styles
│   ├── js/
│   │   ├── utils.js        # escapeHtml, showToast, debounce, fetch helpers
│   │   ├── editor.js       # Galaxy+cluster metadata editor, save/load/export
│   │   ├── values-editor.js # Cluster values list with search/paginate/edit
│   │   ├── meta-editor.js  # Freeform key-value meta editor with autocomplete
│   │   ├── related-editor.js # Relationship editor (dest-uuid, type, tags)
│   │   ├── matrix-editor.js # Kill chain matrix with drag-and-drop
│   │   └── preview.js      # Live JSON preview + validation display
│   └── openapi.json        # OpenAPI 3.0 spec
├── templates/
│   ├── base.html           # Navbar, theme toggle, tooltips, toasts
│   ├── editor.html         # Unified galaxy+cluster editor
│   ├── browser.html        # Browse all 112+ galaxies
│   └── swagger.html        # Swagger UI
├── tests/
│   ├── conftest.py         # Isolated output fixtures, test client, sample bundle
│   ├── test_api_galaxies.py
│   ├── test_api_validation.py
│   └── test_api_persist.py
└── output/                 # Git-ignored user output
    ├── galaxies/
    └── clusters/
```

## Key Design Decisions

### Bundle API Model

Galaxy + cluster are always paired. The API works with a **bundle**:
```json
{
  "galaxy": { "name": "...", "type": "...", "uuid": "...", ... },
  "cluster": { "name": "...", "type": "...", "uuid": "...", "values": [...], ... }
}
```
The `type` field is the binding key and determines the filename. Galaxy and cluster have **separate** names, descriptions, UUIDs, and versions — only `type` is shared.

### Output Directory Layout

```
output/galaxies/<type>.json
output/clusters/<type>.json
```
Mirrors the misp-galaxy repo structure for easy copy.

### Matrix as Integrated View (Not Separate Page)

The matrix editor is integrated into the main editor page as a togglable view mode for kill-chain galaxies. When `kill_chain_order` is defined, a "Matrix View" tab/button appears alongside the values list, letting users switch between list editing and matrix drag-and-drop.

---

## Backend Modules

### `config.py`
Mirror object-template-creator exactly. Differences:
- `PORT` = 5051
- `MISP_GALAXY_PATH` = `../misp-galaxy`
- `SCHEMA_GALAXIES_PATH` / `SCHEMA_CLUSTERS_PATH` from submodule
- Same `MODE` public/private logic

### `galaxy_store.py`
Key functions:
- `list_all_galaxies()` → summary list `[{type, galaxy_name, cluster_name, description, namespace, icon, value_count, has_kill_chain, source}]`
- `get_galaxy(type_name)` → full bundle or None (user output overrides submodule)
- `save_galaxy(bundle)` → write both files to output/
- `persist_galaxy(bundle)` → write to misp-galaxy repo (private mode only)
- `delete_galaxy(type_name)` → delete from output only
- `galaxy_exists_in_submodule(type_name)` / `galaxy_exists_in_output(type_name)`
- `_validate_safe_name(name)` — same regex + realpath check as object-template-creator
- `generate_uuid()`

File naming: filename = `{type}.json` for both galaxy and cluster files.

### `validator.py`
`ValidationResult` class identical to object-template-creator.

**`validate_galaxy(galaxy_dict)`**:
- name, description: required non-empty strings
- type: required, must match SAFE_NAME_RE
- uuid: required, valid UUID
- version: required, positive integer
- icon: optional string
- namespace: optional string
- kill_chain_order: if present, must be object where each value is non-empty array of strings; warn on empty scopes

**`validate_cluster(cluster_dict)`**:
- name, description, type, uuid, version: same rules
- authors: required, non-empty array of strings
- source: required, non-empty string
- category: required, non-empty string
- values: required, non-empty array; each value: `value` required string, uuid valid if present, meta must be object if present, related entries must have dest-uuid and type

**`validate_bundle(bundle)`**:
- Calls both validators
- Cross-validates: `type` must match between galaxy and cluster
- If galaxy has kill_chain_order, validate meta.kill_chain entries in values reference valid `scope:phase` combinations (warning, not error, for flexibility)

### `galaxy_meta.py`
Cached reference data from existing galaxies:
- `get_meta_key_suggestions()` → top meta keys with frequency and typical type (array vs string)
- `get_known_namespaces()` → unique namespaces
- `get_known_categories()` → unique cluster categories
- `get_known_icons()` → unique icon names
- `get_relationship_types()` → unique relationship type strings

---

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/api/config` | Expose mode |
| `GET` | `/api/galaxies` | List all (filters: `?name=`, `?namespace=`, `?has_kill_chain=`) |
| `GET` | `/api/galaxies/<type>` | Get full bundle |
| `POST` | `/api/galaxies` | Create new bundle |
| `PUT` | `/api/galaxies/<type>` | Update bundle |
| `DELETE` | `/api/galaxies/<type>` | Delete from output |
| `POST` | `/api/galaxies/validate` | Validate bundle |
| `POST` | `/api/galaxies/persist` | Write to misp-galaxy repo (private mode) |
| `GET` | `/api/uuid` | Generate UUID |
| `GET` | `/api/meta-suggestions` | Reference data for autocomplete |

---

## Frontend Design

### Editor Page (`/`) — Unified Galaxy + Cluster Editor

**Left column (scrollable form):**

1. **Shared section**: `type` field (auto-slugified, used as filename and binding key)

2. **Galaxy Definition section**: name, description, uuid (+generate), version, icon (searchable dropdown), namespace (dropdown with autocomplete)
   - Toggle: "Matrix galaxy (uses kill chains)" — reveals kill chain order editor
   - **Kill chain order editor**: List of scopes, each with ordered phases. Add/remove scopes, add/remove/reorder phases within scopes.

3. **Cluster Header section**: name, description, uuid (+generate), version, source, category (autocomplete), authors (tag input)

4. **Cluster Values section**: Managed by `values-editor.js`
   - Search bar + value count badge
   - Paginated/virtual list of values (compact one-line rows)
   - Click to expand inline: value, description, uuid, revoked flag, meta (via meta-editor), related (via related-editor)
   - Add Value button, bulk "generate missing UUIDs" button
   - When galaxy has kill_chain_order: toggle "Matrix View" button switches to matrix drag-and-drop

5. **Actions section**: Save, Persist to Repository (private mode), Export JSON, Copy JSON, Import JSON, Load Existing

**Right column (sticky):**
- Live JSON preview with tabs: Galaxy / Cluster
- Validation badge + error/warning list
- Debounced 200ms updates

### Matrix View (within editor page, toggled)

When active, replaces the values list with:
- **Tab bar**: One tab per kill chain scope (e.g., "Windows", "Linux")
- **Column grid**: Phases as columns, ordered per kill_chain_order
- **Cards in cells**: Cluster values placed by their `meta.kill_chain` entries
- **Unplaced panel**: Values without kill_chain assignment for current scope
- **Drag-and-drop**: Drag cards between cells (moves assignment) or from unplaced panel into cells. Ctrl+drag to add to multiple phases without removing.
- Click card to open edit form (same as expanded value in list view)

Implementation: CSS Grid, HTML5 Drag and Drop API, no library.

### Browser Page (`/browse`)

Card grid of all 112+ galaxies with search/filter by name, namespace. Each card shows: galaxy name, type, description, namespace badge, icon, value count, kill-chain indicator. Actions: View JSON, Load in Editor, Clone.

### Values Editor Details

For large clusters (1000+ values), use **client-side pagination** (50 values per page) with search filtering. The full values array is held in JS memory. Virtual scrolling is complex for variable-height rows — pagination is simpler and sufficient.

### Meta Editor Component

Renders as a list of key-value rows:
- Key: text input with autocomplete from `/api/meta-suggestions`
- Value: smart input based on known key type — array keys (refs, synonyms, kill_chain) get tag input; string keys get text input; unknown keys default to text with array toggle
- Add/remove row buttons

### Related Editor Component

List of relationship rows:
- dest-uuid (text input), type (text input with suggestions dropdown), tags (tag input)
- Add/remove row buttons

---

## Implementation Phases

### Phase 1: Skeleton + Config + Store + Browse API
- Directory structure, run.sh, config.py, .gitignore, requirements.txt, config.json.default
- `galaxy_store.py`: list_all_galaxies(), get_galaxy()
- `galaxy_meta.py`: reference data getters
- `app.py`: UI routes with stub templates, GET /api/galaxies, GET /api/galaxies/<type>, GET /api/meta-suggestions, GET /api/config, GET /api/uuid
- `templates/base.html`, `templates/browser.html`
- `static/css/style.css` (adapted from object-template-creator)
- `static/js/utils.js`
- `tests/conftest.py`, `tests/test_api_galaxies.py`

### Phase 2: Validator + CRUD API
- `validator.py`: validate_galaxy, validate_cluster, validate_bundle, validate_against_schema
- `galaxy_store.py`: save_galaxy, delete_galaxy, persist_galaxy
- POST/PUT/DELETE /api/galaxies, POST /api/galaxies/validate, POST /api/galaxies/persist
- `tests/test_api_validation.py`, `tests/test_api_persist.py`

### Phase 3: Editor UI — Galaxy + Cluster Metadata
- `templates/editor.html`: form sections
- `static/js/editor.js`: form management, buildGalaxyBundle(), save/export/import/load
- `static/js/preview.js`: live preview with galaxy/cluster tabs
- Kill chain order editor (inline scope/phase manager)

### Phase 4: Values Editor + Meta + Related
- `static/js/values-editor.js`: paginated list, search, expand/edit, add/remove
- `static/js/meta-editor.js`: freeform key-value with autocomplete
- `static/js/related-editor.js`: relationship rows
- Bulk operations (add value, generate UUIDs)

### Phase 5: Matrix Editor
- `static/js/matrix-editor.js`: tab bar, CSS Grid matrix, drag-and-drop, unplaced panel
- Matrix-specific CSS
- Performance testing with ATT&CK data (1,242 values, 15 scopes)

### Phase 6: Polish
- OpenAPI spec, Swagger UI
- README.md
- Edge case tests, large cluster testing
- GitHub Actions workflow update

---

## Verification

1. `./run.sh` boots on port 5051
2. Browse page shows all 112 galaxies from submodule
3. Can load any galaxy (including ATT&CK) in editor, see both galaxy+cluster JSON in preview
4. Can create a new simple galaxy with values, save, reload
5. Can create a matrix galaxy with kill chains, assign values via drag-and-drop
6. Validation catches missing fields, type mismatches, invalid UUIDs
7. Private mode persist writes to misp-galaxy submodule
8. All tests pass: `./venv/bin/python -m pytest tests/ -v`

## Reference Files

- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/app.py` — Flask route patterns
- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/template_store.py` — Store module patterns
- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/validator.py` — ValidationResult pattern
- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/config.py` — Config loading pattern
- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/static/css/style.css` — CSS theme system
- `/home/iglocska/git/misp-engineering-bay/misp-object-template-creator/tests/conftest.py` — Test fixture patterns
- `/home/iglocska/git/misp-engineering-bay/misp-galaxy/schema_galaxies.json` — Galaxy schema
- `/home/iglocska/git/misp-engineering-bay/misp-galaxy/schema_clusters.json` — Cluster schema
