/**
 * types.js — Load and cache MISP type/category data for the UI.
 */

let typesData = null; // Array of {type, categories, default_category, default_to_ids}
let allCategories = null;
let typeLookup = {}; // type string -> summary object

async function loadTypes() {
    if (typesData) return typesData;
    const [typesRes, catsRes] = await Promise.all([
        fetch('/api/types'),
        fetch('/api/meta-categories'),
    ]);
    typesData = await typesRes.json();
    allCategories = await catsRes.json();
    typeLookup = {};
    typesData.forEach(t => { typeLookup[t.type] = t; });
    return typesData;
}

function getTypeInfo(mispType) {
    return typeLookup[mispType] || null;
}

function getCategoriesForType(mispType) {
    const info = typeLookup[mispType];
    return info ? info.categories : [];
}

function getAllCategories() {
    return allCategories || [];
}

function getAllTypes() {
    return typesData || [];
}

// Utility: HTML escape
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Toast notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}
