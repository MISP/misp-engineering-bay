"""Shared fixtures for Galaxy Editor API tests."""

import os
import sys
import uuid

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """Redirect output to a temp directory for every test."""
    out = str(tmp_path / "output")
    os.makedirs(os.path.join(out, "galaxies"), exist_ok=True)
    os.makedirs(os.path.join(out, "clusters"), exist_ok=True)
    monkeypatch.setattr(config, "OUTPUT_PATH", out)
    # Invalidate cached type index (changes with monkeypatched paths)
    import galaxy_store
    galaxy_store._type_to_filename = None
    yield out


@pytest.fixture
def client():
    """Flask test client."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_bundle():
    """A minimal valid galaxy + cluster bundle."""
    return {
        "galaxy": {
            "name": "Test Galaxy",
            "description": "A test galaxy for unit tests",
            "type": "zz-editor-test-only",
            "uuid": str(uuid.uuid4()),
            "version": 1,
        },
        "cluster": {
            "name": "Test Cluster",
            "description": "A test cluster",
            "type": "zz-editor-test-only",
            "uuid": str(uuid.uuid4()),
            "version": 1,
            "authors": ["test-author"],
            "source": "Unit Tests",
            "category": "test",
            "values": [
                {"value": "test-value-1", "uuid": str(uuid.uuid4())},
            ],
        },
    }


@pytest.fixture
def sample_matrix_bundle():
    """A valid bundle with kill chain order (matrix galaxy)."""
    return {
        "galaxy": {
            "name": "Test Matrix Galaxy",
            "description": "A matrix-style test galaxy",
            "type": "test-matrix",
            "uuid": str(uuid.uuid4()),
            "version": 1,
            "kill_chain_order": {
                "test-scope": ["phase-1", "phase-2", "phase-3"],
            },
        },
        "cluster": {
            "name": "Test Matrix Cluster",
            "description": "Matrix cluster",
            "type": "test-matrix",
            "uuid": str(uuid.uuid4()),
            "version": 1,
            "authors": ["test"],
            "source": "Tests",
            "category": "test",
            "values": [
                {
                    "value": "technique-a",
                    "uuid": str(uuid.uuid4()),
                    "meta": {
                        "kill_chain": ["test-scope:phase-1"],
                    },
                },
                {
                    "value": "technique-b",
                    "uuid": str(uuid.uuid4()),
                    "meta": {
                        "kill_chain": ["test-scope:phase-2", "test-scope:phase-3"],
                    },
                },
            ],
        },
    }
