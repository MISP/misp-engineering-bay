/* Values editor: paginated list of cluster values with search, expand/collapse, edit. */

const PAGE_SIZE = 50;
let allValues = [];
let filteredValues = [];
let currentPage = 0;
let expandedValueIndex = -1;
let activeMetaEditor = null;
let activeRelatedEditor = null;
let valuesOnChange = null;

function initValuesEditor(values, onChange) {
    allValues = values || [];
    valuesOnChange = onChange;
    expandedValueIndex = -1;
    filterValues();
}

function getValues() {
    return allValues.map(v => {
        const clean = { ...v };
        delete clean._origIndex;
        return clean;
    });
}

function filterValues() {
    const q = (document.getElementById('values-search')?.value || '').toLowerCase();
    if (q) {
        filteredValues = allValues.filter((v, i) => {
            v._origIndex = i;
            return (v.value || '').toLowerCase().includes(q) ||
                   (v.description || '').toLowerCase().includes(q);
        });
    } else {
        filteredValues = allValues.map((v, i) => { v._origIndex = i; return v; });
    }
    currentPage = 0;
    renderValues();
}

function renderValues() {
    const container = document.getElementById('values-list');
    const paginationEl = document.getElementById('values-pagination');
    if (!container) return;

    // Update count badge
    const badge = document.getElementById('values-count-badge');
    if (badge) badge.textContent = `${allValues.length} clusters`;

    const totalPages = Math.max(1, Math.ceil(filteredValues.length / PAGE_SIZE));
    if (currentPage >= totalPages) currentPage = totalPages - 1;
    const start = currentPage * PAGE_SIZE;
    const pageValues = filteredValues.slice(start, start + PAGE_SIZE);

    if (pageValues.length === 0) {
        container.innerHTML = '<div class="empty-hint">No clusters match your search.</div>';
        paginationEl.innerHTML = '';
        return;
    }

    container.innerHTML = pageValues.map((val, pageIdx) => {
        const idx = val._origIndex;
        const isExpanded = idx === expandedValueIndex;
        const metaCount = val.meta ? Object.keys(val.meta).length : 0;
        const relCount = val.related ? val.related.length : 0;
        const revokedClass = val.revoked ? ' value-revoked' : '';

        return `
        <div class="value-card${isExpanded ? '' : ' collapsed'}${revokedClass}" data-index="${idx}">
            <div class="value-card-header" onclick="toggleValue(${idx})">
                <span class="collapse-toggle">&#9660;</span>
                <span class="value-name">${escapeHtml(val.value || '(unnamed)')}</span>
                <span class="value-meta-hint">
                    ${val.uuid ? '<span title="Has UUID">&#128273;</span>' : ''}
                    ${metaCount ? `${metaCount} meta` : ''}
                    ${relCount ? `${relCount} rel` : ''}
                    ${val.revoked ? '<span style="color:var(--danger)">revoked</span>' : ''}
                </span>
                <div class="value-card-actions">
                    <button class="btn btn-icon btn-small" onclick="event.stopPropagation();duplicateValue(${idx})" title="Duplicate">&#9776;</button>
                    <button class="btn btn-icon btn-danger btn-small" onclick="event.stopPropagation();removeValue(${idx})" title="Remove">&times;</button>
                </div>
            </div>
            ${isExpanded ? `<div class="value-card-body" id="value-body-${idx}"></div>` : ''}
        </div>`;
    }).join('');

    // If a value is expanded, render its edit form
    if (expandedValueIndex >= 0) {
        const body = document.getElementById(`value-body-${expandedValueIndex}`);
        if (body) renderValueForm(body, expandedValueIndex);
    }

    // Pagination
    if (totalPages <= 1) {
        paginationEl.innerHTML = '';
        return;
    }
    let pagHtml = `<button ${currentPage === 0 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">&laquo;</button>`;
    pagHtml += `<span class="page-info">Page ${currentPage + 1} of ${totalPages}</span>`;
    pagHtml += `<button ${currentPage >= totalPages - 1 ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    paginationEl.innerHTML = pagHtml;
}

function goToPage(page) {
    currentPage = page;
    renderValues();
}

function toggleValue(idx) {
    if (expandedValueIndex === idx) {
        expandedValueIndex = -1;
    } else {
        expandedValueIndex = idx;
    }
    renderValues();
}

function renderValueForm(container, idx) {
    const val = allValues[idx];
    container.innerHTML = `
        <div class="form-group">
            <label class="form-label">Cluster Name</label>
            <input type="text" class="form-input" id="val-value-${idx}" value="${escapeHtml(val.value || '')}">
        </div>
        <div class="form-group">
            <label class="form-label">Description</label>
            <textarea class="form-input form-textarea" id="val-desc-${idx}" rows="3">${escapeHtml(val.description || '')}</textarea>
        </div>
        <div class="form-row">
            <div class="form-group flex-1">
                <label class="form-label">UUID</label>
                <div class="input-group">
                    <input type="text" class="form-input" id="val-uuid-${idx}" value="${escapeHtml(val.uuid || '')}" readonly>
                    <button class="btn btn-small" onclick="generateValueUUID(${idx})">Generate</button>
                </div>
            </div>
            <div class="form-group">
                <label class="toggle-label" style="margin-top:24px">
                    <input type="checkbox" id="val-revoked-${idx}" ${val.revoked ? 'checked' : ''}>
                    <span>Revoked</span>
                </label>
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Meta</label>
            <div id="val-meta-${idx}"></div>
        </div>
        <div class="form-group">
            <label class="form-label">Related</label>
            <div id="val-related-${idx}"></div>
        </div>
        <div style="margin-top:12px;display:flex;justify-content:flex-end">
            <button class="btn btn-primary btn-small" onclick="toggleValue(${idx})">Done</button>
        </div>
    `;

    // Bind simple field changes
    const valueInput = document.getElementById(`val-value-${idx}`);
    const descInput = document.getElementById(`val-desc-${idx}`);
    const uuidInput = document.getElementById(`val-uuid-${idx}`);
    const revokedInput = document.getElementById(`val-revoked-${idx}`);

    function syncFields() {
        val.value = valueInput.value;
        val.description = descInput.value || undefined;
        val.uuid = uuidInput.value || undefined;
        val.revoked = revokedInput.checked || undefined;
        // Clean up undefined fields
        if (!val.description) delete val.description;
        if (!val.uuid) delete val.uuid;
        if (!val.revoked) delete val.revoked;
        notifyChange();
    }

    valueInput.addEventListener('input', syncFields);
    descInput.addEventListener('input', syncFields);
    revokedInput.addEventListener('change', syncFields);

    // Meta editor
    activeMetaEditor = createMetaEditor(
        document.getElementById(`val-meta-${idx}`),
        val.meta ? JSON.parse(JSON.stringify(val.meta)) : {},
        () => {
            val.meta = activeMetaEditor.getMeta();
            if (Object.keys(val.meta).length === 0) delete val.meta;
            notifyChange();
        }
    );

    // Related editor
    activeRelatedEditor = createRelatedEditor(
        document.getElementById(`val-related-${idx}`),
        val.related ? JSON.parse(JSON.stringify(val.related)) : [],
        () => {
            val.related = activeRelatedEditor.getRelated();
            if (val.related.length === 0) delete val.related;
            notifyChange();
        }
    );
}

function notifyChange() {
    if (valuesOnChange) valuesOnChange();
}

function addValue() {
    const newVal = { value: '' };
    allValues.push(newVal);
    expandedValueIndex = allValues.length - 1;
    // Auto-generate UUID for the new cluster
    fetch('/api/uuid').then(r => r.json()).then(data => {
        newVal.uuid = data.uuid;
        const input = document.getElementById(`val-uuid-${expandedValueIndex}`);
        if (input) input.value = data.uuid;
        notifyChange();
    });
    filterValues();
    // Scroll to bottom of values
    const container = document.getElementById('values-list');
    if (container) {
        const totalPages = Math.ceil(filteredValues.length / PAGE_SIZE);
        currentPage = totalPages - 1;
        renderValues();
    }
    notifyChange();
}

function removeValue(idx) {
    allValues.splice(idx, 1);
    if (expandedValueIndex === idx) expandedValueIndex = -1;
    else if (expandedValueIndex > idx) expandedValueIndex--;
    filterValues();
    notifyChange();
}

function duplicateValue(idx) {
    const copy = JSON.parse(JSON.stringify(allValues[idx]));
    delete copy.uuid;  // New copy shouldn't share UUID
    copy.value = (copy.value || '') + ' (copy)';
    allValues.splice(idx + 1, 0, copy);
    expandedValueIndex = idx + 1;
    filterValues();
    notifyChange();
}

function generateValueUUID(idx) {
    fetch('/api/uuid').then(r => r.json()).then(data => {
        allValues[idx].uuid = data.uuid;
        const input = document.getElementById(`val-uuid-${idx}`);
        if (input) input.value = data.uuid;
        notifyChange();
    });
}

function bulkGenerateUUIDs() {
    const promises = [];
    let count = 0;
    for (const val of allValues) {
        if (!val.uuid) {
            count++;
            promises.push(
                fetch('/api/uuid').then(r => r.json()).then(data => {
                    val.uuid = data.uuid;
                })
            );
        }
    }
    if (count === 0) {
        showToast('All values already have UUIDs', 'success');
        return;
    }
    Promise.all(promises).then(() => {
        showToast(`Generated ${count} UUIDs`, 'success');
        renderValues();
        notifyChange();
    });
}

// Bind search
document.addEventListener('DOMContentLoaded', () => {
    const search = document.getElementById('values-search');
    if (search) {
        search.addEventListener('input', debounce(filterValues, 200));
    }
});
