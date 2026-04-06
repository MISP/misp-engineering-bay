"""Validation engine for MISP galaxy definitions and clusters."""

from __future__ import annotations

import json
import re
import uuid as uuid_mod

import jsonschema

import config

# Type names: alphanumeric and hyphens (used as filenames).
NAME_VALID_RE = re.compile(r"^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$")


class ValidationResult:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, path: str, message: str):
        self.errors.append({"path": path, "message": message, "severity": "error"})

    def add_warning(self, path: str, message: str):
        self.warnings.append({"path": path, "message": message, "severity": "warning"})

    def merge(self, other: ValidationResult, prefix: str = ""):
        for e in other.errors:
            p = f"{prefix}.{e['path']}" if prefix else e["path"]
            self.errors.append({"path": p, "message": e["message"], "severity": "error"})
        for w in other.warnings:
            p = f"{prefix}.{w['path']}" if prefix else w["path"]
            self.warnings.append({"path": p, "message": w["message"], "severity": "warning"})

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _validate_uuid(value: str, path: str, result: ValidationResult) -> None:
    if not value or not isinstance(value, str):
        result.add_error(path, "UUID is required.")
    else:
        try:
            uuid_mod.UUID(value)
        except ValueError:
            result.add_error(path, "UUID is not valid.")


def _validate_required_string(value, path: str, label: str, result: ValidationResult) -> None:
    if not value or not isinstance(value, str):
        result.add_error(path, f"{label} is required and must be a non-empty string.")


def validate_galaxy(galaxy: dict) -> ValidationResult:
    """Validate a galaxy definition dict."""
    result = ValidationResult()

    _validate_required_string(galaxy.get("name"), "galaxy.name", "Name", result)
    _validate_required_string(galaxy.get("description"), "galaxy.description", "Description", result)

    gtype = galaxy.get("type")
    if not gtype or not isinstance(gtype, str):
        result.add_error("galaxy.type", "Type is required and must be a non-empty string.")
    elif not NAME_VALID_RE.match(gtype):
        result.add_error(
            "galaxy.type",
            "Type must contain only alphanumeric characters and hyphens.",
        )

    _validate_uuid(galaxy.get("uuid", ""), "galaxy.uuid", result)

    version = galaxy.get("version")
    if version is None:
        result.add_error("galaxy.version", "Version is required.")
    elif not isinstance(version, int) or version < 1:
        result.add_error("galaxy.version", "Version must be a positive integer.")

    # Optional fields
    icon = galaxy.get("icon")
    if icon is not None and not isinstance(icon, str):
        result.add_error("galaxy.icon", "Icon must be a string.")

    namespace = galaxy.get("namespace")
    if namespace is not None and not isinstance(namespace, str):
        result.add_error("galaxy.namespace", "Namespace must be a string.")

    kco = galaxy.get("kill_chain_order")
    if kco is not None:
        if not isinstance(kco, dict):
            result.add_error("galaxy.kill_chain_order", "kill_chain_order must be an object.")
        else:
            for scope, phases in kco.items():
                if not isinstance(phases, list) or not phases:
                    result.add_error(
                        f"galaxy.kill_chain_order.{scope}",
                        f"Scope '{scope}' must have a non-empty array of phases.",
                    )
                elif not all(isinstance(p, str) for p in phases):
                    result.add_error(
                        f"galaxy.kill_chain_order.{scope}",
                        f"All phases in scope '{scope}' must be strings.",
                    )

    return result


