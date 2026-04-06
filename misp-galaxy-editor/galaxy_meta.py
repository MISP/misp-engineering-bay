"""Reference data extracted from existing galaxies and clusters (cached at startup)."""

from __future__ import annotations

import json
import os
from collections import Counter

import config

_cache: dict | None = None


def _build_cache() -> dict:
    """Scan all existing galaxies and clusters to extract reference data."""
    galaxies_dir = os.path.join(config.MISP_GALAXY_PATH, "galaxies")
    clusters_dir = os.path.join(config.MISP_GALAXY_PATH, "clusters")

    namespaces: set[str] = set()
    icons: set[str] = set()
    categories: set[str] = set()
    meta_keys: Counter = Counter()
    meta_types: dict[str, str] = {}  # key -> "array" or "string"
    relationship_types: Counter = Counter()

    # Scan galaxies
    if os.path.isdir(galaxies_dir):
        for fname in os.listdir(galaxies_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(galaxies_dir, fname)) as f:
                    g = json.load(f)
                if g.get("namespace"):
                    namespaces.add(g["namespace"])
                if g.get("icon"):
                    icons.add(g["icon"])
            except (json.JSONDecodeError, OSError):
                continue

    # Scan clusters
    if os.path.isdir(clusters_dir):
        for fname in os.listdir(clusters_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(clusters_dir, fname)) as f:
                    c = json.load(f)
                if c.get("category"):
                    categories.add(c["category"])
                for val in c.get("values", []):
                    meta = val.get("meta")
                    if isinstance(meta, dict):
                        for k, v in meta.items():
                            meta_keys[k] += 1
                            if k not in meta_types:
                                meta_types[k] = "array" if isinstance(v, list) else "string"
                    for rel in val.get("related", []):
                        rtype = rel.get("type", "")
                        if rtype:
                            relationship_types[rtype] += 1
            except (json.JSONDecodeError, OSError):
                continue

    # Build meta key suggestions (top 80 by frequency)
    meta_suggestions = [
        {"key": k, "frequency": cnt, "typical_type": meta_types.get(k, "string")}
        for k, cnt in meta_keys.most_common(80)
    ]

    return {
        "namespaces": sorted(namespaces),
        "icons": sorted(icons),
        "categories": sorted(categories),
        "meta_keys": meta_suggestions,
        "relationship_types": [
            {"type": t, "frequency": cnt}
            for t, cnt in relationship_types.most_common(50)
        ],
    }


def get_suggestions() -> dict:
    """Return cached reference data. Builds cache on first call."""
    global _cache
    if _cache is None:
        _cache = _build_cache()
    return _cache


def get_known_namespaces() -> list[str]:
    return get_suggestions()["namespaces"]


def get_known_icons() -> list[str]:
    return get_suggestions()["icons"]


def get_known_categories() -> list[str]:
    return get_suggestions()["categories"]
