/* Related editor component: manages relationship entries for a cluster value. */

let relationshipTypeSuggestions = [];  // [{type, frequency}]

function initRelationshipSuggestions(suggestions) {
    relationshipTypeSuggestions = suggestions || [];
    // Build datalist if needed
    if (!document.getElementById('rel-type-suggestions')) {
        const dl = document.createElement('datalist');
        dl.id = 'rel-type-suggestions';
        for (const s of relationshipTypeSuggestions) {
            const opt = document.createElement('option');
            opt.value = s.type;
            dl.appendChild(opt);
        }
        document.body.appendChild(dl);
    }
}

/**
 * Render a related editor into a container.
 * @param {HTMLElement} container
 * @param {Array} related - array of {dest-uuid, type, tags?}
 * @param {Function} onChange
 * @returns {{ getRelated: () => Array }}
 */
function createRelatedEditor(container, related, onChange) {
    related = related || [];

    function render() {
        container.innerHTML = '';

        if (related.length === 0) {
            container.innerHTML = '<div class="empty-hint">No relationships. Click "Add Relationship" to add one.</div>';
        }

        for (let i = 0; i < related.length; i++) {
            const rel = related[i];
            const row = document.createElement('div');
            row.className = 'related-row';
            row.innerHTML = `
                <div style="flex:1;display:flex;flex-direction:column;gap:6px">
                    <div style="display:flex;gap:8px">
                        <input type="text" class="form-input" placeholder="dest-uuid" value="${escapeHtml(rel['dest-uuid'] || '')}" data-field="dest-uuid" style="flex:2">
                        <input type="text" class="form-input" placeholder="Relationship type" value="${escapeHtml(rel.type || '')}" data-field="type" list="rel-type-suggestions" style="flex:1">
                    </div>
                    ${rel.tags && rel.tags.length ? `<div class="meta-badge" style="font-size:11px">${rel.tags.length} tag(s)</div>` : ''}
                </div>
                <button class="btn btn-icon btn-danger btn-small" data-remove title="Remove">&times;</button>
            `;
            container.appendChild(row);

            // Input handlers
            row.querySelectorAll('input[data-field]').forEach(inp => {
                inp.addEventListener('input', () => {
                    rel[inp.dataset.field] = inp.value;
                    if (onChange) onChange();
                });
            });

            row.querySelector('[data-remove]').addEventListener('click', () => {
                related.splice(i, 1);
                render();
                if (onChange) onChange();
            });
        }

        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-small';
        addBtn.textContent = '+ Add Relationship';
        addBtn.style.marginTop = '8px';
        addBtn.addEventListener('click', () => {
            related.push({'dest-uuid': '', 'type': 'similar'});
            render();
            if (onChange) onChange();
        });
        container.appendChild(addBtn);
    }

    render();

    return {
        getRelated() { return related; },
        setRelated(newRelated) { related = newRelated || []; render(); },
    };
}
