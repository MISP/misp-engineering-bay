"""Shared fixtures for API tests."""

import os
import shutil
import tempfile
import uuid

import pytest
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """Redirect template output to a temp directory for every test."""
    out = str(tmp_path / "output")
    os.makedirs(out, exist_ok=True)
    monkeypatch.setattr(config, "OUTPUT_PATH", out)
    yield out


@pytest.fixture
def client():
    """Flask test client."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_template():
    """A minimal valid template dict."""
    return {
        "name": "test-object",
        "description": "A test object",
        "meta-category": "misc",
        "uuid": str(uuid.uuid4()),
        "version": 1,
        "attributes": {
            "value": {
                "misp-attribute": "text",
                "ui-priority": 1,
                "description": "A text value",
            }
        },
        "requiredOneOf": ["value"],
    }
