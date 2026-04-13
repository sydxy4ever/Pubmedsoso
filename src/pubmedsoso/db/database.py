"""SQLite database connection management."""

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    authors TEXT NOT NULL DEFAULT '',
    journal TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '',
    pmid INTEGER,
    pmcid TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    affiliations TEXT NOT NULL DEFAULT '',
    free_status INTEGER NOT NULL DEFAULT 0,
    is_review INTEGER NOT NULL DEFAULT 0,
    save_path TEXT NOT NULL DEFAULT ''
);
"""


class Database:
    """Manages SQLite database connections and schema."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get a new database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Initialize database schema. Idempotent."""
        conn = self.get_connection()
        try:
            conn.execute(_SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()
