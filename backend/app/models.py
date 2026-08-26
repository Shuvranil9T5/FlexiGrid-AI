"""SQLite table definitions used by the lightweight MVP persistence layer."""

SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS passports (
        pattern_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_label TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
)
