# MISP Object Template Creator — Requirements & Implementation Plan

## Phase 1: Foundation & Backend Core

### Milestone 1.1: Project Setup
- [ ] Initialize Python project structure (`misp-object-template-creator/`)
- [ ] Create `requirements.txt` with dependencies (flask, jsonschema, requests)
- [ ] Create `config.py` with configurable paths, URLs, and defaults
- [ ] Create `app.py` Flask application skeleton with blueprint registration
- [ ] Add a `README.md` with setup and run instructions

### Milestone 1.2: describeTypes.json Integration
- [ ] Create `describe_types.py` module to fetch and cache `describeTypes.json` from the MISP GitHub repository
- [ ] Bundle a local fallback copy of `describeTypes.json` in `data/` for offline use
- [ ] Parse and expose the following data structures:
  - [ ] Full list of 193 MISP attribute types
  - [ ] Full list of 16 categories
  - [ ] `category_type_mappings` — which types are valid per category
  - [ ] `sane_defaults` — default category and `to_ids` per type
- [ ] Build a reverse mapping: type → list of valid categories
- [ ] Add a refresh mechanism to re-fetch `describeTypes.json` on demand
- [ ] Write unit tests for type/category lookups and mappings

### Milestone 1.3: Validation Engine
- [ ] Create `validator.py` module
- [ ] Implement template-level validation:
  - [ ] `name` — non-empty, lowercase, alphanumeric + hyphens only
  - [ ] `description` — non-empty string
  - [ ] `meta-category` — must be one of the 13 valid enum values
  - [ ] `uuid` — must be valid UUIDv4 format
  - [ ] `version` — must be a positive integer
  - [ ] `attributes` — must contain at least one attribute
  - [ ] `required` — every entry must reference a defined attribute name, no duplicates
  - [ ] `requiredOneOf` — every entry must reference a defined attribute name, no duplicates
- [ ] Implement attribute-level validation:
  - [ ] `misp-attribute` — must exist in `describeTypes.json` types list
  - [ ] `ui-priority` — must be a number
  - [ ] `description` — must be non-empty string
  - [ ] `categories` — each must exist in global categories AND be valid for the chosen `misp-attribute` per `category_type_mappings`
  - [ ] `sane_default` — must be an array of unique strings
  - [ ] `values_list` — must be an array of unique strings
  - [ ] `disable_correlation`, `multiple`, `recommended`, `to_ids` — must be boolean if present
- [ ] Implement warnings (non-blocking):
  - [ ] No `required` or `requiredOneOf` defined
  - [ ] All attributes have `ui-priority: 0`
  - [ ] Insecure hash types used without stronger alternatives
- [ ] Return structured error/warning objects with field path, message, and severity
- [ ] Validate full template against `schema_objects.json` as a final pass
- [ ] Write unit tests covering all validation rules (valid and invalid cases)

### Milestone 1.4: Template Storage & I/O
- [ ] Implement template reader for misp-objects submodule (scan `objects/*/definition.json`)
- [ ] Implement template listing with metadata (name, description, meta-category, attribute count)
- [ ] Implement single template loader (parse and return structured data)
- [ ] Implement template writer (serialize to `definition.json` in output directory, creating `<name>/definition.json`)
- [ ] Implement template deletion (user-created templates only, not submodule)
- [ ] Ensure exported JSON matches the canonical format (sorted keys, 2-space indent)
- [ ] Write unit tests for read/write round-trip fidelity

---

## Phase 2: REST API

### Milestone 2.1: Core API Endpoints
- [ ] `GET /api/describe-types` — return cached describeTypes data
- [ ] `GET /api/meta-categories` — return list of valid meta-categories with descriptions
- [ ] `GET /api/types` — return all MISP attribute types with their valid categories and sane defaults
- [ ] `GET /api/types/<type>/categories` — return valid categories for a specific type

### Milestone 2.2: Template CRUD API
- [ ] `GET /api/templates` — list all templates (submodule + user-created), with filtering by name, meta-category
- [ ] `GET /api/templates/<name>` — return a specific template definition
- [ ] `POST /api/templates` — create a new template (validate → save), return template or validation errors
- [ ] `PUT /api/templates/<name>` — update an existing user-created template
- [ ] `DELETE /api/templates/<name>` — delete a user-created template (refuse for submodule templates)
- [ ] `POST /api/templates/validate` — validate a template payload without saving, return errors/warnings

