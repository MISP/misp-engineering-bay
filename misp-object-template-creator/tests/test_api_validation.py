"""Tests for the validation API endpoint."""

import json
import uuid


def _make_template(**overrides):
    """Build a minimal valid template with optional overrides."""
    tpl = {
        "name": "validation-test",
        "description": "For testing",
        "meta-category": "misc",
        "uuid": str(uuid.uuid4()),
        "version": 1,
        "attributes": {
            "value": {
                "misp-attribute": "text",
                "ui-priority": 1,
                "description": "A value",
            }
        },
    }
    tpl.update(overrides)
    return tpl


def test_validate_valid_template(client):
    tpl = _make_template(requiredOneOf=["value"])
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0


def test_validate_missing_name(client):
    tpl = _make_template(name="")
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("name" in e["path"].lower() or "Name" in e["message"] for e in data["errors"])


def test_validate_invalid_meta_category(client):
    tpl = _make_template(**{"meta-category": "bogus"})
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("meta-category" in e["path"] for e in data["errors"])


def test_validate_invalid_uuid(client):
    tpl = _make_template(uuid="not-a-uuid")
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("uuid" in e["path"].lower() for e in data["errors"])


def test_validate_bad_version(client):
    tpl = _make_template(version=-1)
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("version" in e["path"].lower() for e in data["errors"])


def test_validate_no_attributes(client):
    tpl = _make_template(attributes={})
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("attribute" in e["path"].lower() for e in data["errors"])


def test_validate_invalid_misp_type(client):
    tpl = _make_template(attributes={
        "val": {
            "misp-attribute": "totally-fake-type",
            "ui-priority": 1,
            "description": "test",
        }
    })
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("not a valid MISP attribute type" in e["message"] for e in data["errors"])


def test_validate_invalid_category(client):
    tpl = _make_template(attributes={
        "val": {
            "misp-attribute": "ip-src",
            "ui-priority": 1,
            "description": "test",
            "categories": ["Not A Real Category"],
        }
    })
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("not a valid category" in e["message"] for e in data["errors"])


def test_validate_category_type_mismatch_is_warning(client):
    """A category valid globally but not for the chosen type should be a warning, not error."""
    tpl = _make_template(attributes={
        "val": {
            "misp-attribute": "ip-src",
            "ui-priority": 1,
            "description": "test",
            "categories": ["Person"],
        }
    })
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    # Should still be valid (it's a warning not error)
    assert data["valid"] is True
    assert any("Person" in w["message"] for w in data["warnings"])


def test_validate_required_refs_nonexistent_attr(client):
    tpl = _make_template(required=["nonexistent"])
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("nonexistent" in e["message"] for e in data["errors"])


def test_validate_required_one_of_refs_nonexistent_attr(client):
    tpl = _make_template(requiredOneOf=["nonexistent"])
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("nonexistent" in e["message"] for e in data["errors"])


def test_validate_duplicate_sane_default(client):
    tpl = _make_template(attributes={
        "val": {
            "misp-attribute": "text",
            "ui-priority": 1,
            "description": "test",
            "sane_default": ["a", "b", "a"],
        }
    })
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("duplicate" in e["message"].lower() for e in data["errors"])


def test_validate_duplicate_values_list(client):
    tpl = _make_template(attributes={
        "val": {
            "misp-attribute": "text",
            "ui-priority": 1,
            "description": "test",
            "values_list": ["x", "x"],
        }
    })
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is False
    assert any("duplicate" in e["message"].lower() for e in data["errors"])


def test_validate_warning_no_requirements(client):
    tpl = _make_template()  # No required or requiredOneOf
    res = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res.get_json()
    assert data["valid"] is True
    assert any("No 'required' or 'requiredOneOf'" in w["message"] for w in data["warnings"])


def test_validate_no_body(client):
    res = client.post("/api/templates/validate", content_type="application/json")
    assert res.status_code == 400


def test_validate_existing_submodule_template(client):
    """Loading an existing template and re-validating should pass."""
    res = client.get("/api/templates/file")
    tpl = res.get_json()
    # Remove internal metadata
    tpl.pop("_source", None)
    res2 = client.post(
        "/api/templates/validate",
        data=json.dumps(tpl),
        content_type="application/json",
    )
    data = res2.get_json()
    assert data["valid"] is True
