"""가상 행사 카탈로그. 사용자 입력과 분석 결과는 쓰지 않는다."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from tempfile import gettempdir

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = """
CREATE TABLE IF NOT EXISTS source_ref (
    id TEXT PRIMARY KEY, publisher TEXT NOT NULL, title TEXT NOT NULL, url TEXT,
    retrieved_on TEXT NOT NULL, scope TEXT, is_demo INTEGER NOT NULL CHECK(is_demo IN (0,1)));
CREATE TABLE IF NOT EXISTS event (
    id TEXT PRIMARY KEY, category TEXT NOT NULL CHECK(category IN ('PERFORMANCE','SPORTS')),
    name TEXT NOT NULL, event_date TEXT NOT NULL, venue TEXT, organizer TEXT);
CREATE TABLE IF NOT EXISTS price_rule (
    id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES event(id), seat_grade TEXT NOT NULL,
    list_price_krw INTEGER NOT NULL CHECK(list_price_krw>=0), pricing_note TEXT,
    source_id TEXT NOT NULL REFERENCES source_ref(id), UNIQUE(event_id,seat_grade));
CREATE TABLE IF NOT EXISTS policy (
    id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE REFERENCES event(id),
    transfer_status TEXT NOT NULL CHECK(transfer_status IN ('ALLOWED','PROHIBITED','CONDITIONAL','UNKNOWN')),
    id_check_required INTEGER CHECK(id_check_required IN (0,1)), notes TEXT,
    source_id TEXT NOT NULL REFERENCES source_ref(id));
CREATE TABLE IF NOT EXISTS sample_post (
    id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES event(id), label TEXT NOT NULL, text TEXT NOT NULL,
    extracted_seat_grade TEXT, extracted_price_krw INTEGER CHECK(extracted_price_krw>=0),
    extracted_evidence_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analysis_result (
    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, event_id TEXT REFERENCES event(id),
    sample_post_id TEXT REFERENCES sample_post(id), sanitized_input TEXT, extraction_json TEXT NOT NULL,
    result_json TEXT NOT NULL, model_provider TEXT, model_name TEXT, is_demo INTEGER NOT NULL CHECK(is_demo IN (0,1)));
CREATE INDEX IF NOT EXISTS ix_event_category_date ON event(category,event_date);
CREATE INDEX IF NOT EXISTS ix_price_event ON price_rule(event_id);
"""
SEED_COLUMNS = {
    "source_ref": "id publisher title url retrieved_on scope is_demo",
    "event": "id category name event_date venue organizer",
    "price_rule": "id event_id seat_grade list_price_krw pricing_note source_id",
    "policy": "id event_id transfer_status id_check_required notes source_id",
    "sample_post": "id event_id label text extracted_seat_grade extracted_price_krw extracted_evidence_json",
}


def initialize(conn):
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    seed = json.loads((ROOT / "data" / "demo_seed.json").read_text(encoding="utf-8"))
    with conn:
        for table, fields in SEED_COLUMNS.items():
            columns = fields.split()
            rows = seed[table]
            if table == "sample_post":
                for row in rows:
                    row["extracted_evidence_json"] = json.dumps(row["evidence"], ensure_ascii=False)
            params = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({params}) ON CONFLICT(id) DO NOTHING"
            conn.executemany(sql, [tuple(row[c] for c in columns) for row in rows])


@contextmanager
def database(path=None):
    target = (
        path
        or os.getenv("TICKETGUARD_DB_PATH")
        or Path(gettempdir()) / "ticketguard-ai-catalog-v1.sqlite3"
    )
    conn = sqlite3.connect(target, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        initialize(conn)
        yield conn
    finally:
        conn.close()


def samples(conn, category):
    return [
        dict(r)
        for r in conn.execute(
            """
        SELECT s.*, e.name AS event_name, e.category, e.event_date
        FROM sample_post s JOIN event e ON e.id=s.event_id
        WHERE e.category=? ORDER BY s.rowid""",
            (category,),
        )
    ]


def find_event(conn, name, category, date=None):
    if not name or category not in {"PERFORMANCE", "SPORTS"}:
        return None
    rows = conn.execute(
        """
        SELECT * FROM event WHERE name=? AND category=? AND (? IS NULL OR event_date=?)
        LIMIT 2""",
        (name, category, date, date),
    ).fetchall()
    return rows[0] if len(rows) == 1 else None


def get_grounding(conn, event_id, grade):
    source_fields = "s.id AS ref_id,s.title AS source_title,s.retrieved_on,s.is_demo"
    price = conn.execute(
        f"""SELECT p.*, {source_fields} FROM price_rule p
        JOIN source_ref s ON p.source_id=s.id WHERE p.event_id=? AND p.seat_grade=?""",
        (event_id, grade),
    ).fetchone()
    policy = conn.execute(
        f"""SELECT p.*, {source_fields} FROM policy p
        JOIN source_ref s ON p.source_id=s.id WHERE p.event_id=?""",
        (event_id,),
    ).fetchone()
    return price, policy
