"""Tests for persist endpoint and path safety."""

import json
import os
import uuid

import pytest

import config


class TestPublicMode:
    """Persist should be rejected in public mode."""

    def test_persist_rejected(self, client, sample_bundle):
        res = client.post("/api/galaxies/persist",
                          data=json.dumps(sample_bundle),
                          content_type="application/json")
        assert res.status_code == 403
        assert "private mode" in res.get_json()["error"].lower()


class TestPrivateMode:
    """Persist should work in private mode."""

    @pytest.fixture(autouse=True)
    def enable_private_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "MODE", "private")
        # Redirect submodule path so persist doesn't write to the real repo
        fake_galaxy = str(tmp_path / "fake-galaxy")
        os.makedirs(os.path.join(fake_galaxy, "galaxies"), exist_ok=True)
        os.makedirs(os.path.join(fake_galaxy, "clusters"), exist_ok=True)
        monkeypatch.setattr(config, "MISP_GALAXY_PATH", fake_galaxy)

    def test_persist_creates_galaxy(self, client, sample_bundle):
        res = client.post("/api/galaxies/persist",
                          data=json.dumps(sample_bundle),
                          content_type="application/json")
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is True
        assert "galaxy_path" in data
        assert "cluster_path" in data

    def test_persist_invalid_rejected(self, client, sample_bundle):
        del sample_bundle["galaxy"]["name"]
        res = client.post("/api/galaxies/persist",
                          data=json.dumps(sample_bundle),
                          content_type="application/json")
        assert res.status_code == 422

    def test_persist_no_body(self, client):
        res = client.post("/api/galaxies/persist", content_type="application/json")
        assert res.status_code == 400

    UNSAFE_NAMES = [
        "../etc", "foo/bar", ".hidden", " spaces ", "under_score",
        "trailing-", "-leading", "dot.dot", "", "a" * 300,
    ]

    @pytest.mark.parametrize("name", UNSAFE_NAMES)
    def test_persist_rejects_unsafe_name(self, client, sample_bundle, name):
        sample_bundle["galaxy"]["type"] = name
        sample_bundle["cluster"]["type"] = name
        res = client.post("/api/galaxies/persist",
                          data=json.dumps(sample_bundle),
                          content_type="application/json")
        assert res.status_code in (400, 422), f"Expected rejection for '{name}'"
