"""Shared pytest fixtures for dotx tests."""

import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """
    Isolate the database for tests by setting XDG_DATA_HOME to a temporary directory.

    This ensures tests don't interact with the user's actual database.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    return data_dir
