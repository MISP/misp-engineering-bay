/**
 * preview.js — Live JSON preview and validation display.
 *
 * Inline field errors (red borders, error text) only appear on fields the user
 * has interacted with ("touched"). The preview badge and error list always
 * reflect the full validation state so the user can see what still needs work.
 */

let previewTimeout = null;
const touchedFields = new Set();

/** Mark a metadata field as touched so future validation highlights it. */
function markTouched(fieldId) {
    touchedFields.add(fieldId);
}

/** After a save attempt or import, treat every field as touched. */
function markAllTouched() {
    ['tpl-name', 'tpl-description', 'tpl-meta-category', 'tpl-uuid', 'tpl-version', 'attributes'].forEach(
        id => touchedFields.add(id)
    );
}

// Attach touch tracking to the metadata inputs once the DOM is ready.
document.addEventListener('DOMContentLoaded', () => {
    const ids = ['tpl-name', 'tpl-description', 'tpl-meta-category', 'tpl-version'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('blur', () => markTouched(id));
            el.addEventListener('change', () => markTouched(id));
        }
    });
});

function schedulePreviewUpdate() {
    if (previewTimeout) clearTimeout(previewTimeout);
    previewTimeout = setTimeout(updatePreview, 200);
}

async function updatePreview() {
    const tpl = buildTemplateJson();
    const json = JSON.stringify(tpl, null, 2);

    // Update preview pane
    document.getElementById('json-preview').textContent = json;

    // Validate
    try {
        const res = await fetch('/api/templates/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(tpl),
        });
        const result = await res.json();
        updateValidationDisplay(result);
    } catch (err) {
        // Network error — skip validation display
    }
}

function updateValidationDisplay(result) {
    const badge = document.getElementById('validation-badge');
    const errorsDiv = document.getElementById('validation-errors');

    // Clear previous inline highlights
    document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    if (result.valid) {
        const warningCount = result.warnings ? result.warnings.length : 0;
        if (warningCount > 0) {
            badge.innerHTML = `<span class="badge" style="background: var(--warning-bg); color: var(--warning);">Valid (${warningCount} warning${warningCount > 1 ? 's' : ''})</span>`;
        } else {
            badge.innerHTML = '<span class="badge" style="background: var(--success-bg); color: var(--success);">Valid</span>';
        }
    } else {
        badge.innerHTML = `<span class="badge" style="background: var(--danger-bg); color: var(--danger);">${result.errors.length} error${result.errors.length > 1 ? 's' : ''}</span>`;
    }

    // Show errors and warnings in the preview panel (always)
    const items = [];
    if (result.errors && result.errors.length > 0) {
        result.errors.forEach(err => {
            items.push(`<div class="validation-error-item" data-path="${escapeHtml(err.path)}">${escapeHtml(err.path)}: ${escapeHtml(err.message)}</div>`);
            // Only highlight inline if the field has been touched
            highlightFieldError(err.path, err.message);
        });
    }
    if (result.warnings && result.warnings.length > 0) {
        result.warnings.forEach(w => {
            items.push(`<div class="validation-warning-item">${escapeHtml(w.path)}: ${escapeHtml(w.message)}</div>`);
        });
    }

    if (items.length > 0) {
        errorsDiv.innerHTML = items.join('');
        errorsDiv.hidden = false;
    } else {
        errorsDiv.hidden = true;
    }
}

function highlightFieldError(path, message) {
    const fieldMap = {
        'name': 'tpl-name',
        'description': 'tpl-description',
        'meta-category': 'tpl-meta-category',
        'uuid': 'tpl-uuid',
        'version': 'tpl-version',
    };

    const topField = path.split('.')[0];
    const inputId = fieldMap[topField];

    // Skip inline highlight if the user hasn't interacted with this field yet
    if (inputId && !touchedFields.has(inputId)) return;

    if (inputId) {
        const input = document.getElementById(inputId);
        if (input) input.classList.add('is-invalid');
        const errDiv = document.getElementById(`err-${topField}`);
        if (errDiv) errDiv.textContent = message;
    }
}
