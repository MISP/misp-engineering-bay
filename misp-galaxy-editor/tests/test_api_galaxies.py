"""Tests for galaxy API endpoints."""

import json


def test_list_galaxies(client):
    """GET /api/galaxies returns a list."""
    res = client.get("/api/galaxies")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    # Should have submodule galaxies
    assert len(data) > 0


def test_list_galaxies_filter_by_name(client):
    """GET /api/galaxies?name= filters by name."""
    res = client.get("/api/galaxies?name=threat")
    assert res.status_code == 200
    data = res.get_json()
    for g in data:
        assert "threat" in g["galaxy_name"].lower() or "threat" in g["type"].lower() or "threat" in g["cluster_name"].lower()


def test_list_galaxies_filter_by_namespace(client):
    """GET /api/galaxies?namespace= filters by namespace."""
    res = client.get("/api/galaxies?namespace=misp")
    assert res.status_code == 200
    data = res.get_json()
    for g in data:
        assert g["namespace"] == "misp"


def test_list_galaxies_filter_by_kill_chain(client):
    """GET /api/galaxies?has_kill_chain=true filters to matrix galaxies."""
    res = client.get("/api/galaxies?has_kill_chain=true")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) > 0
    for g in data:
        assert g["has_kill_chain"] is True


def test_get_galaxy_bundle(client):
    """GET /api/galaxies/<type> returns a full bundle."""
    res = client.get("/api/galaxies/threat-actor")
    assert res.status_code == 200
    data = res.get_json()
    assert "galaxy" in data
    assert "cluster" in data
    assert data["galaxy"]["type"] == "threat-actor"
    assert data["cluster"]["type"] == "threat-actor"
    assert data["_source"] == "misp-galaxy"


def test_get_galaxy_not_found(client):
    """GET /api/galaxies/<type> returns 404 for unknown types."""
    res = client.get("/api/galaxies/nonexistent-galaxy-xyz")
    assert res.status_code == 404


def test_get_galaxy_has_values(client):
    """GET returns cluster with values array."""
    res = client.get("/api/galaxies/backdoor")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data["cluster"]["values"], list)
    assert len(data["cluster"]["values"]) > 0


def test_get_galaxy_mismatched_filename(client):
    """GET resolves galaxies where filename differs from type."""
    res = client.get("/api/galaxies/amitt-misinformation-pattern")
    assert res.status_code == 200
    data = res.get_json()
    assert data["galaxy"]["type"] == "amitt-misinformation-pattern"


def test_generate_uuid(client):
    """GET /api/uuid returns a valid UUID."""
    res = client.get("/api/uuid")
    assert res.status_code == 200
    data = res.get_json()
    assert "uuid" in data
    assert len(data["uuid"]) == 36


def test_get_config(client):
    """GET /api/config returns mode."""
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.get_json()
    assert data["mode"] in ("public", "private")


def test_meta_suggestions(client):
    """GET /api/meta-suggestions returns reference data."""
    res = client.get("/api/meta-suggestions")
    assert res.status_code == 200
    data = res.get_json()
    assert "namespaces" in data
    assert "icons" in data
    assert "categories" in data
    assert "meta_keys" in data
    assert "relationship_types" in data
    assert isinstance(data["namespaces"], list)
    assert len(data["namespaces"]) > 0
