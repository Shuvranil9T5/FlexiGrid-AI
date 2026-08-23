import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("FLEXIGRID_DB", os.path.join(os.path.dirname(__file__), "flexigrid.db"))

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS passports (pattern_id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS optimization_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL)")

def save_passport_record(payload: dict):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("INSERT INTO passports(pattern_id,status,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(pattern_id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at", (payload["pattern_id"], payload["status"], json.dumps(payload), now))

def list_saved_passports():
    with connect() as db:
        return [json.loads(row["payload"]) for row in db.execute("SELECT payload FROM passports ORDER BY updated_at DESC")]

def save_run(mode: str, result: dict):
    with connect() as db:
        db.execute("INSERT INTO optimization_runs(mode,result,created_at) VALUES(?,?,?)", (mode, json.dumps(result), datetime.now(timezone.utc).isoformat()))
