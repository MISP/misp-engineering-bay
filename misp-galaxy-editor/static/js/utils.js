/* Shared utilities for the MISP Galaxy Editor. */

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function debounce(fn, ms) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), ms);
    };
}

/* Tag input helper: manages a tag-input-wrapper element. */
function setupTagInput(wrapperId, inputId, tagsId, onChange) {
    const wrapper = document.getElementById(wrapperId);
    const input = document.getElementById(inputId);
    const tagsContainer = document.getElementById(tagsId);
    if (!input || !tagsContainer) return;

    function getTags() {
        return Array.from(tagsContainer.querySelectorAll('.tag-item'))
            .map(el => el.dataset.value);
    }

    function addTag(value) {
        value = value.trim();
        if (!value) return;
        if (getTags().includes(value)) return;
        const tag = document.createElement('span');
        tag.className = 'tag-item';
        tag.dataset.value = value;
        tag.textContent = value;
        const removeBtn = document.createElement('span');
        removeBtn.className = 'tag-remove';
        removeBtn.textContent = '\u00d7';
        removeBtn.addEventListener('click', () => {
            tag.remove();
            if (onChange) window[onChange]();
        });
        tag.appendChild(removeBtn);
        tagsContainer.appendChild(tag);
        if (onChange) window[onChange]();
    }

    function setTags(values) {
        tagsContainer.innerHTML = '';
        for (const v of values) addTag(v);
    }

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addTag(input.value);
            input.value = '';
        } else if (e.key === 'Backspace' && !input.value) {
            const last = tagsContainer.querySelector('.tag-item:last-child');
            if (last) {
                last.remove();
                if (onChange) window[onChange]();
            }
        }
    });

    // Auto-commit on blur so text isn't silently lost
    input.addEventListener('blur', function() {
        if (input.value.trim()) {
            addTag(input.value);
            input.value = '';
        }
    });

    return { getTags, addTag, setTags };
}