### Milestone 2.3: API Quality
- [ ] Consistent JSON error response format across all endpoints
- [ ] Proper HTTP status codes (200, 201, 400, 404, 409, 422)
- [ ] Input sanitization on all endpoints
- [ ] Write integration tests for all API endpoints (happy path + error cases)

---

## Phase 3: Web User Interface

### Milestone 3.1: Base Layout & Navigation
- [ ] Create `base.html` with responsive layout, navigation bar, and footer
- [ ] Choose and integrate a minimal CSS framework (e.g., Pico CSS or similar lightweight framework)
- [ ] Set up static file serving (CSS, JS)
- [ ] Implement two main views: Template Editor and Template Browser
- [ ] Add route for editor (`/`) and browser (`/browse`)

### Milestone 3.2: Template Browser View
- [ ] Display all templates in a searchable, sortable table/card grid
- [ ] Show template name, description, meta-category, attribute count, version
- [ ] Add search input filtering by name and description
- [ ] Add meta-category filter dropdown
- [ ] "Clone to editor" button per template to load it for editing as a new template
- [ ] "View JSON" quick-view modal per template

### Milestone 3.3: Template Editor — Metadata Section
- [ ] Name input with real-time validation (lowercase, hyphens, uniqueness check)
- [ ] Description textarea
- [ ] Meta-category dropdown populated from schema enum values
  - [ ] Tooltip per category explaining its purpose
- [ ] UUID field — auto-generated on new template, read-only display, "Regenerate" button
- [ ] Version numeric input (default: 1)
- [ ] Inline validation messages for each field

### Milestone 3.4: Template Editor — Attribute Builder
- [ ] "Add Attribute" button to append a new attribute card
- [ ] Each attribute card contains:
  - [ ] Attribute name input with validation (lowercase, hyphens)
  - [ ] MISP type searchable dropdown (all 193 types)
    - [ ] Show type description on selection
    - [ ] Show default category and `to_ids` from sane_defaults
  - [ ] Description textarea
  - [ ] UI Priority numeric input
  - [ ] Categories multi-select — **dynamically filtered** to only show valid categories for the selected MISP type
    - [ ] Visual indicator showing which categories are valid
  - [ ] Boolean flag toggles: `disable_correlation`, `multiple`, `recommended`, `to_ids`
    - [ ] Tooltip per flag explaining its effect in MISP
  - [ ] Sane defaults — tag/chip input for adding predefined values
  - [ ] Values list — tag/chip input for strict enum values
    - [ ] Guidance note: mutually exclusive intent with sane_default
- [ ] Remove attribute button (with confirmation)
- [ ] Drag-and-drop or up/down reordering of attributes
- [ ] Collapse/expand individual attribute cards
- [ ] Duplicate attribute button (clone an existing attribute as starting point)

### Milestone 3.5: Template Editor — Requirements Section
- [ ] "Required" multi-select populated from currently defined attribute names
- [ ] "Required One Of" multi-select populated from currently defined attribute names
- [ ] Dynamic updates — when attributes are added/removed/renamed, these selects update
- [ ] Visual indicator: attributes not covered by any requirement rule get a subtle warning
- [ ] Prevent selecting the same attribute in both `required` and `requiredOneOf` (it would be redundant)

### Milestone 3.6: Template Editor — Live Preview & Export
- [ ] Side panel (or bottom panel) showing real-time JSON preview
- [ ] Syntax-highlighted, properly formatted JSON output
- [ ] Validation status badge (valid/invalid) with error count
- [ ] Expandable error/warning list with clickable items that scroll to the relevant field
- [ ] "Export JSON" button — downloads `definition.json` file
- [ ] "Copy to Clipboard" button for the JSON output
- [ ] "Save" button — saves to the output directory via API

