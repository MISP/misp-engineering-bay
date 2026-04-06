/* Live JSON preview and validation display. */

let touchedFields = new Set();
let previewTimer = null;
let currentPreviewTab = 'galaxy';

function markTouched(fieldId) {
    touchedFields.add(fieldId);
}

function markAllTouched() {
    document.querySelectorAll('.form-input, .form-select, .form-textarea').forEach(el => {
        if (el.id) touchedFields.add(el.id);
    });
}

function schedulePreviewUpdate() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(updatePreview, 200);
}

function switchPreviewTab(tab) {
    currentPreviewTab = tab;
    document.querySelectorAll('.preview-tab').forEach(b =>
        b.classList.toggle('active', b.dataset.tab === tab)
    );
    updatePreviewDisplay();
}

let lastBundle = null;
let lastValidation = null;

async function updatePreview() {
    if (typeof buildGalaxyBundle !== 'function') return;

    const bundle = buildGalaxyBundle();
    lastBundle = bundle;

    // Update display
    updatePreviewDisplay();

    // Validate
    try {
        const res = await fetch('/api/galaxies/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bundle),
        });
        lastValidation = await res.json();
    } catch (e) {
        lastValidation = { valid: false, errors: [{ path: 'network', message: 'Validation request failed' }], warnings: [] };
    }

    updateValidationDisplay();
}

function updatePreviewDisplay() {
    const preview = document.getElementById('json-preview');
    if (!preview || !lastBundle) return;

    if (currentPreviewTab === 'galaxy') {
        preview.textContent = JSON.stringify(lastBundle.galaxy, null, 2);
    } else {
        // For cluster, limit values display to avoid huge preview
        const cluster = { ...lastBundle.cluster };
        if (cluster.values && cluster.values.length > 20) {
            const shown = cluster.values.slice(0, 20);
            cluster.values = shown;
            cluster._truncated = `Showing 20 of ${lastBundle.cluster.values.length} values`;
        }
        preview.textContent = JSON.stringify(cluster, null, 2);
    }
}

function updateValidationDisplay() {
    const badge = document.getElementById('validation-badge');
    const errorsEl = document.getElementById('validation-errors');
    if (!badge || !errorsEl || !lastValidation) return;

    const { valid, errors, warnings } = lastValidation;

    if (valid && warnings.length === 0) {
        badge.innerHTML = '<span class="badge" style="background:var(--success-bg);color:var(--success)">Valid</span>';
        errorsEl.style.display = 'none';
    } else if (valid && warnings.length > 0) {
        badge.innerHTML = `<span class="badge" style="background:var(--warning-bg);color:var(--warning)">${warnings.length} warning(s)</span>`;
        errorsEl.style.display = 'block';
        errorsEl.innerHTML = warnings.map(w =>
            `<div class="validation-warning-item">${escapeHtml(w.path)}: ${escapeHtml(w.message)}</div>`
        ).join('');
    } else {
        badge.innerHTML = `<span class="badge" style="background:var(--danger-bg);color:var(--danger)">${errors.length} error(s)</span>`;
        errorsEl.style.display = 'block';
        errorsEl.innerHTML = [
            ...errors.map(e => `<div class="validation-error-item" onclick="highlightField('${escapeHtml(e.path)}')">${escapeHtml(e.path)}: ${escapeHtml(e.message)}</div>`),
            ...warnings.map(w => `<div class="validation-warning-item">${escapeHtml(w.path)}: ${escapeHtml(w.message)}</div>`),
        ].join('');
    }

    // Inline field highlights (only touched fields)
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll('.field-error').forEach(el => el.remove());

    for (const e of errors) {
        highlightFieldError(e.path, e.message);
    }
}

function highlightFieldError(path, message) {
    const fieldMap = {
        'galaxy.name': 'galaxy-name',
        'galaxy.description': 'galaxy-description',
        'galaxy.type': 'galaxy-type',
        'galaxy.uuid': 'galaxy-uuid',
        'galaxy.version': 'galaxy-version',
        'galaxy.icon': 'galaxy-icon',
        'galaxy.namespace': 'galaxy-namespace',
        'cluster.name': 'galaxy-name',
        'cluster.description': 'galaxy-description',
        'cluster.uuid': 'galaxy-uuid',
        'cluster.version': 'galaxy-version',
        'cluster.source': 'galaxy-source',
        'cluster.category': 'galaxy-category',
        'cluster.authors': 'authors-wrapper',
        'cluster.values': 'values-list',
        'type': 'galaxy-type',
    };

    const fieldId = fieldMap[path];
    if (!fieldId) return;
    if (!touchedFields.has(fieldId)) return;

    const el = document.getElementById(fieldId);
    if (el) {
        el.classList.add('is-invalid');
    }
}

function highlightField(path) {
    const fieldMap = {
        'galaxy.name': 'galaxy-name',
        'galaxy.description': 'galaxy-description',
        'galaxy.type': 'galaxy-type',
        'galaxy.uuid': 'galaxy-uuid',
        'galaxy.version': 'galaxy-version',
        'cluster.name': 'galaxy-name',
        'cluster.description': 'galaxy-description',
        'cluster.source': 'galaxy-source',
        'cluster.category': 'galaxy-category',
        'type': 'galaxy-type',
    };
    const fieldId = fieldMap[path];
    if (fieldId) {
        const el = document.getElementById(fieldId);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.focus();
        }
    }
}

// Bind blur events for touched tracking
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('blur', (e) => {
        if (e.target.id && (e.target.classList.contains('form-input') || e.target.classList.contains('form-textarea'))) {
            markTouched(e.target.id);
        }
    }, true);

    document.addEventListener('change', (e) => {
        if (e.target.id) markTouched(e.target.id);
        schedulePreviewUpdate();
    }, true);

    document.addEventListener('input', (e) => {
        if (e.target.classList?.contains('form-input') || e.target.classList?.contains('form-textarea')) {
            schedulePreviewUpdate();
        }
    }, true);
});
