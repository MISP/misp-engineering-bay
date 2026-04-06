"""MISP Object Template Creator — Flask application."""

from flask import Flask, jsonify, request, render_template, abort

import config
from describe_types import get_describe_types
from validator import validate_template, validate_against_schema, META_CATEGORIES
import template_store

app = Flask(__name__)


# ---------------------------------------------------------------------------
# UI routes
# ---------------------------------------------------------------------------

@app.route("/")
def editor():
    return render_template("editor.html")


@app.route("/browse")
def browse():
    return render_template("browser.html")


@app.route("/docs")
def docs():
    return render_template("swagger.html")


# ---------------------------------------------------------------------------
# API — describe-types / meta info
# ---------------------------------------------------------------------------

@app.route("/api/describe-types")
def api_describe_types():
    dt = get_describe_types()
    return jsonify(dt.to_dict())


@app.route("/api/meta-categories")
def api_meta_categories():
    return jsonify(META_CATEGORIES)


@app.route("/api/types")
def api_types():
    dt = get_describe_types()
    return jsonify(dt.all_types_summary())


@app.route("/api/types/<path:misp_type>/categories")
def api_type_categories(misp_type: str):
    dt = get_describe_types()
    if not dt.is_valid_type(misp_type):
        return jsonify({"error": f"Unknown type '{misp_type}'"}), 404
    return jsonify({
        "type": misp_type,
        "categories": dt.get_categories_for_type(misp_type),
        "default_category": dt.get_default_category(misp_type),
        "default_to_ids": dt.get_default_to_ids(misp_type),
    })


# ---------------------------------------------------------------------------
# API — template CRUD
# ---------------------------------------------------------------------------

@app.route("/api/templates")
def api_list_templates():
    name_filter = request.args.get("name", "").lower()
    cat_filter = request.args.get("meta-category", "")
    templates = template_store.list_all_templates()
    if name_filter:
        templates = [t for t in templates if name_filter in t["name"]]
    if cat_filter:
        templates = [t for t in templates if t["meta-category"] == cat_filter]
    return jsonify(templates)


@app.route("/api/templates/<name>")
def api_get_template(name: str):
    t = template_store.get_template(name)
    if t is None:
        return jsonify({"error": f"Template '{name}' not found"}), 404
    return jsonify(t)


@app.route("/api/templates", methods=["POST"])
def api_create_template():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result = validate_template(data)
    if not result.valid:
        return jsonify(result.to_dict()), 422

    name = data["name"]
    if template_store.template_exists_in_output(name):
        return jsonify({"error": f"Template '{name}' already exists. Use PUT to update."}), 409

    path = template_store.save_template(data)
    return jsonify({"message": "Template created", "path": path, **result.to_dict()}), 201


@app.route("/api/templates/<name>", methods=["PUT"])
def api_update_template(name: str):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # Ensure the name in the body matches the URL
    if data.get("name") and data["name"] != name:
        return jsonify({"error": "Template name in body does not match URL"}), 400
    data["name"] = name

    result = validate_template(data)
    if not result.valid:
        return jsonify(result.to_dict()), 422

    path = template_store.save_template(data)
    return jsonify({"message": "Template updated", "path": path, **result.to_dict()})


@app.route("/api/templates/<name>", methods=["DELETE"])
def api_delete_template(name: str):
    if template_store.template_exists_in_submodule(name) and not template_store.template_exists_in_output(name):
        return jsonify({"error": "Cannot delete a template from the misp-objects submodule"}), 403

    if template_store.delete_template(name):
        return jsonify({"message": f"Template '{name}' deleted"})
    return jsonify({"error": f"Template '{name}' not found in output directory"}), 404


@app.route("/api/templates/validate", methods=["POST"])
def api_validate_template():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result = validate_template(data)

    # Also run schema validation
    schema_errors = validate_against_schema(data)
    for err in schema_errors:
        # Avoid duplicating errors already caught by our validator
        if not any(e["message"] in err for e in result.errors):
            result.add_error("schema", err)

    return jsonify(result.to_dict())


@app.route("/api/uuid")
def api_generate_uuid():
    return jsonify({"uuid": template_store.generate_uuid()})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
