import json
import sqlite3
from datetime import datetime, timezone

from app.config import settings
from app.models import SCHEMA_STATEMENTS


DB_PATH = settings.database_path


def connect():
    database = sqlite3.connect(DB_PATH)
    database.row_factory = sqlite3.Row
    return database


def init_db():
    with connect() as database:
        for statement in SCHEMA_STATEMENTS:
            database.execute(statement)


def save_passport_record(payload: dict):
    init_db()
    current_time = datetime.now(timezone.utc).isoformat()

    with connect() as database:
        database.execute(
            """
            INSERT INTO passports (
                pattern_id,
                status,
                payload,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pattern_id)
            DO UPDATE SET
                status = excluded.status,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                payload["pattern_id"],
                payload["status"],
                json.dumps(payload),
                current_time,
            ),
        )


def list_saved_passports():
    init_db()

    with connect() as database:
        rows = database.execute(
            """
            SELECT payload
            FROM passports
            ORDER BY updated_at DESC
            """
        )

        return [json.loads(row["payload"]) for row in rows]


def save_run(mode: str, result: dict):
    init_db()

    with connect() as database:
        database.execute(
            """
            INSERT INTO optimization_runs (
                mode,
                result,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                mode,
                json.dumps(result),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def save_analysis(source_label: str, summary: dict):
    init_db()

    with connect() as database:
        database.execute(
            """
            INSERT INTO analysis_runs (
                source_label,
                summary,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                source_label,
                json.dumps(summary),
                datetime.now(timezone.utc).isoformat(),
            ),
        )