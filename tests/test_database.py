from pubmedsoso.db.database import Database


def test_database_creates_file(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    assert tmp_db.exists()


def test_database_init_schema_idempotent(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    db.init_schema()


def test_database_get_connection(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    conn = db.get_connection()
    assert conn is not None
    conn.close()
