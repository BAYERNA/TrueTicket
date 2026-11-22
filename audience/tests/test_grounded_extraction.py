import json
import unittest
from unittest.mock import Mock

from evaluation.live_check import evaluate
from src.extractor import parse_extraction, price_is_supported, request_extraction, source_clauses


class GroundedExtractionTests(unittest.TestCase):
    def test_reference_fee_and_total_cannot_stand_in_for_unit_price(self):
        for text, wanted, rejected in [
            ("정가 105,000원, 판매가 85,000원입니다.", 85000, 105000),
            ("장당 75,000원, 배송비 3,000원 별도입니다.", 75000, 3000),
            ("두 장 합계 184,000원, 한 장당 92,000원입니다.", 92000, 184000),
            ("VIP 한 장 0원으로 나눠요. 택배비 4,000원 별도.", 0, 4000),
            ("105,000원(정가), 판매가 85,000원입니다.", 85000, 105000),
            ("8만원(판매가), 3천원(배송비)", 80000, 3000),
        ]:
            with self.subTest(text=text):
                self.assertTrue(price_is_supported(wanted, [text], text))
                self.assertFalse(price_is_supported(rejected, [text], text))
        self.assertTrue(price_is_supported(90000, ["정가 9만원에 양도합니다."], "정가 9만원에 양도합니다."))

    def test_only_unique_cited_explicit_offers_can_fill_a_missing_price(self):
        for text, indices, expected in [
            ("장당 0원. 배송비 5천원.", [0, 1], 0),
            ("VIP 장당 3만원. R석 장당 2만원.", [0], None),
            ("가격 협의. 정가 8만원.", [0, 1], None),
            ("R석입니다. 장당 7만원.", [0], None),
            ("두 장 총 12만원.", [0], None),
            ("장당 8만원~9만원 사이로 협의합니다.", [0], None),
        ]:
            with self.subTest(text=text):
                result = parse_extraction(json.dumps({"evidence_indices": indices}), text)
                self.assertEqual(result["asking_price_krw"], expected)
        self.assertFalse(price_is_supported(150000, ["5만원"], "한 장 15만원"))
        for text in ("장당 8만원 - 9만원 사이로 협의합니다.", "장당 8만원에서 9만원 사이로 협의합니다."):
            for price in (80000, 90000):
                with self.subTest(text=text, price=price):
                    self.assertFalse(price_is_supported(price, [text], text))

    def test_date_and_seat_need_literal_source_support(self):
        text = "겨울무대. 등급과 날짜는 미정이에요."
        result = parse_extraction(json.dumps({
            "event_name": "행사 이름", "event_date": "2027-12-22",
            "seat_grade": "VIP", "evidence_indices": [0, 1],
        }), text)
        self.assertIsNone(result["event_name"])
        self.assertIsNone(result["event_date"])
        self.assertIsNone(result["seat_grade"])
        text = "2027. 3. 7. 눈꽃축제 VIP석입니다."
        result = parse_extraction(json.dumps({
            "event_date": "2027-03-07", "seat_grade": "vip석", "evidence_indices": [0, 1],
        }), text)
        self.assertEqual(result["event_date"], "2027-03-07")
        self.assertEqual(result["seat_grade"], "VIP")
        self.assertIsNone(parse_extraction(
            '{"seat_grade":"R","evidence_indices":[0]}', "River 공연 좌석은 미정."
        )["seat_grade"])

    def test_recovered_title_evidence_does_not_authorize_uncited_price(self):
        text = "바람 공연 2027-04-05 장당 45,000원. R석입니다."
        payload = {"event_name": "바람 공연", "event_date": "2027-04-05", "seat_grade": "R",
                   "asking_price_krw": 45000, "evidence_indices": [1, 1]}
        result = parse_extraction(json.dumps(payload), text)
        self.assertEqual(result["event_name"], "바람 공연")
        self.assertEqual(result["event_date"], "2027-04-05")
        self.assertIsNone(result["asking_price_krw"])
        self.assertEqual(result["evidence_phrases"], source_clauses(text))

    def test_bad_indices_and_fabricated_legacy_quotes_are_rejected(self):
        for indices in ([True], [1], [-1], ["0"], None):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                parse_extraction(json.dumps({"evidence_indices": indices}), "하나뿐인 구절")
        with self.assertRaises(ValueError):
            parse_extraction('{"evidence_phrases":["없는 근거"]}', "실제 구절")

    def test_schema_candidates_belong_only_to_current_post(self):
        client = Mock()
        for text, prices, dates in [
            ("2027년 3월 7일 장당 0원, 배송비 3천원.", [0, None], ["2027-03-07", None]),
            ("2027-02-30 날짜 확인 중. 두 장 합계 10만원.", [None], [None]),
        ]:
            request_extraction(client, "test", text)
            args = client.chat.completions.create.call_args.kwargs
            properties = args["response_format"]["json_schema"]["schema"]["properties"]
            self.assertEqual(properties["asking_price_krw"]["enum"], prices)
            self.assertEqual(properties["event_date"]["enum"], dates)

    def test_empty_evaluation_cannot_be_reported_as_finished(self):
        with self.assertRaisesRegex(ValueError, "하나 이상"):
            evaluate([], "test-model")
