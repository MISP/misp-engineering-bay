"""Tests for the validation endpoint."""

import json
import uuid


def test_validate_valid_bundle(client, sample_bundle):
    """POST /api/galaxies/validate accepts a valid bundle."""
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    assert res.status_code == 200
    data = res.get_json()
    assert data["valid"] is True


def test_validate_missing_galaxy_name(client, sample_bundle):
    del sample_bundle["galaxy"]["name"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False
    assert any("name" in e["path"].lower() for e in data["errors"])


def test_validate_missing_cluster_name(client, sample_bundle):
    del sample_bundle["cluster"]["name"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_type_mismatch(client, sample_bundle):
    sample_bundle["cluster"]["type"] = "different-type"
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False
    assert any("type" in e["path"].lower() for e in data["errors"])


def test_validate_invalid_galaxy_uuid(client, sample_bundle):
    sample_bundle["galaxy"]["uuid"] = "not-a-uuid"
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_bad_version(client, sample_bundle):
    sample_bundle["galaxy"]["version"] = -1
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_missing_authors(client, sample_bundle):
    del sample_bundle["cluster"]["authors"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_missing_source(client, sample_bundle):
    del sample_bundle["cluster"]["source"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_missing_values(client, sample_bundle):
    del sample_bundle["cluster"]["values"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_empty_value_name(client, sample_bundle):
    sample_bundle["cluster"]["values"] = [{"value": ""}]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_invalid_value_uuid(client, sample_bundle):
    sample_bundle["cluster"]["values"] = [{"value": "test", "uuid": "bad"}]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_related_missing_dest_uuid(client, sample_bundle):
    sample_bundle["cluster"]["values"] = [{
        "value": "test",
        "related": [{"type": "similar"}],
    }]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_related_missing_type(client, sample_bundle):
    sample_bundle["cluster"]["values"] = [{
        "value": "test",
        "related": [{"dest-uuid": str(uuid.uuid4())}],
    }]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_kill_chain_cross_validation(client, sample_matrix_bundle):
    """Valid kill_chain entries should pass."""
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_matrix_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is True


def test_validate_kill_chain_invalid_entry_warns(client, sample_matrix_bundle):
    """Invalid kill_chain entries produce warnings, not errors."""
    sample_matrix_bundle["cluster"]["values"][0]["meta"]["kill_chain"] = ["test-scope:nonexistent-phase"]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_matrix_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is True  # Warning, not error
    assert len(data["warnings"]) > 0


def test_validate_no_body(client):
    res = client.post("/api/galaxies/validate", content_type="application/json")
    assert res.status_code == 400


def test_validate_missing_galaxy(client):
    res = client.post("/api/galaxies/validate",
                      data=json.dumps({"cluster": {}}),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_missing_cluster(client):
    res = client.post("/api/galaxies/validate",
                      data=json.dumps({"galaxy": {"name": "x", "type": "x", "uuid": str(uuid.uuid4()), "version": 1, "description": "x"}}),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is False


def test_validate_duplicate_value_warns(client, sample_bundle):
    """Duplicate values produce warnings."""
    sample_bundle["cluster"]["values"] = [
        {"value": "dup"},
        {"value": "dup"},
    ]
    res = client.post("/api/galaxies/validate",
                      data=json.dumps(sample_bundle),
                      content_type="application/json")
    data = res.get_json()
    assert len(data["warnings"]) > 0


def test_validate_existing_submodule_galaxy(client):
    """Loading and re-validating a submodule galaxy should work."""
    # Get an existing galaxy
    get_res = client.get("/api/galaxies/backdoor")
    assert get_res.status_code == 200
    bundle = get_res.get_json()

    # Remove internal fields
    bundle.pop("_source", None)

    res = client.post("/api/galaxies/validate",
                      data=json.dumps(bundle),
                      content_type="application/json")
    data = res.get_json()
    assert data["valid"] is True