def validate_cluster(cluster: dict) -> ValidationResult:
    """Validate a cluster dict."""
    result = ValidationResult()

    _validate_required_string(cluster.get("name"), "cluster.name", "Name", result)
    _validate_required_string(cluster.get("description"), "cluster.description", "Description", result)

    ctype = cluster.get("type")
    if not ctype or not isinstance(ctype, str):
        result.add_error("cluster.type", "Type is required and must be a non-empty string.")

    _validate_uuid(cluster.get("uuid", ""), "cluster.uuid", result)

    version = cluster.get("version")
    if version is None:
        result.add_error("cluster.version", "Version is required.")
    elif not isinstance(version, int) or version < 1:
        result.add_error("cluster.version", "Version must be a positive integer.")

    _validate_required_string(cluster.get("source"), "cluster.source", "Source", result)
    _validate_required_string(cluster.get("category"), "cluster.category", "Category", result)

    authors = cluster.get("authors")
    if authors is None or not isinstance(authors, list) or not authors:
        result.add_error("cluster.authors", "Authors is required and must be a non-empty array.")
    elif not all(isinstance(a, str) for a in authors):
        result.add_error("cluster.authors", "All authors must be strings.")

    # Values
    values = cluster.get("values")
    if values is None or not isinstance(values, list):
        result.add_error("cluster.values", "Values is required and must be an array.")
    elif not values:
        result.add_warning("cluster.values", "Cluster has no values.")
    else:
        seen_values = set()
        for i, val in enumerate(values):
            prefix = f"cluster.values[{i}]"
            if not isinstance(val, dict):
                result.add_error(prefix, "Each value must be an object.")
                continue

            v = val.get("value")
            if not v or not isinstance(v, str):
                result.add_error(f"{prefix}.value", "Value field is required and must be a non-empty string.")
            else:
                if v in seen_values:
                    result.add_warning(f"{prefix}.value", f"Duplicate value '{v}'.")
                seen_values.add(v)

            uid = val.get("uuid")
            if uid is not None:
                _validate_uuid(uid, f"{prefix}.uuid", result)

            meta = val.get("meta")
            if meta is not None and not isinstance(meta, dict):
                result.add_error(f"{prefix}.meta", "Meta must be an object.")

            related = val.get("related")
            if related is not None:
                if not isinstance(related, list):
                    result.add_error(f"{prefix}.related", "Related must be an array.")
                else:
                    for j, rel in enumerate(related):
                        rprefix = f"{prefix}.related[{j}]"
                        if not isinstance(rel, dict):
                            result.add_error(rprefix, "Each related entry must be an object.")
                            continue
                        if not rel.get("dest-uuid"):
                            result.add_error(f"{rprefix}.dest-uuid", "dest-uuid is required.")
                        if not rel.get("type"):
                            result.add_error(f"{rprefix}.type", "Relationship type is required.")

    return result


def validate_bundle(bundle: dict) -> ValidationResult:
    """Validate a full galaxy + cluster bundle."""
    result = ValidationResult()

    galaxy = bundle.get("galaxy")
    cluster = bundle.get("cluster")

    if not galaxy or not isinstance(galaxy, dict):
        result.add_error("galaxy", "Galaxy definition is required.")
        return result
    if not cluster or not isinstance(cluster, dict):
        result.add_error("cluster", "Cluster definition is required.")
        return result

    # Validate each independently
    result.merge(validate_galaxy(galaxy))
    result.merge(validate_cluster(cluster))

    # Cross-validation: types must match
    gtype = galaxy.get("type", "")
    ctype = cluster.get("type", "")
    if gtype and ctype and gtype != ctype:
        result.add_error(
            "type",
            f"Galaxy type '{gtype}' does not match cluster type '{ctype}'. They must be identical.",
        )

    # Cross-validation: kill_chain references
    kco = galaxy.get("kill_chain_order")
    if kco and isinstance(kco, dict):
        valid_entries = set()
        for scope, phases in kco.items():
            if isinstance(phases, list):
                for phase in phases:
                    valid_entries.add(f"{scope}:{phase}")

        values = cluster.get("values", [])
        if isinstance(values, list):
            for i, val in enumerate(values):
                if not isinstance(val, dict):
                    continue
                meta = val.get("meta")
                if not isinstance(meta, dict):
                    continue
                kc = meta.get("kill_chain")
                if not isinstance(kc, list):
                    continue
                for entry in kc:
                    if isinstance(entry, str) and entry not in valid_entries:
                        result.add_warning(
                            f"cluster.values[{i}].meta.kill_chain",
                            f"Kill chain entry '{entry}' does not match any scope:phase in kill_chain_order.",
                        )

    return result


def validate_galaxy_against_schema(galaxy: dict) -> list[str]:
    """Validate a galaxy dict against schema_galaxies.json."""
    return _validate_against_schema(galaxy, config.SCHEMA_GALAXIES_PATH)


def validate_cluster_against_schema(cluster: dict) -> list[str]:
    """Validate a cluster dict against schema_clusters.json."""
    return _validate_against_schema(cluster, config.SCHEMA_CLUSTERS_PATH)


def _validate_against_schema(data: dict, schema_path: str) -> list[str]:
    """Validate data against a JSON schema file. Returns list of error strings."""
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        return [f"Schema file not found at {schema_path}"]

    errors = []
    v = jsonschema.Draft7Validator(schema)
    for error in v.iter_errors(data):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors
