import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analyzer import analyze
from src.extractor import extract_from_sample, extract_with_llm, parse_extraction
from src.privacy import require_demo_safe
from src.reporting import NOTICE, SECTIONS, as_text
from src.repository import database, samples


class ConsumerChecks(unittest.TestCase):
    def setUp(self):
        self.ctx = database(":memory:")
        self.conn = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        self.fixtures = {
            r["id"]: r for cat in ("PERFORMANCE", "SPORTS") for r in samples(self.conn, cat)
        }

    def result(self, sample_id="SP-FEST", **overrides):
        row = self.fixtures[sample_id]
        data = extract_from_sample(row, row["text"])
        data.update(overrides)
        return analyze(data, self.conn, row["text"])

    def test_01_festival(self):
        r = self.result()
        self.assertEqual(
            (r["level"], r["premium_krw"], r["premium_pct_vs_list"]), ("CAUTION", 180000, 150.0)
        )

    def test_02_musical(self):
        r = self.result("SP-MUS")
        self.assertEqual((r["level"], r["premium_krw"]), ("CAUTION", 0))
        self.assertIn("캡처", " ".join(r["facts"]))

    def test_03_baseball(self):
        r = self.result("SP-BASE")
        self.assertEqual((r["level"], r["premium_pct_vs_list"]), ("REVIEW", 0))
        self.assertIn("선물하기", " ".join(r["unknowns"]))

    def test_04_unregistered_event(self):
        r = self.result(event_name="이름 없는 가상 행사")
        self.assertEqual(r["level"], "INSUFFICIENT")
        self.assertIsNone(r["benchmark_source"])
        self.assertIsNone(r["premium_krw"])

    def test_05_private_input_blocked_before_client(self):
        with patch("openai.OpenAI") as client:
            for text in [
                "연락 010-1234-5678",
                "연락 ０１０－１２３４－５６７８",
                "가상 주소 demo@example.invalid",
                "가상 계좌 123-456-78901",
            ]:
                with self.subTest(text=text), self.assertRaisesRegex(ValueError, "개인정보"):
                    extract_with_llm(text, "unused")
            client.assert_not_called()

    def test_06_text_download(self):
        for sample in self.fixtures:
            r = self.result(sample)
            result = as_text(r)
            self.assertEqual(
                [title for _, title in SECTIONS],
                [line[1:-1] for line in result.splitlines() if line.startswith("[")],
            )
            self.assertIn(NOTICE, result)
            self.assertIn("SRC-DEMO", result)
            self.assertEqual(r["legal_verdict"], "NOT_DETERMINED")

    def test_07_missing_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch("openai.OpenAI") as client:
            with self.assertRaisesRegex(ValueError, "키가 설정되지"):
                extract_with_llm("개인정보 없는 가상 공연 글")
            client.assert_not_called()

    def test_08_sources_and_unknowns(self):
        for sample in self.fixtures:
            r = self.result(sample)
            self.assertIn("SRC-DEMO", r["benchmark_source"])
            self.assertIn("SRC-DEMO", r["policy_source"])
            self.assertIn("실제 구입가", " ".join(r["unknowns"]))

    def test_no_preset_for_edited_text(self):
        row = self.fixtures["SP-FEST"]
        with self.assertRaisesRegex(ValueError, "수정한"):
            extract_from_sample(row, row["text"].replace("30만원", "3만원"))

    def test_blank_input_and_wrong_date(self):
        with self.assertRaises(ValueError):
            require_demo_safe("   ")
        self.assertEqual(self.result(event_date="2026-12-13")["level"], "INSUFFICIENT")

    def test_missing_seat_and_price(self):
        for change in ({"seat_grade": "미등록석"}, {"asking_price_krw": None}):
            r = self.result(**change)
            self.assertEqual(r["level"], "INSUFFICIENT")
            self.assertIsNone(r["premium_pct_vs_list"])

    def test_no_fictional_policy(self):
        self.conn.execute("DELETE FROM policy WHERE event_id='EV-MUS-01'")
        r = self.result("SP-MUS")
        self.assertIsNone(r["policy_source"])
        self.assertEqual(r["level"], "INSUFFICIENT")

    def test_zero_benchmark(self):
        self.conn.execute("UPDATE price_rule SET list_price_krw=0 WHERE id='PR-FEST-VIP'")
        r = self.result()
        self.assertIsNone(r["premium_pct_vs_list"])
        self.assertEqual(r["premium_krw"], 300000)

    def test_schema_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE price_rule SET source_id='none' WHERE id='PR-FEST-VIP'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE price_rule SET list_price_krw=-5 WHERE id='PR-FEST-VIP'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""INSERT INTO price_rule SELECT 'duplicate',event_id,seat_grade,list_price_krw,
                              pricing_note,source_id FROM price_rule WHERE id='PR-FEST-VIP'""")

    def test_no_saved_user_results_and_reseed(self):
        with tempfile.TemporaryDirectory() as folder:
            storage = Path(folder) / "demo.db"
            for i in range(3):
                if i == 2:
                    storage.unlink()
                with database(storage) as c:
                    self.assertEqual(c.execute("SELECT COUNT(*) FROM sample_post").fetchone()[0], 3)
                    row = samples(c, "PERFORMANCE")[0]
                    analyze(extract_from_sample(row, row["text"]), c, row["text"])
                    self.assertEqual(c.execute("SELECT COUNT(*) FROM analysis_result").fetchone()[0], 0)

    def test_llm_parser_rejects_invalid_or_invented_evidence(self):
        for raw in (
            "not json",
            "[]",
            '{"asking_price_krw":-1}',
            '{"asking_price_krw":true}',
            '{"category":"OTHER"}',
            '{"evidence_phrases":["상상한 문장"]}',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_extraction(raw, "가상 공연")

    def test_llm_missing_and_total_only_prices(self):
        for field in ("event_name", "seat_grade", "asking_price_krw"):
            self.assertIsNone(parse_extraction("{}", "알 수 없음")[field])
        for text, price, expected in (
            ("VIP 한 장 30만원", 300000, 300000),
            ("두 장 총액 30만원", 300000, None),
            ("세 장에 30만원", 300000, None),
            ("R석 한 장 12만 7천 원", 127000, 127000),
            ("VIP 한 장 3만원", 300000, None),
        ):
            r = parse_extraction(
                json.dumps({"asking_price_krw": price, "evidence_phrases": [text]}), text
            )
            self.assertEqual(r["asking_price_krw"], expected)

class PriceContextRegression(unittest.TestCase):
    def test_total_and_per_ticket_in_the_same_quotation(self):
        text = "두 장 총액은 20만원, 장당 10만원입니다."
        for candidate, expected in [(200000, None), (100000, 100000)]:
            with self.subTest(price=candidate):
                raw = {"asking_price_krw": candidate, "evidence_phrases": [text]}
                self.assertEqual(parse_extraction(json.dumps(raw), text)["asking_price_krw"], expected)
