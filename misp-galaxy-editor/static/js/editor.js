/* Main editor logic: galaxy+cluster metadata, save/load/export/import. */

let isEditingExisting = false;
let originalGalaxyVersion = null;
let clusterUUID = '';  // Auto-managed, not shown in UI
let authorsTagInput = null;
let loadGalaxiesList = [];

// --- Initialization ---

document.addEventListener('DOMContentLoaded', async () => {
    // Generate initial UUIDs
    await regenerateUUID('galaxy-uuid');
    // Auto-generate cluster UUID (not shown in UI)
    try {
        const data = await fetch('/api/uuid').then(r => r.json());
        clusterUUID = data.uuid;
    } catch (e) {
        clusterUUID = '';
    }

    // Load suggestions for autocomplete
    try {
        const suggestions = await fetch('/api/meta-suggestions').then(r => r.json());
        populateDatalist('namespace-suggestions', suggestions.namespaces);
        populateDatalist('icon-suggestions', suggestions.icons);
        populateDatalist('category-suggestions', suggestions.categories);
        initMetaSuggestions(suggestions.meta_keys);
        initRelationshipSuggestions(suggestions.relationship_types);
    } catch (e) {
        console.error('Failed to load suggestions', e);
    }

    // Setup authors tag input
    authorsTagInput = setupTagInput('authors-wrapper', 'authors-input', 'authors-tags', 'schedulePreviewUpdate');

    // Init values editor
    initValuesEditor([], schedulePreviewUpdate);

    // Init matrix editor
    initMatrixEditor(schedulePreviewUpdate);

    // Check URL params for load/clone
    const params = new URLSearchParams(window.location.search);
    const loadType = params.get('load');
    const cloneType = params.get('clone');
    if (loadType) {
        await loadGalaxyByType(loadType, false);
    } else if (cloneType) {
        await loadGalaxyByType(cloneType, true);
    }

    // Initial preview
    schedulePreviewUpdate();
});

function populateDatalist(id, values) {
    const dl = document.getElementById(id);
    if (!dl) return;
    dl.innerHTML = '';
    for (const v of values) {
        const opt = document.createElement('option');
        opt.value = v;
        dl.appendChild(opt);
    }
}

// --- UUID generation ---

async function regenerateUUID(fieldId) {
    try {
        const data = await fetch('/api/uuid').then(r => r.json());
        document.getElementById(fieldId).value = data.uuid;
        schedulePreviewUpdate();
    } catch (e) {
        console.error('Failed to generate UUID', e);
    }
}

// --- Kill chain order editor ---

function toggleKillChain() {
    const checked = document.getElementById('kill-chain-toggle').checked;
    document.getElementById('kill-chain-editor').style.display = checked ? 'block' : 'none';
    // Show/hide matrix view button
    document.getElementById('matrix-view-btn').style.display = checked ? '' : 'none';
    if (!checked && matrixActive) toggleMatrixView();
    // Auto-create a default scope if none exist
    if (checked && document.querySelectorAll('.kc-scope').length === 0) {
        const type = document.getElementById('galaxy-type').value.trim() || 'default';
        addKillChainScope(type, []);
    }
    schedulePreviewUpdate();
}

function addKillChainScope(name, phases) {
    const container = document.getElementById('kill-chain-scopes');
    const scope = document.createElement('div');
    scope.className = 'kc-scope';
    scope.innerHTML = `
        <div class="kc-scope-header">
            <label class="form-label" style="margin-bottom:0;white-space:nowrap">Scope
                <span class="tooltip-trigger" data-tooltip="Scope name groups phases into a tab. For single-scope galaxies, use the galaxy type. For multi-scope (e.g., ATT&CK per platform), add multiple scopes.">&#9432;</span>
            </label>
            <input type="text" class="form-input" placeholder="Scope name (e.g. attack-Windows)" value="${escapeHtml(name || '')}">
            <button class="btn btn-icon btn-danger btn-small" onclick="removeKillChainScope(this)" title="Remove scope">&times;</button>
        </div>
        <div class="kc-phases"></div>
        <button class="btn btn-small" onclick="addKillChainPhase(this.previousElementSibling)" style="margin-top:6px">+ Add Phase</button>
    `;
    container.appendChild(scope);

    const phasesContainer = scope.querySelector('.kc-phases');
    if (phases && phases.length) {
        for (const phase of phases) {
            addKillChainPhase(phasesContainer, phase);
        }
    }

    // Bind scope name change
    scope.querySelector('.kc-scope-header input').addEventListener('input', schedulePreviewUpdate);
}

function removeKillChainScope(btn) {
    btn.closest('.kc-scope').remove();
    // If all scopes removed, add a default one back
    if (document.querySelectorAll('.kc-scope').length === 0) {
        const type = document.getElementById('galaxy-type').value.trim() || 'default';
        addKillChainScope(type, []);
    }
    schedulePreviewUpdate();
}

