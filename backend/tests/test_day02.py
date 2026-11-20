import json
from collections import Counter, defaultdict
from pathlib import Path
import tempfile
import unittest

import httpx

from backend.app.adapters.bot_detection import bot_score
from backend.app.adapters.resale_monitor import FeedFormatError, parse_listings
from backend.app.main import create_app


ROOT = Path(__file__).resolve().parents[2]


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8"))
        cls.gold = json.loads((ROOT / "data/evaluation/evaluation_set.json").read_text(encoding="utf-8"))
        cls.bookings = {row["booking_id"]: row for row in cls.seed["bookings"]}

    def test_reference_post_qualifies_for_resale_based_high_risk(self):
        expected = self.gold["posts"]["post-017"]["expected"]
        listing = expected["extracted"]
        self.assertEqual(expected["risk_level"], "높음")
        self.assertEqual(expected["matched_booking_ids"], ["booking-0001", "booking-0002"])
        self.assertEqual(listing["seats"], ["A-01-01", "A-01-02"])
        self.assertEqual(listing["quantity"], 2)
        self.assertIn("R1", expected["rule_hits"])
        self.assertTrue({"R2", "R3"} & set(expected["rule_hits"]))
        for booking_id in expected["matched_booking_ids"]:
            self.assertGreater(listing["price_per_ticket_krw"], self.bookings[booking_id]["price_paid"])
        self.assertEqual(min(
            (item for item in self.seed["waitlist"] if item["event_id"] == "event-001" and item["grade"] == "R"),
            key=lambda item: (item["joined_at"], item["fan_id"]),
        )["fan_id"], "fan-001")

    def test_repeat_sales_join_confirmed_bookings_and_include_separate_sellers(self):
        groups = Counter()
        matches = defaultdict(set)
        for post in self.gold["posts"].values():
            expected = post["expected"]
            group = expected["seller_group_id"]
            if group is None:
                continue
            groups[group] += 1
            extraction = expected["extracted"]
            rows = [self.bookings[booking_id] for booking_id in expected["matched_booking_ids"]]
            self.assertEqual([booking["seat"] for booking in rows], extraction["seats"])
            for booking in rows:
                self.assertEqual(booking["event_id"], extraction["event_id"])
                self.assertEqual(booking["session_id"], extraction["session_id"])
                self.assertEqual(booking["status"], "confirmed")
                matches[group].add(booking["seat"])
        self.assertEqual(sorted(groups.values()), [5] * 5)
        self.assertEqual(sorted(map(len, matches.values())), [5, 5, 5, 5, 6])

    def test_missing_and_cancelled_seats(self):
        by_seat = {
            (row["event_id"], row["session_id"], row["seat"]): row
            for row in self.bookings.values()
        }
        counts = Counter()
        for post in self.gold["posts"].values():
            expected = post["expected"]
            reason = expected["matching_failure_reason"]
            if reason is None:
                continue
            extracted = expected["extracted"]
            cross_reference = (extracted["event_id"], extracted["session_id"], *extracted["seats"])
            self.assertEqual(expected["matched_booking_ids"], [])
            if reason == "seat_not_found":
                self.assertNotIn(cross_reference, by_seat)
            else:
                self.assertEqual(reason, "cancelled_booking")
                self.assertEqual(by_seat[cross_reference]["status"], "cancelled")
            counts[reason] += 1
        self.assertEqual(counts, {"seat_not_found": 7, "cancelled_booking": 3})

    def test_bot_boundaries_and_normal_accounts(self):
        normal_accounts = {row["account_id"] for row in self.seed["accounts"] if row["group_tag"] == "정상"}
        normal_scores = [
            bot_score(row["behavior_events"])["score"]
            for row in self.bookings.values() if row["account_id"] in normal_accounts
        ]
        self.assertEqual(len(normal_scores), 974)
        self.assertLessEqual(max(normal_scores), 0.3)
        for case in self.gold["bot_score_cases"]:
            events = self.bookings[case["booking_id"]]["behavior_events"]
            with self.subTest(booking_id=case["booking_id"]):
                result = bot_score(events)
                self.assertEqual(result["score"], case["expected_score"])
                self.assertEqual(result["score"] >= 0.8, case["expected_r4"])
                self.assertEqual(result["evidence"]["click_interval_count"], 4)
                self.assertEqual(
                    result["evidence"]["automation_signature_count"],
                    sum(event["event_type"] == "automation_signature" for event in events),
                )
        self.assertAlmostEqual(
            bot_score(self.bookings["booking-0004"]["behavior_events"])["evidence"]["click_interval_cv"],
            20 / 300,
        )


class MarketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.app = create_app(Path(temporary) / "test.sqlite3")
        await self.enterAsyncContext(self.app.router.lifespan_context(self.app))
        self.client = await self.enterAsyncContext(httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        ))

    async def test_database_and_html_feed_match_seed(self):
        items = (await self.client.get("/api/market/posts")).json()
        feed = await self.client.get("/api/market/feed")
        parsed = parse_listings(feed.text)
        self.assertEqual(len(parsed), 80)
        self.assertEqual([post.model_dump() for post in parsed], items)
        self.assertTrue(any(post.price is None for post in parsed))
        self.assertTrue(any(post.price is not None for post in parsed))
        self.assertNotIn("seller_group_id", feed.text)
        with self.app.state.db.connect() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0], 0)
        empty_feed = await self.client.get("/api/market/feed", params={"event_id": "no-listings"})
        self.assertEqual(parse_listings(empty_feed.text), ())
        with self.assertRaises(FeedFormatError):
            parse_listings("<h1>Invalid feed</h1>")

    async def test_unpriced_test_post_and_reset(self):
        created = await self.client.post("/api/market/posts", json={
            "event_id": "event-001",
            "title": '시연 <글>',
            "body": "가격 미정\n본문 줄바꿈 & <script>",
            "author_handle": '가상"운영자',
            "channel": "가상 SNS",
        })
        self.assertEqual(created.status_code, 201)
        inserted_post = created.json()
        feed = await self.client.get("/api/market/feed")
        self.assertNotIn("<script>", feed.text)
        parsed_post = next(post for post in parse_listings(feed.text) if post.post_id == inserted_post["post_id"])
        self.assertEqual(parsed_post.model_dump(), inserted_post)
        reset = await self.client.post("/api/demo/reset")
        self.assertEqual(reset.json()["counts"], {
            "events": 2, "accounts": 300, "bookings": 1000, "resale_posts": 80,
            "waitlist": 50, "analyses": 0, "cases": 0, "agent_logs": 0,
        })
        self.assertNotIn(inserted_post["post_id"], (await self.client.get("/api/market/feed")).text)
