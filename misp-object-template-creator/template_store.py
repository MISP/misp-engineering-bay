"""Read/write MISP object templates from the submodule and user output directory."""

from __future__ import annotations

import json
import os
import uuid as uuid_mod

import config


def _objects_dir() -> str:
    return os.path.join(config.MISP_OBJECTS_PATH, "objects")


def _output_dir() -> str:
    os.makedirs(config.OUTPUT_PATH, exist_ok=True)
    return config.OUTPUT_PATH


def list_submodule_templates() -> list[dict]:
    """List all templates from the misp-objects submodule."""
    return _scan_directory(_objects_dir(), source="misp-objects")


def list_user_templates() -> list[dict]:
    """List all user-created templates in the output directory."""
    return _scan_directory(_output_dir(), source="user")


def list_all_templates() -> list[dict]:
    """List all templates from both sources."""
    templates = list_submodule_templates()
    user = list_user_templates()
    # User templates override submodule ones with same name in the listing
    submodule_names = {t["name"] for t in templates}
    for t in user:
        if t["name"] in submodule_names:
            # Replace the submodule entry
            templates = [s for s in templates if s["name"] != t["name"]] + [t]
        else:
            templates.append(t)
    templates.sort(key=lambda t: t["name"])
    return templates


def _scan_directory(directory: str, source: str) -> list[dict]:
    results = []
    if not os.path.isdir(directory):
        return results
    for entry in sorted(os.listdir(directory)):
        defn_path = os.path.join(directory, entry, "definition.json")
        if os.path.isfile(defn_path):
            try:
                with open(defn_path) as f:
                    data = json.load(f)
                results.append({
                    "name": data.get("name", entry),
                    "description": data.get("description", ""),
                    "meta-category": data.get("meta-category", ""),
                    "version": data.get("version", 0),
                    "attribute_count": len(data.get("attributes", {})),
                    "source": source,
                })
            except (json.JSONDecodeError, OSError):
                continue
    return results


def get_template(name: str) -> dict | None:
    """Load a template by name. Checks user output first, then submodule."""
    # Check user output first
    user_path = os.path.join(_output_dir(), name, "definition.json")
    if os.path.isfile(user_path):
        with open(user_path) as f:
            data = json.load(f)
        data["_source"] = "user"
        return data

    # Fallback to submodule
    sub_path = os.path.join(_objects_dir(), name, "definition.json")
    if os.path.isfile(sub_path):
        with open(sub_path) as f:
            data = json.load(f)
        data["_source"] = "misp-objects"
        return data

    return None


def save_template(template: dict) -> str:
    """Save a template to the output directory. Returns the file path."""
    name = template["name"]
    # Strip internal metadata before saving
    clean = {k: v for k, v in template.items() if not k.startswith("_")}
    out_dir = os.path.join(_output_dir(), name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "definition.json")
    with open(out_path, "w") as f:
        json.dump(clean, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return out_path


def delete_template(name: str) -> bool:
    """Delete a user-created template. Returns True if deleted, False if not found."""
    import shutil
    out_dir = os.path.join(_output_dir(), name)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
        return True
    return False


def template_exists_in_submodule(name: str) -> bool:
    return os.path.isfile(os.path.join(_objects_dir(), name, "definition.json"))


def template_exists_in_output(name: str) -> bool:
    return os.path.isfile(os.path.join(_output_dir(), name, "definition.json"))


def generate_uuid() -> str:
    return str(uuid_mod.uuid4())