function addKillChainPhase(container, value) {
    const phase = document.createElement('div');
    phase.className = 'kc-phase';
    phase.draggable = true;
    phase.innerHTML = `
        <span class="drag-handle">&#9776;</span>
        <input type="text" value="${escapeHtml(value || '')}" placeholder="Phase name">
        <button class="btn btn-icon btn-danger btn-small" onclick="this.closest('.kc-phase').remove();schedulePreviewUpdate()" style="font-size:12px">&times;</button>
    `;
    container.appendChild(phase);

    phase.querySelector('input').addEventListener('input', schedulePreviewUpdate);

    // Drag-and-drop reordering for phases
    phase.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        phase.classList.add('dragging');
    });
    phase.addEventListener('dragend', () => {
        phase.classList.remove('dragging');
        schedulePreviewUpdate();
    });
    phase.addEventListener('dragover', (e) => {
        e.preventDefault();
        const dragging = container.querySelector('.dragging');
        if (dragging && dragging !== phase) {
            const rect = phase.getBoundingClientRect();
            const mid = rect.top + rect.height / 2;
            if (e.clientY < mid) {
                container.insertBefore(dragging, phase);
            } else {
                container.insertBefore(dragging, phase.nextSibling);
            }
        }
    });
}

function buildKillChainOrder() {
    const kco = {};
    document.querySelectorAll('.kc-scope').forEach(scope => {
        const name = scope.querySelector('.kc-scope-header input').value.trim();
        if (!name) return;
        const phases = [];
        scope.querySelectorAll('.kc-phase input').forEach(inp => {
            const v = inp.value.trim();
            if (v) phases.push(v);
        });
        if (phases.length) kco[name] = phases;
    });
    return kco;
}

function getAuthorTags() {
    const container = document.getElementById('authors-tags');
    if (!container) return [];
    const tags = Array.from(container.querySelectorAll('.tag-item'))
        .map(el => el.dataset.value)
        .filter(Boolean);
    // Also capture any uncommitted text in the input field
    const input = document.getElementById('authors-input');
    if (input && input.value.trim()) {
        const pending = input.value.trim();
        if (!tags.includes(pending)) tags.push(pending);
    }
    return tags;
}

// --- Build bundle from form state ---

function buildGalaxyBundle() {
    const name = document.getElementById('galaxy-name').value.trim();
    const description = document.getElementById('galaxy-description').value.trim();
    const type = document.getElementById('galaxy-type').value.trim();
    const version = parseInt(document.getElementById('galaxy-version').value) || 1;

    const galaxy = { name, description, type,
        uuid: document.getElementById('galaxy-uuid').value.trim(),
        version,
    };

    const icon = document.getElementById('galaxy-icon').value.trim();
    if (icon) galaxy.icon = icon;

    const namespace = document.getElementById('galaxy-namespace').value.trim();
    if (namespace) galaxy.namespace = namespace;

    if (document.getElementById('kill-chain-toggle').checked) {
        const kco = buildKillChainOrder();
        if (Object.keys(kco).length) galaxy.kill_chain_order = kco;
    }

    // Cluster collection mirrors galaxy metadata
    const cluster = {
        name,
        description,
        type,
        uuid: clusterUUID,
        version,
        source: document.getElementById('galaxy-source').value.trim(),
        category: document.getElementById('galaxy-category').value.trim(),
        authors: getAuthorTags(),
        values: getValues(),
    };

    return { galaxy, cluster };
}

// --- Load galaxy into editor ---

function loadGalaxyIntoEditor(bundle, isClone) {
    const g = bundle.galaxy;
    const c = bundle.cluster;

    document.getElementById('galaxy-type').value = isClone ? '' : (g.type || '');
    document.getElementById('galaxy-name').value = g.name || '';
    document.getElementById('galaxy-description').value = g.description || '';
    document.getElementById('galaxy-uuid').value = isClone ? '' : (g.uuid || '');
    document.getElementById('galaxy-version').value = isClone ? 1 : (g.version || 1);
    document.getElementById('galaxy-icon').value = g.icon || '';
    document.getElementById('galaxy-namespace').value = g.namespace || '';

    // Cluster metadata fields (source, category, authors) come from the cluster file
    document.getElementById('galaxy-source').value = c?.source || '';
    document.getElementById('galaxy-category').value = c?.category || '';

    // Preserve cluster UUID (auto-managed)
    clusterUUID = isClone ? '' : (c?.uuid || '');

    // Authors
    if (authorsTagInput && c?.authors) {
        authorsTagInput.setTags(c.authors);
    }

    // Kill chain order
    const kco = g.kill_chain_order;
    const kcToggle = document.getElementById('kill-chain-toggle');
    if (kco && Object.keys(kco).length) {
        kcToggle.checked = true;
        document.getElementById('kill-chain-editor').style.display = 'block';
        document.getElementById('kill-chain-scopes').innerHTML = '';
        document.getElementById('matrix-view-btn').style.display = '';
        for (const [scope, phases] of Object.entries(kco)) {
            addKillChainScope(scope, phases);
        }
    } else {
        kcToggle.checked = false;
        document.getElementById('kill-chain-editor').style.display = 'none';
        document.getElementById('kill-chain-scopes').innerHTML = '';
        document.getElementById('matrix-view-btn').style.display = 'none';
    }

    // Clusters (values)
    initValuesEditor(c?.values || [], schedulePreviewUpdate);

    if (isClone) {
        isEditingExisting = false;
        originalGalaxyVersion = null;
        // Generate new UUIDs for clone
        regenerateUUID('galaxy-uuid');
        fetch('/api/uuid').then(r => r.json()).then(data => { clusterUUID = data.uuid; });
    } else {
        isEditingExisting = true;
        originalGalaxyVersion = g.version;
        // Auto-increment version
        document.getElementById('galaxy-version').value = autoIncrementVersion(g.version);
    }

    schedulePreviewUpdate();
}

function autoIncrementVersion(version) {
    if (!version) return 1;
    if (typeof version === 'number') {
        if (version >= 20000000) {
            // Date-based: use today's date
            const today = new Date();
            const yyyymmdd = today.getFullYear() * 10000 + (today.getMonth() + 1) * 100 + today.getDate();
            return Math.max(version + 1, yyyymmdd);
        }
        return version + 1;
    }
    return version;
}

async function loadGalaxyByType(typeName, isClone) {
    try {
        const res = await fetch(`/api/galaxies/${encodeURIComponent(typeName)}`);
        if (!res.ok) {
            showToast(`Galaxy '${typeName}' not found`, 'error');
            return;
        }
        const bundle = await res.json();
        loadGalaxyIntoEditor(bundle, isClone);
        if (!isClone) {
            showToast(`Loaded galaxy: ${bundle.galaxy.name}`, 'success');
        } else {
            showToast(`Cloned galaxy: ${bundle.galaxy.name}`, 'success');
        }
    } catch (e) {
        console.error('Load galaxy error:', e);
        showToast(`Failed to load galaxy '${typeName}': ${e.message}`, 'error');
    }
}

// --- Persist (private mode only) ---

async function persistGalaxy() {
    if (!confirm('This will write the galaxy directly to the misp-galaxy repository. Continue?')) return;
    markAllTouched();
    const bundle = buildGalaxyBundle();

    try {
        const res = await fetch('/api/galaxies/persist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bundle),
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message || 'Galaxy persisted', 'success');
        } else {
            showToast(data.error || 'Persist failed', 'error');
        }
    } catch (e) {
        showToast('Network error', 'error');
    }
}

// --- Export / Copy ---

async function exportJson() {
    const bundle = buildGalaxyBundle();
    const type = bundle.galaxy.type || 'galaxy';

    const galaxyJson = JSON.stringify(bundle.galaxy, null, 2) + '\n';
    const clusterJson = JSON.stringify(bundle.cluster, null, 2) + '\n';

    const zip = new JSZip();
    zip.file(`galaxies/${type}.json`, galaxyJson);
    zip.file(`clusters/${type}.json`, clusterJson);

    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}.zip`;
    a.click();
    URL.revokeObjectURL(url);
}

function copyJson() {
    const bundle = buildGalaxyBundle();
    navigator.clipboard.writeText(JSON.stringify(bundle, null, 2)).then(() => {
        showToast('JSON copied to clipboard', 'success');
    });
}

// --- Load existing ---

async function openLoadExisting() {
    document.getElementById('load-modal').hidden = false;
    document.getElementById('load-search').value = '';
    document.getElementById('load-list').innerHTML = '<div class="loading">Loading...</div>';

    try {
        loadGalaxiesList = await fetch('/api/galaxies').then(r => r.json());
        filterLoadList();
    } catch (e) {
        document.getElementById('load-list').innerHTML = '<div class="empty-hint">Failed to load galaxies.</div>';
    }
}

function closeLoadModal() {
    document.getElementById('load-modal').hidden = true;
}

function filterLoadList() {
    const q = (document.getElementById('load-search')?.value || '').toLowerCase();
    let filtered = loadGalaxiesList;
    if (q) {
        filtered = filtered.filter(g =>
            g.galaxy_name.toLowerCase().includes(q) ||
            g.type.toLowerCase().includes(q) ||
            g.description.toLowerCase().includes(q)
        );
    }

    const list = document.getElementById('load-list');
    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-hint">No galaxies match.</div>';
        return;
    }

    list.innerHTML = filtered.map(g => `
        <div class="load-template-row" onclick="selectLoadGalaxy('${escapeHtml(g.type)}')">
            <span class="load-template-name">${escapeHtml(g.galaxy_name || g.type)}</span>
            <span class="load-template-desc">${escapeHtml(g.description)}</span>
            <span class="load-template-meta">${g.value_count} clusters</span>
            <span class="badge ${g.source === 'user' ? 'badge-user' : 'badge-submodule'}">${g.source}</span>
        </div>
    `).join('');
}

async function selectLoadGalaxy(typeName) {
    const mode = document.querySelector('input[name="load-mode"]:checked')?.value || 'edit';
    closeLoadModal();
    await loadGalaxyByType(typeName, mode === 'clone');
    // Update URL without reload
    const param = mode === 'clone' ? 'clone' : 'load';
    history.replaceState(null, '', `/?${param}=${encodeURIComponent(typeName)}`);
}
