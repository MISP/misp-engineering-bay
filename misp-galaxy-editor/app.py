"""MISP Galaxy Editor — Flask application."""

from flask import Flask, jsonify, request, render_template

import config
import galaxy_store
import galaxy_meta
from validator import (
    validate_bundle,
    validate_galaxy_against_schema,
    validate_cluster_against_schema,
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# UI routes
# ---------------------------------------------------------------------------

@app.route("/")
def editor():
    return render_template("editor.html", mode=config.MODE)


@app.route("/browse")
def browse():
    return render_template("browser.html")


@app.route("/docs")
def docs():
    return render_template("swagger.html")


# ---------------------------------------------------------------------------
# API — reference data
# ---------------------------------------------------------------------------

@app.route("/api/config")
def api_config():
    """Expose non-sensitive configuration to the UI."""
    return jsonify({"mode": config.MODE})


@app.route("/api/meta-suggestions")
def api_meta_suggestions():
    """Return reference data for autocomplete (namespaces, icons, meta keys, etc.)."""
    return jsonify(galaxy_meta.get_suggestions())


@app.route("/api/uuid")
def api_generate_uuid():
    return jsonify({"uuid": galaxy_store.generate_uuid()})


# ---------------------------------------------------------------------------
# API — galaxy CRUD
# ---------------------------------------------------------------------------

@app.route("/api/galaxies")
def api_list_galaxies():
    name_filter = request.args.get("name", "").lower()
    namespace_filter = request.args.get("namespace", "")
    kill_chain_filter = request.args.get("has_kill_chain", "")

    galaxies = galaxy_store.list_all_galaxies()

    if name_filter:
        galaxies = [
            g for g in galaxies
            if name_filter in g["galaxy_name"].lower()
            or name_filter in g["cluster_name"].lower()
            or name_filter in g["type"].lower()
        ]
    if namespace_filter:
        galaxies = [g for g in galaxies if g["namespace"] == namespace_filter]
    if kill_chain_filter:
        want_kc = kill_chain_filter.lower() in ("true", "1", "yes")
        galaxies = [g for g in galaxies if g["has_kill_chain"] == want_kc]

    return jsonify(galaxies)


@app.route("/api/galaxies/<type_name>")
def api_get_galaxy(type_name: str):
    bundle = galaxy_store.get_galaxy(type_name)
    if bundle is None:
        return jsonify({"error": f"Galaxy '{type_name}' not found"}), 404
    return jsonify(bundle)



@app.route("/api/galaxies/validate", methods=["POST"])
def api_validate_galaxy():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result = validate_bundle(data)

    # Also run schema validation
    galaxy = data.get("galaxy", {})
    cluster = data.get("cluster", {})

    for err in validate_galaxy_against_schema(galaxy):
        if not any(e["message"] in err for e in result.errors):
            result.add_error("galaxy.schema", err)

    for err in validate_cluster_against_schema(cluster):
        if not any(e["message"] in err for e in result.errors):
            result.add_error("cluster.schema", err)

    return jsonify(result.to_dict())


@app.route("/api/galaxies/persist", methods=["POST"])
def api_persist_galaxy():
    """Persist a galaxy directly to the misp-galaxy repository (private mode only)."""
    if config.MODE != "private":
        return jsonify({"error": "Persist to repository is only available in private mode"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    type_name = data.get("galaxy", {}).get("type", "")
    try:
        galaxy_store._validate_safe_name(type_name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    result = validate_bundle(data)
    if not result.valid:
        return jsonify(result.to_dict()), 422

    try:
        gpath, cpath = galaxy_store.persist_galaxy(data)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": str(e)}), 403

    return jsonify({
        "message": "Galaxy persisted to repository",
        "galaxy_path": gpath,
        "cluster_path": cpath,
        **result.to_dict(),
    })


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
