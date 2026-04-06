"""Read/write MISP galaxy+cluster file pairs from the submodule and user output directory."""

from __future__ import annotations

import json
import os
import re
import uuid as uuid_mod

import config

# Strict pattern for filenames — alphanumeric, hyphens, and uppercase allowed
# (some existing galaxies use uppercase like "NACE").
SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$")


def _validate_safe_name(name: str) -> None:
    """Raise ValueError if a name is not safe for use as a filename."""
    if not name:
        raise ValueError("Galaxy type must not be empty")
    if len(name) > 128:
        raise ValueError("Galaxy type must not exceed 128 characters.")
    if not SAFE_NAME_RE.match(name):
        raise ValueError(
            f"Galaxy type '{name}' contains invalid characters. "
            "Only alphanumeric characters and hyphens are allowed (no leading/trailing hyphens)."
        )


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def _submodule_galaxies_dir() -> str:
    return os.path.join(config.MISP_GALAXY_PATH, "galaxies")


def _submodule_clusters_dir() -> str:
    return os.path.join(config.MISP_GALAXY_PATH, "clusters")


def _output_galaxies_dir() -> str:
    d = os.path.join(config.OUTPUT_PATH, "galaxies")
    os.makedirs(d, exist_ok=True)
    return d


def _output_clusters_dir() -> str:
    d = os.path.join(config.OUTPUT_PATH, "clusters")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def _scan_galaxies(galaxies_dir: str, clusters_dir: str, source: str) -> list[dict]:
    """Scan a galaxies directory and its companion clusters directory."""
    results = []
    if not os.path.isdir(galaxies_dir):
        return results

    for fname in sorted(os.listdir(galaxies_dir)):
        if not fname.endswith(".json"):
            continue
        gpath = os.path.join(galaxies_dir, fname)
        cpath = os.path.join(clusters_dir, fname)
        try:
            with open(gpath) as f:
                galaxy = json.load(f)
            value_count = 0
            cluster_name = ""
            if os.path.isfile(cpath):
                with open(cpath) as f:
                    cluster = json.load(f)
                value_count = len(cluster.get("values", []))
                cluster_name = cluster.get("name", "")
            results.append({
                "type": galaxy.get("type", fname.replace(".json", "")),
                "galaxy_name": galaxy.get("name", ""),
                "cluster_name": cluster_name,
                "description": galaxy.get("description", ""),
                "namespace": galaxy.get("namespace", ""),
                "icon": galaxy.get("icon", ""),
                "value_count": value_count,
                "has_kill_chain": "kill_chain_order" in galaxy,
                "version": galaxy.get("version", 0),
                "source": source,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return results


def list_all_galaxies() -> list[dict]:
    """List all galaxies from both submodule and user output."""
    galaxies = _scan_galaxies(
        _submodule_galaxies_dir(), _submodule_clusters_dir(), "misp-galaxy"
    )
    user = _scan_galaxies(
        _output_galaxies_dir(), _output_clusters_dir(), "user"
    )
    # User galaxies override submodule ones with same type
    submodule_types = {g["type"] for g in galaxies}
    for g in user:
        if g["type"] in submodule_types:
            galaxies = [s for s in galaxies if s["type"] != g["type"]] + [g]
        else:
            galaxies.append(g)
    galaxies.sort(key=lambda g: g["type"])
    return galaxies


# ---------------------------------------------------------------------------
# Type → filename index (cached)
# Needed because some galaxy filenames differ from their type field.
# ---------------------------------------------------------------------------

_type_to_filename: dict[str, str] | None = None


def _build_type_index() -> dict[str, str]:
    """Scan submodule galaxies and map type field → filename (without .json)."""
    index = {}
    gdir = _submodule_galaxies_dir()
    if os.path.isdir(gdir):
        for fname in os.listdir(gdir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(gdir, fname)) as f:
                    g = json.load(f)
                gtype = g.get("type", fname.replace(".json", ""))
                index[gtype] = fname.replace(".json", "")
            except (json.JSONDecodeError, OSError):
                continue
    return index


def _resolve_filename(type_name: str) -> str:
    """Resolve a type name to the actual filename stem. Falls back to type_name itself."""
    global _type_to_filename
    if _type_to_filename is None:
        _type_to_filename = _build_type_index()
    return _type_to_filename.get(type_name, type_name)


# ---------------------------------------------------------------------------
# Get a single galaxy bundle
# ---------------------------------------------------------------------------

def _load_bundle(galaxies_dir: str, clusters_dir: str, filename: str, source: str) -> dict | None:
    """Load a galaxy + cluster pair from a directory by filename stem."""
    gpath = os.path.join(galaxies_dir, f"{filename}.json")
    if not os.path.isfile(gpath):
        return None
    with open(gpath) as f:
        galaxy = json.load(f)

    cpath = os.path.join(clusters_dir, f"{filename}.json")
    cluster = None
    if os.path.isfile(cpath):
        with open(cpath) as f:
            cluster = json.load(f)

    return {"galaxy": galaxy, "cluster": cluster, "_source": source}


def get_galaxy(type_name: str) -> dict | None:
    """Load a galaxy bundle by type. Checks user output first, then submodule."""
    # User output: filename always matches type (we control this)
    bundle = _load_bundle(
        _output_galaxies_dir(), _output_clusters_dir(), type_name, "user"
    )
    if bundle:
        return bundle
    # Submodule: filename may differ from type
    filename = _resolve_filename(type_name)
    return _load_bundle(
        _submodule_galaxies_dir(), _submodule_clusters_dir(), filename, "misp-galaxy"
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _write_json(data: dict, path: str, parent_dir: str) -> None:
    """Write a dict as sorted-key JSON to a path, with traversal check."""
    real_parent = os.path.realpath(parent_dir)
    real_path = os.path.realpath(path)
    if not real_path.startswith(real_parent + os.sep):
        raise ValueError("Invalid name: path traversal detected")
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    with open(path, "w") as f:
        json.dump(clean, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def _write_bundle_to_dirs(bundle: dict, galaxies_dir: str, clusters_dir: str) -> tuple[str, str]:
    """Write both galaxy and cluster files. Returns (galaxy_path, cluster_path)."""
    galaxy = bundle["galaxy"]
    cluster = bundle["cluster"]
    type_name = galaxy["type"]
    _validate_safe_name(type_name)

    gpath = os.path.join(galaxies_dir, f"{type_name}.json")
    cpath = os.path.join(clusters_dir, f"{type_name}.json")

    _write_json(galaxy, gpath, galaxies_dir)
    try:
        _write_json(cluster, cpath, clusters_dir)
    except Exception:
        # Roll back the galaxy file if cluster write fails
        if os.path.isfile(gpath):
            os.remove(gpath)
        raise

    return gpath, cpath


def save_galaxy(bundle: dict) -> tuple[str, str]:
    """Save a galaxy bundle to the output directory."""
    return _write_bundle_to_dirs(bundle, _output_galaxies_dir(), _output_clusters_dir())


def persist_galaxy(bundle: dict) -> tuple[str, str]:
    """Save a galaxy bundle directly to the misp-galaxy repository (private mode only)."""
    if config.MODE != "private":
        raise RuntimeError("Persist to repository is only available in private mode")
    return _write_bundle_to_dirs(
        bundle, _submodule_galaxies_dir(), _submodule_clusters_dir()
    )


def delete_galaxy(type_name: str) -> bool:
    """Delete a user-created galaxy. Returns True if any file deleted."""
    _validate_safe_name(type_name)
    deleted = False
    for d in (_output_galaxies_dir(), _output_clusters_dir()):
        path = os.path.join(d, f"{type_name}.json")
        if os.path.isfile(path):
            os.remove(path)
            deleted = True
    return deleted


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------

def galaxy_exists_in_submodule(type_name: str) -> bool:
    filename = _resolve_filename(type_name)
    return os.path.isfile(os.path.join(_submodule_galaxies_dir(), f"{filename}.json"))


def galaxy_exists_in_output(type_name: str) -> bool:
    return os.path.isfile(os.path.join(_output_galaxies_dir(), f"{type_name}.json"))


def generate_uuid() -> str:
    return str(uuid_mod.uuid4())
