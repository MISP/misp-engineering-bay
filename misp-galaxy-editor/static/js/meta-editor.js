/* Meta editor component: freeform key-value editor with autocomplete. */

let metaSuggestions = [];  // [{key, frequency, typical_type}]

function initMetaSuggestions(suggestions) {
    metaSuggestions = suggestions || [];
}

/**
 * Render a meta editor into a container element.
 * @param {HTMLElement} container
 * @param {Object} meta - the meta object to edit
 * @param {Function} onChange - called when meta changes
 * @returns {{ getMeta: () => Object }}
 */
function createMetaEditor(container, meta, onChange) {
    meta = meta || {};

    function render() {
        container.innerHTML = '';
        const keys = Object.keys(meta);

        if (keys.length === 0) {
            container.innerHTML = '<div class="empty-hint">No meta fields. Click "Add Field" to add one.</div>';
        }

        for (const key of keys) {
            const row = document.createElement('div');
            row.className = 'meta-row';

            const isArray = Array.isArray(meta[key]);
            const value = meta[key];

            row.innerHTML = `
                <input type="text" class="form-input meta-key" value="${escapeHtml(key)}"
                       placeholder="Key" list="meta-key-suggestions">
                <div class="meta-value" style="flex:1">
                    ${isArray
                        ? `<div class="tag-input-wrapper" onclick="this.querySelector('input').focus()">
                               <div class="tag-list">${value.map(v => `<span class="tag-item" data-value="${escapeHtml(String(v))}">${escapeHtml(String(v))}<span class="tag-remove">&times;</span></span>`).join('')}</div>
                               <input type="text" class="tag-input meta-array-input" placeholder="Add item...">
                           </div>`
                        : `<input type="text" class="form-input meta-string-input" value="${escapeHtml(String(value))}" placeholder="Value">`
                    }
                </div>
                <button class="btn btn-icon btn-small" title="Toggle array/string" onclick="this" data-toggle-type>
                    ${isArray ? '[ ]' : 'Aa'}
                </button>
                <button class="btn btn-icon btn-danger btn-small" title="Remove field" data-remove>&times;</button>
            `;
            container.appendChild(row);

            // Key rename (merges into array if key already exists)
            const keyInput = row.querySelector('.meta-key');
            keyInput.addEventListener('change', () => {
                const newKey = keyInput.value.trim();
                if (newKey && newKey !== key) {
                    if (meta.hasOwnProperty(newKey)) {
                        // Merge: combine both values into an array
                        const existing = meta[newKey];
                        const incoming = meta[key];
                        const toArray = v => Array.isArray(v) ? v : [v];
                        meta[newKey] = [...toArray(existing), ...toArray(incoming)];
                    } else {
                        meta[newKey] = meta[key];
                    }
                    delete meta[key];
                    render();
                    if (onChange) onChange();
                }
            });

            // String value change
            const strInput = row.querySelector('.meta-string-input');
            if (strInput) {
                strInput.addEventListener('input', () => {
                    meta[key] = strInput.value;
                    if (onChange) onChange();
                });
            }

            // Array tag input
            const arrInput = row.querySelector('.meta-array-input');
            if (arrInput) {
                arrInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ',') {
                        e.preventDefault();
                        const val = arrInput.value.trim();
                        if (val && !meta[key].includes(val)) {
                            meta[key].push(val);
                            render();
                            if (onChange) onChange();
                        }
                        arrInput.value = '';
                    }
                });
            }

            // Tag remove buttons
            row.querySelectorAll('.tag-remove').forEach((btn, idx) => {
                btn.addEventListener('click', () => {
                    meta[key].splice(idx, 1);
                    render();
                    if (onChange) onChange();
                });
            });

            // Toggle type
            row.querySelector('[data-toggle-type]').addEventListener('click', () => {
                if (isArray) {
                    meta[key] = meta[key].join(', ');
                } else {
                    const str = String(meta[key]);
                    meta[key] = str ? str.split(',').map(s => s.trim()).filter(Boolean) : [];
                }
                render();
                if (onChange) onChange();
            });

            // Remove
            row.querySelector('[data-remove]').addEventListener('click', () => {
                delete meta[key];
                render();
                if (onChange) onChange();
            });
        }

        // Add button
        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-small';
        addBtn.textContent = '+ Add Field';
        addBtn.style.marginTop = '8px';
        addBtn.addEventListener('click', () => {
            // Find a unique key name
            let newKey = 'new-field';
            let i = 1;
            while (meta.hasOwnProperty(newKey)) newKey = `new-field-${i++}`;

            // Check if known key suggests array
            const suggestion = metaSuggestions.find(s => s.key === newKey);
            meta[newKey] = (suggestion && suggestion.typical_type === 'array') ? [] : '';
            render();
            // Focus the new key input
            const lastKey = container.querySelector('.meta-row:last-of-type .meta-key');
            if (lastKey) { lastKey.select(); lastKey.focus(); }
            if (onChange) onChange();
        });
        container.appendChild(addBtn);

        // Add datalist for suggestions
        if (!document.getElementById('meta-key-suggestions')) {
            const dl = document.createElement('datalist');
            dl.id = 'meta-key-suggestions';
            for (const s of metaSuggestions) {
                const opt = document.createElement('option');
                opt.value = s.key;
                dl.appendChild(opt);
            }
            document.body.appendChild(dl);
        }
    }

    render();

    return {
        getMeta() { return meta; },
        setMeta(newMeta) { meta = newMeta || {}; render(); },
    };
}
