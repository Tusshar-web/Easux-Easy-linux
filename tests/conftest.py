"""
Pytest configuration and shared fixtures.
"""

import os
import tempfile
import pytest
from pathlib import Path
from ai_terminal.storage.database import Database
from ai_terminal.storage.repository import Repository


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def temp_db(temp_dir):
    db_file = temp_dir / "test_ai_terminal.db"
    db = Database(str(db_file))
    return db


@pytest.fixture
def temp_repo(temp_db):
    return Repository(temp_db)
