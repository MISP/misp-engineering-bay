# MISP Object Template Creator — Product Requirements Document

## 1. Overview

The **MISP Object Template Creator** is a Python-based web application that provides both a graphical user interface and a REST API for creating, editing, validating, and exporting MISP object template definitions. It eliminates the need to manually craft `definition.json` files by offering a guided, schema-aware authoring experience.

### 1.1 Problem Statement

MISP object templates are JSON files that follow a strict schema (`schema_objects.json`). Today, creating or modifying these templates requires:

- Intimate knowledge of the JSON schema and its constraints
- Manual lookup of valid MISP attribute types, categories, and their mappings
- Hand-editing JSON with no validation feedback until a CI check runs
- Risk of typos, invalid type/category combinations, and missing required fields

This friction slows down contributions and increases error rates.

### 1.2 Goals

1. **Lower the barrier** — anyone familiar with MISP concepts should be able to author a valid object template without reading the schema spec.
2. **Enforce correctness** — the tool must make it impossible to produce an invalid template. Validation is real-time, not after-the-fact.
3. **Stay in sync** — attribute types and categories are driven by MISP's canonical `describeTypes.json`, ensuring the tool always reflects the current MISP type system.
4. **Support automation** — a full REST API allows programmatic template creation for CI/CD pipelines or other tooling.

### 1.3 Non-Goals (v1)

- Pushing templates directly to the misp-objects Git repository (export only)
- Managing object relationships (separate schema)
- User authentication / multi-tenancy (single-user local tool)
- Editing templates already deployed on a live MISP instance via its API

---

## 2. Users & Use Cases

