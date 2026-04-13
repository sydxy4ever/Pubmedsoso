"""SQLite database connection management."""

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL DEFAULT '',
    authors TEXT NOT NULL DEFAULT '',
    journal TEXT NOT NULL DEFAULT '',
    pub_year TEXT NOT NULL DEFAULT '',
    impact_factor TEXT NOT NULL DEFAULT '',
    jcr_quartile TEXT NOT NULL DEFAULT '',
    cas_quartile TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS search_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
"""


_MIGRATE_SQL = [
    "ALTER TABLE articles ADD COLUMN impact_factor TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE articles ADD COLUMN jcr_quartile TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE articles ADD COLUMN cas_quartile TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE articles ADD COLUMN pub_year TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE articles ADD COLUMN search_id INTEGER NOT NULL DEFAULT 0",
]


class Database:
    """Manages SQLite database connections and schema."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Initialize database schema. Idempotent with migration support."""
        conn = self.get_connection()
        try:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
            try:
                for sql in _MIGRATE_SQL:
                    conn.execute(sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()

    def set_meta(self, key: str, value: str) -> None:
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO search_meta (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()

    def get_meta(self, key: str) -> str:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT value FROM search_meta WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            return row["value"] if row else ""
        except sqlite3.OperationalError:
            return ""
        finally:
            conn.close()

    def create_search(self, keyword: str, created_at: str) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO searches (keyword, created_at) VALUES (?, ?)",
                (keyword, created_at),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.OperationalError:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT ''
                );
            """)
            conn.commit()
            cursor = conn.execute(
                "INSERT INTO searches (keyword, created_at) VALUES (?, ?)",
                (keyword, created_at),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_searches(self) -> list[dict]:
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT id, keyword, created_at FROM searches ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
