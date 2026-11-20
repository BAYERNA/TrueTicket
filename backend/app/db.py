from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from .models import MarketPost, NewMarketPost


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
KST = timezone(timedelta(hours=9))
SEED_COLUMNS = {
    "events": ("id", "name", "venue", "date", "session_id", "session_label", "seat_grades", "booking_fee"),
    "accounts": ("account_id", "nickname", "created_at", "group_tag"),
    "bookings": (
        "booking_id", "event_id", "session_id", "account_id", "seat", "grade",
        "price_paid", "booked_at", "behavior_events", "status",
    ),
    "resale_posts": ("post_id", "event_id", "channel", "author_handle", "title", "body", "price", "created_at"),
    "waitlist": ("fan_id", "event_id", "grade", "joined_at", "status"),
}
RESET_ORDER = ("agent_logs", "cases", "analyses", *reversed(SEED_COLUMNS))
JSON_COLUMNS = {"seat_grades", "behavior_events"}


class Database:
    def __init__(self, path: Path, seed_path: Path):
        self.path = path
        self.seed_path = seed_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=10.0)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(analyses)")}
            if "details" not in columns:
                connection.execute("ALTER TABLE analyses ADD COLUMN details TEXT")
            if "gemini_cache" not in columns:
                connection.execute("ALTER TABLE analyses ADD COLUMN gemini_cache TEXT")
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM events LIMIT 1").fetchone() is None:
                self._insert_seed(connection, self._read_seed())

    def reset(self) -> dict[str, int]:
        seed = self._read_seed()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for table in RESET_ORDER:
                connection.execute(f"DELETE FROM {table}")
            existing = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ("checkpoints", "writes"):
                if table in existing:
                    connection.execute(f"DELETE FROM {table}")
            self._insert_seed(connection, seed)
            return {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in RESET_ORDER}

    def _read_seed(self) -> dict:
        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        if seed.get("schema_version") != 1:
            raise ValueError("지원하는 시드 스키마 버전은 1입니다.")
        return seed

    @staticmethod
    def _insert_seed(connection: sqlite3.Connection, seed: dict) -> None:
        for table, columns in SEED_COLUMNS.items():
            column_names = ", ".join(columns)
            placeholders = ", ".join("?" for _ in columns)
            rows = []
            for record in seed[table]:
                values = [record.get(name) if name == "price" else record[name] for name in columns]
                rows.append(tuple(
                    json.dumps(value, ensure_ascii=False) if name in JSON_COLUMNS else value
                    for name, value in zip(columns, values, strict=True)
                ))
            connection.executemany(f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})", rows)

    def list_events(self) -> list[dict]:
        with self.connect() as connection:
            events = [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY date, id")]
        for event in events:
            event["seat_grades"] = json.loads(event["seat_grades"])
        return events

    def list_market_posts(self, event_id: str | None) -> list[MarketPost]:
        query = "SELECT * FROM resale_posts"
        params: tuple[str, ...] = ()
        if event_id is not None:
            query += " WHERE event_id = ?"
            params = (event_id,)
        with self.connect() as connection:
            return [
                MarketPost.model_validate(dict(row))
                for row in connection.execute(query + " ORDER BY created_at DESC, post_id", params)
            ]

    def create_market_post(self, draft: NewMarketPost) -> MarketPost | None:
        post = MarketPost(
            **draft.model_dump(),
            post_id=f"demo-{uuid4().hex}",
            created_at=datetime.now(KST).isoformat(),
        )
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT id FROM events WHERE id = ?", (post.event_id,)).fetchone() is None:
                return None
            connection.execute(
                "INSERT INTO resale_posts (post_id, event_id, channel, author_handle, title, body, price, created_at) "
                "VALUES (:post_id, :event_id, :channel, :author_handle, :title, :body, :price, :created_at)",
                post.model_dump(),
            )
        return post

    def record_agent_step(
        self, run_id: str, event_id: str | None, step: str, tool: str, result: dict,
        latency_ms: int, tokens: int = 0,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO agent_logs (run_id, event_id, step, tool, input_summary, output_summary, latency, tokens) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, event_id, step, tool, json.dumps({"event_id": event_id}),
                 json.dumps(result, ensure_ascii=False), latency_ms, tokens),
            )

    def read_extractions(self) -> dict[str, dict]:
        with self.connect() as connection:
            return {
                row["post_id"]: json.loads(row["cached"])
                for row in connection.execute(
                    "SELECT post_id, COALESCE(gemini_cache, extracted) AS cached FROM analyses "
                    "WHERE gemini_cache IS NOT NULL OR extracted IS NOT NULL"
                )
            }

    def cache_gemini_extraction(self, post_id: str, result: dict) -> None:
        # A successful extraction can be resumed even if the later embedding request fails.
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO analyses(post_id, gemini_cache) VALUES (?, ?) "
                "ON CONFLICT(post_id) DO UPDATE SET gemini_cache = excluded.gemini_cache",
                (post_id, json.dumps(result, ensure_ascii=False)),
            )

    def save_extractions(self, results: dict[str, dict]) -> None:
        with self.connect() as connection:
            for post_id, result in results.items():
                case = connection.execute("SELECT status FROM cases WHERE post_id = ?", (post_id,)).fetchone()
                if case is not None and case["status"] != "신규":
                    continue
                fields = result["fields"]
                confidence = min(fields["confidence"]["price_per_ticket_krw"], fields["confidence"]["seats"]) if fields else 0.0
                risk_level = "확인 불가" if result["status"] == "review" else None
                connection.execute(
                    "INSERT INTO analyses (post_id, extracted, confidence, risk_level) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(post_id) DO UPDATE SET extracted = excluded.extracted, "
                    "confidence = excluded.confidence, risk_level = excluded.risk_level",
                    (post_id, json.dumps(result, ensure_ascii=False), confidence, risk_level),
                )

    def read_run(self, run_id: str) -> list[dict]:
        with self.connect() as connection:
            logs = [
                dict(row) for row in connection.execute(
                    "SELECT step, tool, input_summary, output_summary, latency, tokens "
                    "FROM agent_logs WHERE run_id = ? ORDER BY id",
                    (run_id,),
                )
            ]
        for log in logs:
            log["input_summary"] = json.loads(log["input_summary"])
            log["output_summary"] = json.loads(log["output_summary"])
        return logs

    def reserve_api_request(self, day: str) -> None:
        from .agent.gemini import AIUnavailable

        limit = max(0, int(os.getenv("TRUETICKET_DAILY_REQUEST_LIMIT", "100")))
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO api_usage(day, requests) VALUES (?, 0)", (day,))
            count = connection.execute("SELECT requests FROM api_usage WHERE day = ?", (day,)).fetchone()[0]
            if count >= limit:
                raise AIUnavailable("daily_request_limit")
            connection.execute("UPDATE api_usage SET requests = requests + 1 WHERE day = ?", (day,))

    def save_analyses(self, records: dict[str, dict]) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for post_id, record in records.items():
                previous = connection.execute("SELECT status FROM cases WHERE post_id = ?", (post_id,)).fetchone()
                if previous is not None and previous["status"] != "신규":
                    continue
                extraction = record["extraction"]
                fields = extraction.get("fields") or {}
                confidence = fields.get("confidence") or {}
                ids = record["match"]["matched_booking_ids"]
                risk = record["risk"]
                score = max((b["bot"]["score"] for b in record["match"]["bookings"]), default=0)
                connection.execute(
                    "INSERT INTO analyses(post_id, extracted, confidence, matched_booking_id, matched_booking_ids, "
                    "bot_score, cluster_id, rule_hits, risk_level, explanation, details) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(post_id) DO UPDATE SET "
                    "extracted=excluded.extracted, confidence=excluded.confidence, matched_booking_id=excluded.matched_booking_id, "
                    "matched_booking_ids=excluded.matched_booking_ids, bot_score=excluded.bot_score, cluster_id=excluded.cluster_id, "
                    "rule_hits=excluded.rule_hits, risk_level=excluded.risk_level, explanation=excluded.explanation, details=excluded.details",
                    (post_id, json.dumps(extraction, ensure_ascii=False), min(confidence.get("seats", 0), confidence.get("price_per_ticket_krw", 0)),
                     ids[0] if ids else None, json.dumps(ids), score, record["cluster"]["cluster_id"],
                     json.dumps(risk["rule_hits"]), risk["risk_level"], record["explanation"]["text"], json.dumps(record, ensure_ascii=False)),
                )
                connection.execute("INSERT OR IGNORE INTO cases(case_id, post_id, status) VALUES (?, ?, '신규')", (f"case-{post_id}", post_id))

    def list_cases(self, event_id: str | None = None, risk: str | None = None) -> list[dict]:
        query = "SELECT c.*, a.details FROM cases c JOIN analyses a USING(post_id) JOIN resale_posts p USING(post_id) WHERE a.details IS NOT NULL"
        params = []
        if event_id:
            query += " AND p.event_id = ?"
            params.append(event_id)
        if risk:
            query += " AND a.risk_level = ?"
            params.append(risk)
        with self.connect() as connection:
            rows = connection.execute(query + " ORDER BY CASE a.risk_level WHEN '높음' THEN 0 WHEN '중간' THEN 1 WHEN '확인 불가' THEN 2 ELSE 3 END, c.post_id", params).fetchall()
        cases = []
        for row in rows:
            record = json.loads(row["details"])
            fields = record["extraction"].get("fields") or {}
            cases.append({"case_id": row["case_id"], "post_id": row["post_id"], "status": row["status"],
                          "title": record["post"]["title"], "event_id": record["post"]["event_id"],
                          "risk_level": record["risk"]["risk_level"], "rule_hits": record["risk"]["rule_hits"],
                          "seats": fields.get("seats"), "price_per_ticket_krw": fields.get("price_per_ticket_krw"),
                          "matched_booking_ids": record["match"]["matched_booking_ids"],
                          "provider": record["extraction"].get("provider", "openai")})
        return cases

    def get_case(self, case_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT c.*, a.details FROM cases c JOIN analyses a USING(post_id) WHERE case_id = ?", (case_id,)).fetchone()
            if row is None or row["details"] is None:
                return None
            record = json.loads(row["details"])
            for booking in record["match"]["bookings"]:
                current = connection.execute("SELECT status FROM bookings WHERE booking_id = ?", (booking["booking_id"],)).fetchone()
                booking["current_status"] = current["status"] if current else "unknown"
            related = []
            for post_id in record["cluster"]["post_ids"]:
                source = connection.execute("SELECT details FROM analyses WHERE post_id = ?", (post_id,)).fetchone()
                if source and source["details"]:
                    peer = json.loads(source["details"])
                    related.append({"post_id": post_id, "case_id": f"case-{post_id}", "title": peer["post"]["title"],
                                    "author_handle": peer["post"]["author_handle"], "channel": peer["post"]["channel"]})
        return {"case_id": case_id, "status": row["status"], "actions": json.loads(row["actions"]),
                **record, "related_posts": related}

    def overview(self) -> dict:
        with self.connect() as connection:
            statuses = dict(connection.execute("SELECT status, COUNT(*) FROM cases GROUP BY status").fetchall())
            risks = dict(connection.execute("SELECT risk_level, COUNT(*) FROM analyses WHERE details IS NOT NULL GROUP BY risk_level").fetchall())
            latest = connection.execute("SELECT run_id FROM agent_logs ORDER BY id DESC LIMIT 1").fetchone()
            offered = connection.execute("SELECT COUNT(*) FROM waitlist WHERE status = 'offered'").fetchone()[0]
            usage = dict(connection.execute("SELECT day, requests FROM api_usage ORDER BY day DESC LIMIT 3").fetchall())
            false_positives = sum(
                any(action.get("false_positive") for action in json.loads(row["actions"]))
                for row in connection.execute("SELECT actions FROM cases WHERE status = '정상 종료'")
            )
        return {"case_count": sum(statuses.values()), "statuses": statuses, "risks": risks,
                "offered_count": offered, "false_positive_count": false_positives,
                "latest_run_id": latest["run_id"] if latest else None,
                "api_requests": usage, "daily_request_limit": max(0, int(os.getenv("TRUETICKET_DAILY_REQUEST_LIMIT", "100")))}