| User | Use Case |
|------|----------|
| **Threat intel analyst** | Create a new object template for a novel data source (e.g., a new malware family's config structure) |
| **MISP maintainer** | Review and refine community-submitted templates with instant validation feedback |
| **Automation engineer** | Generate object templates programmatically via the API as part of a CI pipeline |
| **New contributor** | Use the guided UI with tooltips and contextual help to submit their first template |

---

## 3. Data Model

The tool operates on the MISP object template schema. The core data structures are:

### 3.1 Object Template (top-level)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the object (lowercase, hyphens) |
| `description` | string | Yes | Human-readable description of the object's purpose |
| `meta-category` | enum | Yes | One of: `file`, `network`, `financial`, `marine`, `misc`, `mobile`, `internal`, `vulnerability`, `climate`, `iot`, `health`, `followthemoney`, `detection` |
| `uuid` | UUIDv4 | Yes | Unique identifier (auto-generated) |
| `version` | integer | Yes | Schema version, starts at 1 |
| `required` | string[] | No | Attribute names that are always mandatory |
| `requiredOneOf` | string[] | No | At least one of these attributes must be present |
| `attributes` | object | Yes | Map of attribute name → attribute definition |

### 3.2 Attribute Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `misp-attribute` | string | Yes | The MISP attribute type (from `describeTypes.json` types list) |
| `ui-priority` | number | Yes | Display ordering hint (higher = more prominent) |
| `description` | string | Yes | What this attribute represents |
| `disable_correlation` | boolean | No | If true, MISP will not correlate on this attribute |
| `multiple` | boolean | No | If true, multiple values are allowed |
| `recommended` | boolean | No | If false, the attribute is de-emphasized in the MISP UI |
| `to_ids` | boolean | No | Whether this attribute should be used for IDS detection |
| `categories` | string[] | No | Override allowed categories (must be valid per `describeTypes.json` mappings) |
| `sane_default` | string[] | No | Predefined dropdown values for convenience |
| `values_list` | string[] | No | Exhaustive list of allowed values (strict enum) |

### 3.3 describeTypes.json Mapping

The `describeTypes.json` file provides:

- **`types`** — 193 valid MISP attribute types (e.g., `md5`, `ip-src`, `domain`, `text`)
- **`categories`** — 16 valid categories (e.g., `Payload delivery`, `Network activity`)
- **`category_type_mappings`** — which types are valid in which categories
- **`sane_defaults`** — default category and `to_ids` flag for each type

The tool **must** enforce that:
- Every `misp-attribute` value exists in `types`
- Every entry in an attribute's `categories` array exists in `categories`
- Every category listed for an attribute is valid for that `misp-attribute` type per `category_type_mappings`

---

## 4. Architecture

### 4.1 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | Python 3.10+ / Flask | Lightweight, well-known, easy to extend |
| **Frontend** | HTML/CSS/JS (Jinja2 templates + vanilla JS or Alpine.js) | No build step, simple deployment, modern feel |
| **Validation** | jsonschema + custom validators | Schema validation matching `schema_objects.json` |
| **Data source** | `describeTypes.json` (fetched/cached from MISP repo) | Canonical type/category definitions |
| **Export** | JSON file generation | Direct output of valid `definition.json` files |

### 4.2 Component Diagram

```
┌─────────────────────────────────────────────────┐
│                  Browser (UI)                    │
│  ┌───────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Template   │ │Attribute │ │ Live Preview / │  │
│  │ Meta Form  │ │ Builder  │ │ JSON Output    │  │
│  └─────┬──────┘ └────┬─────┘ └───────┬────────┘  │
│        │             │               │           │
│        └─────────────┼───────────────┘           │
│                      │ REST API calls            │
└──────────────────────┼───────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────┐
│              Flask Backend                        │
│  ┌───────────┐ ┌──────────┐ ┌────────────────┐   │
│  │ API Routes│ │Validation│ │DescribeTypes   │   │
│  │ /api/*    │ │ Engine   │ │  Cache/Loader  │   │
│  └───────────┘ └──────────┘ └────────────────┘   │
│  ┌───────────┐ ┌──────────────────────────────┐   │
│  │ Template  │ │ JSON Export / Import Engine   │   │
│  │ Storage   │ │                              │   │
│  └───────────┘ └──────────────────────────────┘   │
└───────────────────────────────────────────────────┘
```

### 4.3 Key Design Decisions

1. **No database** — Templates are stored as JSON files on disk, mirroring the misp-objects repo structure. This makes it trivial to copy output into a PR.
2. **describeTypes.json is fetched once and cached** — On startup (or on-demand refresh), the app pulls the latest `describeTypes.json` from the MISP GitHub repo and caches it locally. A bundled fallback is included for offline use.
3. **Real-time validation** — The UI validates on every change. The API validates on every request. Invalid states are surfaced immediately with actionable error messages.
4. **Progressive disclosure** — The UI shows required fields first, with optional/advanced fields collapsed. Tooltips explain every field.

---

## 5. User Interface Design

### 5.1 Template Editor (Main View)

The main view is a single-page form divided into sections:

#### Section 1: Template Metadata
- **Name** — text input with validation (lowercase, alphanumeric + hyphens, must be unique)
- **Description** — textarea with character guidance
- **Meta-category** — dropdown with the 13 valid values, each with a tooltip explaining its purpose
- **UUID** — auto-generated, shown read-only, with a "regenerate" button
- **Version** — numeric input, defaults to 1

#### Section 2: Attributes Builder
- A dynamic list of attribute cards that can be added, removed, and reordered
- Each attribute card contains:
  - **Attribute name** — text input (the key in the attributes map)
  - **MISP type** — searchable dropdown of all 193 types, with type descriptions shown
  - **Description** — textarea
  - **UI Priority** — numeric input with explanation tooltip
  - **Categories** — multi-select filtered to only show categories valid for the selected MISP type (driven by `category_type_mappings`)
  - **Flags** — toggle switches for `disable_correlation`, `multiple`, `recommended`, `to_ids`
  - **Sane defaults** — tag input for adding predefined values
  - **Values list** — tag input for adding exhaustive enum values (mutually exclusive guidance with sane_default)
- When a MISP type is selected, the UI automatically:
  - Filters the categories dropdown to valid options
  - Shows the default category and `to_ids` value from `sane_defaults`
  - Displays a description of the type

#### Section 3: Requirements Configuration
- **Required attributes** — multi-select from defined attribute names (always mandatory)
- **Required one-of** — multi-select from defined attribute names (at least one must be present)
- Visual indicator showing which attributes are covered by requirements

#### Section 4: Live Preview & Export
- Real-time JSON preview panel showing the current template as it would appear in `definition.json`
- Syntax-highlighted, formatted JSON
- **Validation status** — green/red indicator with detailed error list
- **Export** button — downloads the valid `definition.json`
- **Copy to clipboard** button

### 5.2 Template Browser

- Lists all existing templates from the misp-objects repository (read from the submodule)
- Search/filter by name, meta-category, description
- Click to load any existing template into the editor for viewing or as a starting point (clone)

### 5.3 Guidance & Help System

Every form field includes:
- **Info icon with tooltip** — explains what the field does and its constraints
- **Contextual validation messages** — shown inline next to the field (not just at submit time)
- **Type/category relationship help** — when selecting a MISP type, show which categories it belongs to and what the type is typically used for

---

## 6. REST API

### 6.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/describe-types` | Returns the cached describeTypes data (types, categories, mappings) |
| `GET` | `/api/templates` | List all templates (from misp-objects submodule + user-created) |
| `GET` | `/api/templates/<name>` | Get a specific template definition |
| `POST` | `/api/templates` | Create a new template (validates, saves to working directory) |
| `PUT` | `/api/templates/<name>` | Update an existing template |
| `DELETE` | `/api/templates/<name>` | Delete a user-created template |
| `POST` | `/api/templates/validate` | Validate a template without saving |
| `GET` | `/api/meta-categories` | List valid meta-categories |
| `GET` | `/api/types` | List all MISP attribute types with their allowed categories |
| `GET` | `/api/types/<type>/categories` | Get valid categories for a specific type |

### 6.2 Validation Response Format

```json
{
  "valid": false,
  "errors": [
    {
      "path": "attributes.src-ip.categories[0]",
      "message": "'Payload delivery' is not a valid category for type 'ip-src'",
      "severity": "error"
    },
    {
      "path": "requiredOneOf[2]",
      "message": "'nonexistent-attr' is not defined in attributes",
      "severity": "error"
    }
  ],
  "warnings": [
    {
      "path": "attributes.hash.misp-attribute",
      "message": "md5 is considered insecure; consider also including sha256",
      "severity": "warning"
    }
  ]
}
```

---

## 7. Validation Rules

The tool enforces the following rules in real-time:

### 7.1 Template-Level
1. `name` must be non-empty, lowercase, alphanumeric with hyphens
2. `description` must be non-empty
3. `meta-category` must be one of the 13 valid enum values
4. `uuid` must be a valid UUIDv4
5. `version` must be a positive integer
6. `attributes` must contain at least one attribute
7. Every entry in `required` must reference a defined attribute name
8. Every entry in `requiredOneOf` must reference a defined attribute name
9. No duplicate entries in `required` or `requiredOneOf`

### 7.2 Attribute-Level
1. `misp-attribute` must be one of the 193 types from `describeTypes.json`
2. `ui-priority` must be a number
3. `description` must be non-empty
4. If `categories` is provided, every category must:
   - Exist in the global categories list
   - Be valid for the chosen `misp-attribute` per `category_type_mappings`
5. `sane_default` entries must be unique
6. `values_list` entries must be unique
7. Attribute names should be lowercase with hyphens (warning, not error)

### 7.3 Warnings (non-blocking)
1. No `required` or `requiredOneOf` specified (template has no mandatory attributes)
2. All attributes have `ui-priority: 0` (no prioritization)
3. Using deprecated or insecure hash types without stronger alternatives

---

## 8. Import & Export

### 8.1 Import Sources
- **From misp-objects submodule** — browse and load any existing template as a starting point
- **From JSON file upload** — upload an existing `definition.json` for editing
- **From JSON paste** — paste raw JSON into the editor

### 8.2 Export Formats
- **definition.json** — the standard MISP object template format, ready to be placed in `objects/<name>/definition.json`
- **Directory structure** — optionally export as `<name>/definition.json` to match the repo layout

---

## 9. Technical Specifications

### 9.1 File Structure

```
misp-object-template-creator/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── config.py                   # Configuration (paths, URLs, defaults)
├── describe_types.py           # describeTypes.json loader/cache
├── validator.py                # Template validation engine
├── templates/
│   ├── base.html               # Base layout
│   ├── editor.html             # Main template editor
│   └── browser.html            # Template browser
├── static/
│   ├── css/
│   │   └── style.css           # Application styles
│   └── js/
│       ├── editor.js           # Editor logic (attribute builder, validation)
│       ├── preview.js          # Live JSON preview
│       └── types.js            # Type/category relationship helpers
├── data/
│   └── describeTypes.json      # Cached/fallback describeTypes
└── output/                     # User-created template output directory
```

### 9.2 Dependencies

- `flask` — web framework
- `jsonschema` — JSON schema validation
- `requests` — fetching describeTypes.json
- `uuid` (stdlib) — UUID generation

### 9.3 Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `MISP_OBJECTS_PATH` | `../misp-objects` | Path to misp-objects repository |
| `DESCRIBE_TYPES_URL` | GitHub raw URL | Remote describeTypes.json location |
| `OUTPUT_PATH` | `./output` | Where created templates are saved |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `5000` | Bind port |

---

## 10. Success Criteria

1. A user can create a valid MISP object template in under 5 minutes using only the UI
2. The tool rejects 100% of invalid templates with clear, actionable error messages
3. Every exported `definition.json` passes validation against `schema_objects.json`
4. The API supports full CRUD and can be used from scripts without the UI
5. All 388 existing templates from the misp-objects repo can be loaded and re-exported without modification
