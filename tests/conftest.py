import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return tmp_path / "test.db"
