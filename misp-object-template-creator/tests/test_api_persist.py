"""Tests for the persist-to-repo endpoint and path safety."""

import json
import os
import uuid

import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def _make_template(name="persist-test", **overrides):
    tpl = {
        "name": name,
        "description": "Test template for persist",
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
        "requiredOneOf": ["value"],
    }
    tpl.update(overrides)
    return tpl


class TestPublicMode:
    """In public mode, persist should be rejected."""

    def test_persist_rejected_in_public_mode(self, client, monkeypatch):
        monkeypatch.setattr(config, "MODE", "public")
        tpl = _make_template()
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 403
        assert "private mode" in res.get_json()["error"]


class TestPrivateMode:
    """In private mode, persist should write to the misp-objects directory."""

    @pytest.fixture(autouse=True)
    def _set_private_mode(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "MODE", "private")
        # Point MISP_OBJECTS_PATH to a temp directory to avoid writing to the real submodule
        self.fake_objects = str(tmp_path / "fake-misp-objects")
        os.makedirs(os.path.join(self.fake_objects, "objects"), exist_ok=True)
        monkeypatch.setattr(config, "MISP_OBJECTS_PATH", self.fake_objects)

    def test_persist_creates_template(self, client):
        tpl = _make_template()
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is True
        assert "persisted" in data["message"].lower()

        # Verify the file was created in the fake objects dir
        defn = os.path.join(self.fake_objects, "objects", "persist-test", "definition.json")
        assert os.path.isfile(defn)
        with open(defn) as f:
            saved = json.load(f)
        assert saved["name"] == "persist-test"

    def test_persist_invalid_template_rejected(self, client):
        tpl = _make_template(name="")
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_persist_validation_errors(self, client):
        tpl = _make_template(**{"meta-category": "bogus"})
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 422

    def test_persist_no_body(self, client):
        res = client.post("/api/templates/persist", content_type="application/json")
        assert res.status_code == 400


class TestPathSafety:
    """Ensure template names cannot be used for path traversal."""

    @pytest.fixture(autouse=True)
    def _set_private_mode(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "MODE", "private")
        self.fake_objects = str(tmp_path / "fake-misp-objects")
        os.makedirs(os.path.join(self.fake_objects, "objects"), exist_ok=True)
        monkeypatch.setattr(config, "MISP_OBJECTS_PATH", self.fake_objects)

    @pytest.mark.parametrize("bad_name", [
        "../etc",
        "../../passwd",
        "foo/bar",
        "foo\\bar",
        ".hidden",
        "-leading-hyphen",
        "trailing-hyphen-",
        "has space",
        "has.dot",
        "has_underscore",
        "",
        "a" * 0,
    ])
    def test_persist_rejects_unsafe_names(self, client, bad_name):
        tpl = _make_template(name=bad_name)
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 400, f"Expected 400 for name '{bad_name}', got {res.status_code}"

    @pytest.mark.parametrize("bad_name", [
        "../etc",
        "../../passwd",
        "foo/bar",
        "-leading",
        "has space",
    ])
    def test_create_rejects_unsafe_names(self, client, bad_name):
        tpl = _make_template(name=bad_name)
        res = client.post(
            "/api/templates",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        # Should be 400 (bad name) or 422 (validation)
        assert res.status_code in (400, 422), f"Expected 400/422 for name '{bad_name}', got {res.status_code}"

    @pytest.mark.parametrize("good_name", [
        "my-template",
        "file",
        "network-connection",
        "a1-b2-c3",
        "ADS",
    ])
    def test_persist_accepts_safe_names(self, client, good_name):
        tpl = _make_template(name=good_name)
        res = client.post(
            "/api/templates/persist",
            data=json.dumps(tpl),
            content_type="application/json",
        )
        assert res.status_code == 200, f"Expected 200 for name '{good_name}', got {res.status_code}: {res.get_json()}"
