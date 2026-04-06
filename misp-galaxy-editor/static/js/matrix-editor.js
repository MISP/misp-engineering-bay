/* Matrix editor: kill chain matrix with drag-and-drop for cluster values. */

let matrixActive = false;
let matrixCurrentScope = '';
let matrixOnChange = null;

function initMatrixEditor(onChange) {
    matrixOnChange = onChange;
}

function toggleMatrixView() {
    matrixActive = !matrixActive;
    const btn = document.getElementById('matrix-view-btn');
    const valuesList = document.getElementById('values-list');
    const valuesToolbar = document.getElementById('values-toolbar');
    const pagination = document.getElementById('values-pagination');
    const matrixContainer = document.getElementById('matrix-container');

    if (matrixActive) {
        btn.textContent = 'List View';
        btn.classList.add('btn-primary');
        valuesList.style.display = 'none';
        valuesToolbar.style.display = 'none';
        pagination.style.display = 'none';
        matrixContainer.style.display = 'block';
        renderMatrix();
    } else {
        btn.textContent = 'Matrix View';
        btn.classList.remove('btn-primary');
        valuesList.style.display = '';
        valuesToolbar.style.display = '';
        pagination.style.display = '';
        matrixContainer.style.display = 'none';
    }
}

function getKillChainOrder() {
    // Read from editor form state
    if (typeof buildKillChainOrder === 'function') {
        return buildKillChainOrder();
    }
    return {};
}

function renderMatrix() {
    const container = document.getElementById('matrix-container');
    if (!container) return;

    const kco = getKillChainOrder();
    const scopes = Object.keys(kco);

    if (scopes.length === 0) {
        container.innerHTML = '<div class="empty-hint">No kill chain scopes defined. Add scopes in the galaxy definition above.</div>';
        return;
    }

    if (!matrixCurrentScope || !scopes.includes(matrixCurrentScope)) {
        matrixCurrentScope = scopes[0];
    }

    const phases = kco[matrixCurrentScope] || [];
    const values = getValues();

    // Build index: which values are in which phase for current scope
    const phaseValues = {};
    const unplaced = [];
    for (const phase of phases) phaseValues[phase] = [];

    for (let i = 0; i < values.length; i++) {
        const val = values[i];
        const kc = val.meta?.kill_chain;
        let placed = false;
        if (Array.isArray(kc)) {
            for (const entry of kc) {
                const [scope, phase] = entry.split(':');
                if (scope === matrixCurrentScope && phaseValues[phase]) {
                    phaseValues[phase].push({ index: i, value: val });
                    placed = true;
                }
            }
        }
        if (!placed) {
            // Check if placed in another scope
            const inOtherScope = Array.isArray(kc) && kc.some(e => {
                const [s] = e.split(':');
                return s !== matrixCurrentScope && scopes.includes(s);
            });
            // Always show in unplaced for this scope if not in this scope
            unplaced.push({ index: i, value: val });
        }
    }

    // Render tabs
    let html = '<div class="matrix-tabs">';
    for (const scope of scopes) {
        html += `<button class="matrix-tab${scope === matrixCurrentScope ? ' active' : ''}" onclick="switchMatrixScope('${escapeHtml(scope)}')">${escapeHtml(scope)}</button>`;
    }
    html += '</div>';
    html += '<div class="section-hint" style="margin-bottom:12px">Drag clusters into columns to assign them to kill chain phases. <strong>Ctrl+drag</strong> to assign a cluster to multiple phases without removing it from its current position.</div>';

    // Render grid
    const colCount = phases.length;
    html += `<div class="matrix-grid" style="grid-template-columns: repeat(${colCount}, minmax(160px, 1fr))">`;

    // Headers
    for (const phase of phases) {
        html += `<div class="matrix-column-header">${escapeHtml(phase)}</div>`;
    }

    // Cells
    for (const phase of phases) {
        const cellValues = phaseValues[phase];
        html += `<div class="matrix-cell" data-scope="${escapeHtml(matrixCurrentScope)}" data-phase="${escapeHtml(phase)}"
                      ondragover="matrixDragOver(event)" ondragleave="matrixDragLeave(event)" ondrop="matrixDrop(event)">`;
        for (const { index, value } of cellValues) {
            html += `<div class="matrix-card" draggable="true" data-index="${index}"
                          ondragstart="matrixDragStart(event)" onclick="toggleValue(${index})"
                          title="${escapeHtml(value.description || '')}">${escapeHtml(value.value || '(unnamed)')}</div>`;
        }
        html += '</div>';
    }
    html += '</div>';

    // Unplaced panel
    html += `<div class="matrix-unplaced">
        <div class="matrix-unplaced-header">
            <span>Unplaced Clusters</span>
            <span class="meta-badge">${unplaced.length}</span>
        </div>
        <div class="matrix-unplaced-list" ondragover="matrixDragOver(event)" ondragleave="matrixDragLeave(event)">`;
    for (const { index, value } of unplaced.slice(0, 200)) {
        html += `<div class="matrix-card" draggable="true" data-index="${index}"
                      ondragstart="matrixDragStart(event)"
                      title="${escapeHtml(value.description || '')}">${escapeHtml(value.value || '(unnamed)')}</div>`;
    }
    if (unplaced.length > 200) {
        html += `<div class="meta-badge">...and ${unplaced.length - 200} more</div>`;
    }
    html += '</div></div>';

    container.innerHTML = html;
}

function switchMatrixScope(scope) {
    matrixCurrentScope = scope;
    renderMatrix();
}

// --- Drag and drop ---

let dragIndex = -1;

function matrixDragStart(e) {
    dragIndex = parseInt(e.target.dataset.index);
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(dragIndex));
}

function matrixDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const cell = e.target.closest('.matrix-cell');
    if (cell) cell.classList.add('drag-over');
}

function matrixDragLeave(e) {
    const cell = e.target.closest('.matrix-cell');
    if (cell) cell.classList.remove('drag-over');
}

function matrixDrop(e) {
    e.preventDefault();
    const cell = e.target.closest('.matrix-cell');
    if (!cell) return;
    cell.classList.remove('drag-over');

    const idx = parseInt(e.dataTransfer.getData('text/plain'));
    if (isNaN(idx)) return;

    const scope = cell.dataset.scope;
    const phase = cell.dataset.phase;
    if (!scope || !phase) return;

    const val = allValues[idx];
    if (!val) return;

    // Ensure meta and kill_chain exist
    if (!val.meta) val.meta = {};
    if (!Array.isArray(val.meta.kill_chain)) val.meta.kill_chain = [];

    const entry = `${scope}:${phase}`;

    // If ctrl held, add without removing old entries for this scope
    if (!e.ctrlKey) {
        // Remove all entries for current scope
        val.meta.kill_chain = val.meta.kill_chain.filter(kc => {
            const [s] = kc.split(':');
            return s !== scope;
        });
    }

    // Add the new entry if not already present
    if (!val.meta.kill_chain.includes(entry)) {
        val.meta.kill_chain.push(entry);
    }

    // Clean up empty meta
    if (val.meta.kill_chain.length === 0) delete val.meta.kill_chain;
    if (Object.keys(val.meta).length === 0) delete val.meta;

    renderMatrix();
    if (matrixOnChange) matrixOnChange();
}