### Milestone 3.7: Import Functionality
- [ ] "Import JSON" button — file upload that parses and loads a `definition.json` into the editor
- [ ] "Paste JSON" option — textarea modal for pasting raw JSON
- [ ] Validation on import — show errors if the imported JSON has issues, but still load it for fixing
- [ ] "Load from existing" — integrated with browser view (clone button)

### Milestone 3.8: Tooltips & Guidance System
- [ ] Info icon (ⓘ) next to every form field with contextual tooltip
- [ ] Tooltips content:
  - [ ] `name` — "Unique identifier for this object template. Use lowercase letters and hyphens only."
  - [ ] `description` — "A clear, concise explanation of what this object represents and when to use it."
  - [ ] `meta-category` — "The broad category this object belongs to. Determines how it's grouped in the MISP UI."
  - [ ] `uuid` — "Unique identifier for this template. Auto-generated. Only regenerate if creating a completely new template."
  - [ ] `version` — "Increment when modifying an existing template. Start at 1 for new templates."
  - [ ] `misp-attribute` — "The MISP data type for this attribute. Determines validation rules and correlation behavior."
  - [ ] `ui-priority` — "Controls display order in MISP. Higher values = shown first. Use 0 for rarely-used attributes, 1 for standard, 100+ for primary."
  - [ ] `disable_correlation` — "When enabled, MISP will not create correlation links for this attribute. Use for high-volume, low-value fields like timestamps."
  - [ ] `multiple` — "Allow multiple values for this attribute in a single object instance."
  - [ ] `recommended` — "When set to false, this attribute is visually de-emphasized in the MISP UI."
  - [ ] `to_ids` — "If enabled, this attribute will be included in IDS exports (e.g., NIDS/HIDS rules)."
  - [ ] `categories` — "Override the default categories for this attribute. Only categories valid for the selected MISP type are shown."
  - [ ] `sane_default` — "Predefined values shown as a dropdown in MISP for convenience. Users can still enter custom values."
  - [ ] `values_list` — "Strict enumeration — users must choose from these values only. No custom input allowed."
  - [ ] `required` — "Attributes that must always be filled in when creating an object of this type."
  - [ ] `requiredOneOf` — "At least one of these attributes must be filled in. Use when an object has multiple possible identifiers."
- [ ] Inline contextual help for type selection: when a type is picked, show a brief "commonly used in..." hint

---

## Phase 4: Polish & Quality Assurance

### Milestone 4.1: Validation Completeness
- [ ] Verify all 388 existing misp-objects templates load without errors
- [ ] Verify all 388 templates can be re-exported and produce identical JSON (round-trip test)
- [ ] Test edge cases: templates with both `required` and `requiredOneOf`, templates with `values_list`, templates with `sane_default` containing many items
- [ ] Test boundary conditions: empty attributes map, very long names, special characters

### Milestone 4.2: UI/UX Refinement
- [ ] Responsive design — usable on tablet-width screens (1024px minimum)
- [ ] Keyboard navigation — tab between fields, Enter to add items to tag inputs
- [ ] Loading states for async operations (save, validate, import)
- [ ] Confirmation dialogs for destructive actions (delete template, remove attribute)
- [ ] Toast notifications for save success/failure
- [ ] Smooth scroll-to-error when clicking validation messages

### Milestone 4.3: Error Handling & Resilience
- [ ] Graceful degradation when `describeTypes.json` fetch fails (use bundled fallback)
- [ ] Handle corrupt/malformed JSON on import with helpful error messages
- [ ] Prevent data loss — warn before navigating away with unsaved changes
- [ ] Handle concurrent access gracefully (file locking or last-write-wins with warning)

### Milestone 4.4: Documentation
- [ ] API documentation (endpoint reference with request/response examples)
- [ ] User guide with screenshots for the UI workflow
- [ ] Developer setup guide (how to run locally, how to contribute)

---

## Phase Summary

| Phase | Focus | Key Deliverables |
|-------|-------|-----------------|
| **Phase 1** | Foundation | Project structure, describeTypes integration, validation engine, file I/O |
| **Phase 2** | API | Full REST API with CRUD, validation, and type/category lookups |
| **Phase 3** | UI | Template browser, guided editor with attribute builder, live preview, import/export |
| **Phase 4** | Quality | Round-trip testing, UX polish, error handling, documentation |
