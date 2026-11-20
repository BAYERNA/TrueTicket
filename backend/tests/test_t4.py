import json
from pathlib import Path
import unittest

import httpx

from backend.app.agent.extraction import (
    EMBEDDING_MODEL, EXTRACTION_MODEL, LISTING_SCHEMA, LLM_FIELDS, extract_batch, extract_listing,
    extraction_request, prepare_listing,
)
from backend.app.agent.pii import mask_pii
from backend.app.evaluation.t4 import evaluate
from backend.app.models import MarketPost


ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8"))
GOLD = json.loads((ROOT / "data/evaluation/evaluation_set.json").read_text(encoding="utf-8"))
POSTS = {item["post_id"]: MarketPost.model_validate(item) for item in SEED["resale_posts"]}
EVENTS = SEED["events"]


def fields(values: dict | None = None, evidence: dict | None = None) -> dict:
    values = values or {}
    return {
        **{key: values.get(key) for key in LLM_FIELDS},
        "confidence": {key: 0.93 if values.get(key) is not None else 0.0 for key in LLM_FIELDS},
        "evidence": evidence or {"seats": [], "quantity": [], "price_per_ticket_krw": []},
    }


def reference_fields() -> dict:
    return fields({
        "event_id": "event-001",
        "session_id": "event-001-session-01",
        "seats": ["A-01-01", "A-01-02"],
        "quantity": 2,
        "price_per_ticket_krw": 137_000,
        "trade_method": "아옮",
    }, {
        "seats": ["A-01-01", "A-01-02"],
        "quantity": ["2장"],
        "price_per_ticket_krw": ["정가 장당 11만 원", "추가금 장당 27,000원"],
    })


def provider_json(values: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "status": "completed",
        "model": EXTRACTION_MODEL,
        "usage": {"input_tokens": 21, "output_tokens": 10},
        "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(values, ensure_ascii=False)},
        ]}],
    })


class RequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_10_masking_cases_at_http_boundary(self):
        requests = {}

        def provider(request: httpx.Request) -> httpx.Response:
            index = len(requests)
            requests[cases[index]["post_id"]] = json.loads(request.content)
            return provider_json(fields())

        cases = GOLD["masking_cases"]
        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            for case in cases:
                prepared = prepare_listing(POSTS[case["post_id"]], EVENTS)
                await extract_listing(client, prepared, skip_unpriced=False)
                self.assertEqual(prepared.masked_counts, {kind: 1 for kind in case["synthetic_values"]})

        self.assertEqual(len(requests), 10)
        for case in cases:
            payload = requests[case["post_id"]]
            input_text = payload["input"][0]["content"][0]["text"]
            for value in case["synthetic_values"].values():
                self.assertNotIn(value, input_text)
            self.assertEqual(set(json.loads(input_text)), {"title", "body", "events"})

    async def test_t4_injection_pairs_have_identical_inputs_and_review(self):
        def provider(request: httpx.Request) -> httpx.Response:
            return provider_json(fields())

        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            for case in GOLD["injection_cases"]:
                post = POSTS[case["post_id"]]
                with self.subTest(post_id=post.post_id):
                    prepared = prepare_listing(post, EVENTS)
                    baseline = prepare_listing(post.model_copy(update={"body": case["baseline_body"]}), EVENTS)
                    self.assertEqual(prepared.removed_instructions, 1)
                    self.assertEqual(extraction_request(prepared), extraction_request(baseline))
                    self.assertEqual(
                        await extract_listing(client, prepared, skip_unpriced=False),
                        await extract_listing(client, baseline, skip_unpriced=False),
                    )

    async def test_reference_extraction_and_structured_schema(self):
        def provider(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(request.url.path, "/v1/responses")
            self.assertEqual(payload["model"], "gpt-5.6-terra")
            self.assertFalse(payload["store"])
            self.assertTrue(payload["text"]["format"]["strict"])
            return provider_json(reference_fields())

        for schema in (LISTING_SCHEMA, *LISTING_SCHEMA.get("$defs", {}).values()):
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["properties"]), set(schema["required"]))
        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            result = await extract_listing(client, prepare_listing(POSTS["post-017"], EVENTS))
        self.assertEqual(result.status, "extracted")
        self.assertEqual(result.listing.price_per_ticket_krw, 137_000)
        self.assertEqual(result.listing.seats, ["A-01-01", "A-01-02"])
        self.assertEqual(result.listing.quantity, 2)

    async def test_invalid_schema_is_retried_only_once(self):
        requests = []

        def provider(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return provider_json({"quantity": "2"})

        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            result = await extract_listing(client, prepare_listing(POSTS["post-017"], EVENTS))
        self.assertEqual((result.status, result.reason, result.attempts), ("review", "invalid_schema", 2))
        self.assertIsNone(result.listing)
        self.assertEqual(requests[0]["input"], requests[1]["input"])
        self.assertIn("다시 추출", requests[1]["instructions"])
        self.assertEqual((result.input_tokens, result.output_tokens), (42, 20))

    async def test_retry_recovers_and_confidence_threshold_is_inclusive(self):
        events = []

        def provider(request: httpx.Request) -> httpx.Response:
            events.append(request)
            values = reference_fields()
            values["confidence"]["price_per_ticket_krw"] = 0.60 if len(events) == 2 else 0.5999
            if len(events) == 1:
                values["evidence"]["price_per_ticket_krw"] = ["원문에 없는 근거"]
            return provider_json(values)

        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            prepared = prepare_listing(POSTS["post-017"], EVENTS)
            recovered = await extract_listing(client, prepared)
            unclear = await extract_listing(client, prepared)
        self.assertEqual((recovered.status, recovered.attempts), ("extracted", 2))
        self.assertEqual((unclear.status, unclear.reason), ("review", "low_confidence"))

    async def test_batch_stops_configuration_errors_and_prefilters_unpriced(self):
        calls = []
        unknown = POSTS["post-017"].model_copy(update={
            "title": "한빛 티켓 양도", "body": "A구역 1열 1번 한 장. 가격은 아직 미정입니다.",
        })
        pending = {
            "no_price": prepare_listing(unknown, EVENTS),
            "probe": prepare_listing(POSTS["post-017"], EVENTS),
            "next": prepare_listing(POSTS["post-017"], EVENTS),
        }

        def provider(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(403)

        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            outcomes = await extract_batch(client, pending)
        self.assertEqual(list(outcomes), ["no_price", "probe"])
        self.assertEqual(outcomes["no_price"].source, "prefilter")
        self.assertEqual(outcomes["probe"].reason, "api_http_403")
        self.assertEqual(len(calls), 1)

    async def test_evaluator_distinguishes_wrong_fields_and_api_errors(self):
        def provider(request: httpx.Request) -> httpx.Response:
            values = reference_fields()
            values["price_per_ticket_krw"] = 274_000
            return provider_json(values)

        async with httpx.AsyncClient(base_url="https://api.openai.com", transport=httpx.MockTransport(provider)) as client:
            report = await evaluate(client, SEED, GOLD, "post-017")
        self.assertEqual(report["summary"]["schema_valid"], 1)
        self.assertEqual(report["summary"]["field_accuracy_by_name"]["price_per_ticket_krw"], 0)
        self.assertEqual(report["wrong_cases"][0]["post_id"], "post-017")
        self.assertEqual(report["summary"]["embedding_model"], EMBEDDING_MODEL)


class LocalTests(unittest.TestCase):
    def test_five_glossary_terms(self):
        post = POSTS["post-017"].model_copy(update={"body": "정가 양도, 수고비, 플미, 아옮, 오만 원 추가."})
        meanings = {item["term"]: item["meaning"] for item in prepare_listing(post, EVENTS).slang}
        self.assertEqual(set(meanings), {"정가양도", "수고비", "플미", "아옮", "오만 추가"})
        self.assertEqual(meanings["오만 추가"], "50,000원 추가")

    def test_title_and_body_masking_preserve_currency_and_seats(self):
        title = "이름: 가상인 / 한빛 콘서트"
        body = "A-01-01, 137,000원. 연락처: +82 10-0000-0000 / 계좌번호: 000-000-000000 / a@example.invalid"
        prepared = prepare_listing(POSTS["post-017"].model_copy(update={"title": title, "body": body}), EVENTS)
        self.assertNotIn("가상인", prepared.model_input)
        self.assertNotIn("000-000-000000", prepared.model_input)
        self.assertIn("A-01-01, 137,000원", prepared.body)
        self.assertEqual(sum(prepared.masked_counts.values()), 4)
        self.assertEqual(mask_pii(prepared.body).text, prepared.body)
