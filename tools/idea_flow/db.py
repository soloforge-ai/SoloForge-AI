from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = PACKAGE_DIR / "migrations"
DEFAULT_DB_PATH = PACKAGE_DIR.parents[1] / "data" / "runtime" / "idea_flow.db"


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def migrate(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    con.commit()

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        sql = path.read_text(encoding="utf-8")
        checksum = _checksum(sql)
        row = con.execute(
            "SELECT checksum FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        if row:
            if row["checksum"] != checksum:
                raise RuntimeError(f"Migration checksum changed after apply: {version}")
            continue

        script = "BEGIN IMMEDIATE;\n" + sql + "\n" + (
            "INSERT INTO schema_migrations(version, checksum, applied_at) "
            f"VALUES ('{version.replace("'", "''")}', '{checksum}', strftime('%Y-%m-%dT%H:%M:%fZ','now'));\n"
            "COMMIT;"
        )
        con.executescript(script)
