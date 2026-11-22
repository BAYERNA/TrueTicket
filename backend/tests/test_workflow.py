import asyncio
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.app.adapters.resale_monitor import CollectionResult
from backend.app.agent.extraction import prepare_listing
from backend.app.agent.gemini import AIUnavailable, Gemini
from backend.app.agent.local import extract_local
from backend.app.main import create_app
from backend.app.models import MarketPost
from backend.app.services.analysis import assess_risk


ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8"))
GOLD = json.loads((ROOT / "data/evaluation/evaluation_set.json").read_text(encoding="utf-8"))
POSTS = tuple(MarketPost.model_validate(p) for p in SEED["resale_posts"])


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.app = create_app(Path(temporary) / "demo.sqlite3")
        await self.enterAsyncContext(self.app.router.lifespan_context(self.app))
        self.api = await self.enterAsyncContext(httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test"))
        self.enterContext(patch("backend.app.agent.monitor.collect_posts", AsyncMock(return_value=CollectionResult("ok", POSTS, http_status=200))))
        await self.scan()

    async def scan(self, mode="local", expected_status="completed"):
        response = await self.api.post("/api/agent/runs", json={"mode": mode} if mode else {})
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["run_id"]
        for _ in range(200):
            run = (await self.api.get(f"/api/agent/runs/{run_id}")).json()
            if run["status"] != "running":
                break
            await asyncio.sleep(0.01)
        self.assertEqual(run["status"], expected_status)
        return run

    async def action(self, kind, case_id="case-post-017", **extra):
        return await self.api.post(f"/api/cases/{case_id}/actions", json={"type": kind, "approved": True, **extra})

    async def test_all_rule_cases_and_multi_seat_match(self):
        items = (await self.api.get("/api/cases")).json()
        self.assertEqual(len(items), 80)
        for item in items:
            gold = GOLD["posts"][item["post_id"]]["expected"]
            self.assertEqual(item["matched_booking_ids"], gold["matched_booking_ids"], item["post_id"])
            self.assertEqual(item["risk_level"], gold["risk_level"], item["post_id"])
            self.assertEqual(item["rule_hits"], gold["rule_hits"], item["post_id"])
        case = (await self.api.get("/api/cases/case-post-017")).json()
        self.assertEqual(case["match"]["matched_booking_ids"], ["booking-0001", "booking-0002"])
        self.assertEqual(case["risk"]["above_cost_seat_count"], 6)
        self.assertEqual(len(case["related_posts"]), 5)
        self.assertEqual({s["rule_id"] for s in case["explanation"]["sentences"]}, set(case["risk"]["rule_hits"]))
        self.assertFalse(case["explanation"]["generated_by_ai"])

    async def test_unapproved_and_unexpired_actions_are_rejected(self):
        response = await self.api.post("/api/cases/case-post-017/actions", json={"type": "cancel_redistribute"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual((await self.action("cancel_redistribute")).status_code, 409)
        self.assertEqual((await self.action("request_explanation")).status_code, 200)
        self.assertEqual((await self.action("cancel_redistribute")).status_code, 409)
        with self.app.state.db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist WHERE status='offered'").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT status FROM bookings WHERE booking_id='booking-0001'").fetchone()[0], "confirmed")

    async def test_approval_interrupt_atomic_cancel_retry_and_report(self):
        preview = (await self.api.post("/api/cases/case-post-017/approvals", json={"type": "request_explanation"})).json()
        snapshot = self.app.state.action_graph.get_state({"configurable": {"thread_id": preview["approval_id"]}})
        self.assertTrue(snapshot.next)
        self.assertNotIn("result", snapshot.values)
        self.assertEqual((await self.action("request_explanation", approval_id=preview["approval_id"])).status_code, 200)
        await self.api.post("/api/cases/case-post-017/simulate", json={"type": "deadline_elapsed"})
        preview = (await self.api.post("/api/cases/case-post-017/approvals", json={"type": "cancel_redistribute"})).json()
        first = (await self.action("cancel_redistribute", approval_id=preview["approval_id"])).json()
        repeated = (await self.action("cancel_redistribute", approval_id=preview["approval_id"])).json()
        self.assertTrue(repeated["replayed"])
        self.assertEqual(first["action"], repeated["action"])
        self.assertEqual(first["action"]["allocations"][0]["fan_id"], "fan-001")
        self.assertEqual(first["action"]["allocations"][0]["price"], 110000)
        self.assertEqual({b["current_status"] for b in first["case"]["match"]["bookings"]}, {"cancelled"})
        await self.scan()
        case = (await self.api.get("/api/cases/case-post-017")).json()
        self.assertEqual(case["match"]["matched_booking_ids"], ["booking-0001", "booking-0002"])
        report = (await self.api.get("/api/cases/case-post-017/report")).text
        for text in ("post-017", "booking-0001", "booking-0002", "R1", "R2", "R4", "fan-001", "post-069", "deadline_elapsed"):
            self.assertIn(text, report)
        with self.app.state.db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist WHERE status='offered'").fetchone()[0], 2)

    async def test_explanation_prevents_cancel_and_normal_close_records_false_positive(self):
        await self.action("request_explanation")
        await self.api.post("/api/cases/case-post-017/simulate", json={"type": "explanation_received", "text": "친구 대신 정가 양도"})
        await self.api.post("/api/cases/case-post-017/simulate", json={"type": "deadline_elapsed"})
        self.assertEqual((await self.action("cancel_redistribute")).status_code, 409)
        closed = (await self.action("close_normal")).json()["case"]
        self.assertEqual(closed["status"], "정상 종료")
        self.assertTrue(closed["actions"][-1]["false_positive"])

    async def test_approval_cannot_cross_case_and_reset_removes_checkpoint(self):
        preview = (await self.api.post("/api/cases/case-post-017/approvals", json={"type": "request_explanation"})).json()
        self.assertEqual((await self.action("request_explanation", case_id="case-post-030", approval_id=preview["approval_id"])).status_code, 403)
        await self.api.post("/api/demo/reset")
        state = self.app.state.action_graph.get_state({"configurable": {"thread_id": preview["approval_id"]}})
        self.assertFalse(state.values)
        self.assertEqual((await self.api.get("/api/cases")).json(), [])

    async def test_rule_thresholds_and_duplicate_listing_seats(self):
        base = (await self.api.get("/api/cases/case-post-017")).json()
        record = {"post": base["post"], "masked_body": base["masked_body"], "extraction": base["extraction"], "match": base["match"]}
        records = {"a": record, "duplicate": deepcopy(record)}
        cluster = {"post_ids": ["a", "duplicate"]}
        for score, expected in ((0.798, False), (0.800, True)):
            for booking in record["match"]["bookings"]:
                booking["bot"]["score"] = score
            record["extraction"]["fields"]["price_per_ticket_krw"] = 112000
            risk = assess_risk(record, {"a": record}, {"post_ids": ["a"]}, {e["id"]: e for e in SEED["events"]})
            self.assertEqual("R4" in risk["rule_hits"], expected)
            self.assertNotIn("R1", risk["rule_hits"])
        record["extraction"]["fields"]["price_per_ticket_krw"] = 137000
        risk = assess_risk(record, records, cluster, {e["id"]: e for e in SEED["events"]})
        self.assertEqual(risk["above_cost_seat_count"], 2)

    async def test_missing_gemini_key_does_not_fall_back_to_paid_provider(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "OPENAI_API_KEY": "irrelevant"}):
            self.assertEqual((await self.api.post("/api/agent/runs", json={"mode": "gemini"})).status_code, 409)
            self.assertEqual((await self.api.post("/api/eval", json={"mode": "gemini"})).status_code, 409)

    async def test_default_run_uses_zero_api_calls_even_with_openai_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "unused", "GEMINI_API_KEY": "offline-test"}), patch.object(Gemini, "call", AsyncMock(side_effect=AssertionError("unexpected API call"))):
            self.assertEqual((await self.api.get("/api/config")).json()["default_mode"], "local")
            run = await self.scan(None)
            extracted = next(s for s in run["steps"] if s["step"] == "extract")["output_summary"]
            self.assertEqual(extracted["provider"], "local")
            self.assertEqual(extracted["api_requests"], 0)

    async def test_download_preserves_approved_report_and_subsequent_offers(self):
        endpoint = "/api/cases/case-post-017/report"
        response = await self.api.get(endpoint)
        self.assertIn('filename="TicketGuard_AI_case-post-017_report.txt"', response.headers["Content-Disposition"])
        original = response.text
        self.assertEqual(original.splitlines()[0], "TicketGuard AI 신고서 초안")
        edited = original + "\n운영자 확인 메모"
        await self.action("draft_report", edited_text=edited)
        self.assertEqual((await self.api.get(endpoint)).text, edited)
        await self.action("request_explanation")
        await self.api.post("/api/cases/case-post-017/simulate", json={"type": "deadline_elapsed"})
        await self.action("cancel_redistribute")
        current = (await self.api.get(endpoint)).text
        self.assertTrue(current.startswith(edited))
        for value in ("승인 후 처리 경과", "deadline_elapsed", "fan-001", "fan-003"):
            self.assertIn(value, current)
        await self.action("draft_report", edited_text=current + "\n최종 확인")
        self.assertEqual((await self.api.get(endpoint)).text, current + "\n최종 확인")

    async def test_gemini_interruption_preserves_cases_and_resumes_extraction(self):
        from backend.app.agent.monitor import build_monitor
        ref, peer = (next(p for p in POSTS if p.post_id == key) for key in ("post-017", "post-030"))
        prepared = [prepare_listing(p, SEED["events"]) for p in (ref, peer)]
        responses = {item.model_input: extract_local(item)["fields"] for item in prepared}
        sent = []
        embeddings = 0

        def transport(request):
            nonlocal embeddings
            payload = json.loads(request.content)
            if request.url.path.endswith(":batchEmbedContents"):
                embeddings += 1
                if embeddings == 1:
                    return httpx.Response(429)
                return httpx.Response(200, json={"embeddings": [{"values": [1.0] * 768} for _ in payload["requests"]]})
            text = payload["contents"][0]["parts"][0]["text"]
            if text in responses:
                sent.append(text)
                if len(sent) == 2:
                    return httpx.Response(429)
                value = responses[text]
            else:
                value = {"lead": "확인된 근거를 바탕으로 운영자 검토가 필요합니다."}
            return httpx.Response(200, json={"modelVersion": "offline-fixture", "candidates": [
                {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(value, ensure_ascii=False)}]}}]})

        endpoint = "/api/cases/case-post-017"
        before = (await self.api.get(endpoint)).json()
        async with httpx.AsyncClient(base_url="https://example.invalid", transport=httpx.MockTransport(transport)) as client:
            def graph(db, port):
                return build_monitor(db, port, Gemini(db, client))
            with patch.dict("os.environ", {"GEMINI_API_KEY": "offline-test"}), patch(
                "backend.app.api.agent.build_monitor", graph
            ), patch("backend.app.agent.monitor.collect_posts", AsyncMock(return_value=CollectionResult("ok", (ref, peer), http_status=200))):
                for failed_step in ("extract", "cluster"):
                    run = await self.scan("gemini", "failed")
                    self.assertEqual(run["steps"][-1]["step"], failed_step)
                    self.assertEqual(run["steps"][-1]["output_summary"]["error"], "gemini_http_429")
                    self.assertEqual((await self.api.get(endpoint)).json(), before)
                third = await self.scan("gemini")
                self.assertEqual(third["steps"][2]["output_summary"]["cached"], 2)
                self.assertEqual([sent.count(item.model_input) for item in prepared], [1, 2])
                self.assertEqual((await self.api.get(endpoint)).json()["extraction"]["provider"], "gemini")

    async def test_zero_ticket_post_remains_in_review_without_stopping_the_scan(self):
        reference = next(post for post in POSTS if post.post_id == "post-017")
        draft = reference.model_dump(exclude={"created_at", "post_id"})
        draft["body"] = "A-01-01 0장 장당 십오만 원"
        added = await self.api.post("/api/market/posts", json=draft)
        self.assertEqual(added.status_code, 201)
        entry = MarketPost.model_validate(added.json())
        batch = CollectionResult("ok", (*POSTS, entry), http_status=200)
        with patch("backend.app.agent.monitor.collect_posts", AsyncMock(return_value=batch)):
            await self.scan()
        cases = (await self.api.get("/api/cases")).json()
        self.assertEqual(len(cases), 81)
        case = (await self.api.get(f"/api/cases/case-{entry.post_id}")).json()
        self.assertEqual(case["risk"]["risk_level"], "확인 불가")
        self.assertEqual(case["risk"]["rule_hits"], [])
        self.assertEqual(case["match"]["failure_reason"], "missing_quantity")
        self.assertIsNone(case["extraction"]["fields"]["quantity"])
        self.assertEqual(case["extraction"]["fields"]["evidence"]["quantity"], [])
        self.assertEqual(case["extraction"]["fields"]["price_per_ticket_krw"], 150000)

    async def test_distinct_masked_handles_do_not_merge_unrelated_sellers(self):
        records = []
        for key, handle, body in (("post-017", "fan-a@example.invalid", "직거래"),
                                  ("post-030", "fan-b@example.invalid", "현장 전달"),
                                  ("post-042", "fan-a@example.invalid", "현장")):
            record = next(p for p in POSTS if p.post_id == key)
            records.append(record.model_copy(update={"author_handle": handle, "body": body}))
        collection = CollectionResult("ok", tuple(records), http_status=200)
        with patch("backend.app.agent.monitor.collect_posts", AsyncMock(return_value=collection)):
            await self.scan()
        case = (await self.api.get("/api/cases/case-post-017")).json()
        self.assertEqual(set(case["cluster"]["post_ids"]), {"post-017", "post-042"})
        self.assertNotIn("@example.invalid", json.dumps(case))

    async def test_gemini_cache_and_reset_use_masked_inputs(self):
        reference = next(p for p in POSTS if p.post_id == "post-017").model_copy(update={
            "body": next(p for p in POSTS if p.post_id == "post-017").body + " 이름: 가상인 / 연락처: 010-0000-0000",
        })
        prepared = prepare_listing(reference, SEED["events"])
        expected = extract_local(prepared)["fields"]
        calls = []

        async def structured(instructions, text, schema):
            if "lead" in schema["properties"]:
                return json.dumps({"lead": "확인된 근거를 바탕으로 운영자 검토가 필요합니다."}), {"modelVersion": "mock"}
            calls.append(text)
            self.assertNotIn("010-0000-0000", text)
            self.assertNotIn("가상인", text)
            return json.dumps(expected, ensure_ascii=False), {"modelVersion": "mock"}

        collection = AsyncMock(return_value=CollectionResult("ok", (reference,), http_status=200))
        with patch.dict("os.environ", {"GEMINI_API_KEY": "mock"}), patch("backend.app.agent.monitor.collect_posts", collection), patch.object(Gemini, "structured", side_effect=structured), patch.object(Gemini, "embed", AsyncMock(return_value={})):
            first = await self.scan("gemini")
            second = await self.scan("gemini")
            self.assertEqual(len(calls), 1)
            summary = next(s for s in second["steps"] if s["step"] == "extract")["output_summary"]
            self.assertEqual(summary["cached"], 1)
            self.assertEqual(first["steps"][2]["output_summary"]["ready"], 1)
            await self.api.post("/api/demo/reset")
            await self.scan("gemini")
            self.assertEqual(len(calls), 2)

    async def test_partial_cancel_failure_rolls_back_all_seats_and_waiters(self):
        await self.action("request_explanation")
        await self.api.post("/api/cases/case-post-017/simulate", json={"type": "deadline_elapsed"})
        with self.app.state.db.connect() as connection:
            connection.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = 'booking-0002'")
        response = await self.action("cancel_redistribute")
        self.assertEqual(response.status_code, 409)
        with self.app.state.db.connect() as connection:
            self.assertEqual(connection.execute("SELECT status FROM bookings WHERE booking_id='booking-0001'").fetchone()[0], "confirmed")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist WHERE status='offered'").fetchone()[0], 0)

    async def test_pending_approval_survives_app_restart(self):
        preview = (await self.api.post("/api/cases/case-post-017/approvals", json={"type": "request_explanation"})).json()
        restarted = create_app(self.app.state.db.path)
        async with restarted.router.lifespan_context(restarted):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted), base_url="http://restarted") as client:
                result = await client.post("/api/cases/case-post-017/actions", json={
                    "type": "request_explanation", "approval_id": preview["approval_id"], "approved": True,
                })
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["case"]["status"], "소명 대기")


class GeminiTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_provider_envelopes_have_safe_failure_codes(self):
        ai = Gemini(None)
        post = next(p for p in POSTS if p.post_id == "post-017")
        for data in ({"candidates": [None]}, {"candidates": [{"finishReason": "STOP", "content": {"parts": [None]}}]}):
            with patch.object(ai, "call", AsyncMock(return_value=data)) as call:
                result = await ai.extract(prepare_listing(post, SEED["events"]))
                self.assertEqual(result["reason"], "gemini_invalid_response")
                self.assertFalse(result["schema_valid"])
                self.assertEqual(call.await_count, 2)
        with patch.object(ai, "call", AsyncMock(return_value={"embeddings": [None]})):
            with self.assertRaisesRegex(AIUnavailable, "gemini_invalid_embeddings"):
                await ai.embed({"post-017": "가상 게시글"})

    def test_title_only_seats_quantity_and_price_are_extracted_with_evidence(self):
        ref = next(p for p in POSTS if p.post_id == "post-017")
        post = ref.model_copy(update={"title": "2026 한빛 겨울 콘서트 A-01-01 1장 장당 123,456원",
                                      "body": "현장에서 직접 전달합니다.", "price": None})
        result = extract_local(prepare_listing(post, SEED["events"]))
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["fields"]["price_per_ticket_krw"], 123456)
        self.assertEqual(result["fields"]["seats"], ["A-01-01"])
        self.assertEqual(result["fields"]["quantity"], 1)
        for quotes in result["fields"]["evidence"].values():
            self.assertTrue(quotes)
            self.assertTrue(all(quote in post.title for quote in quotes))

    def test_korean_prices_totals_and_separate_charges(self):
        ref = next(p for p in POSTS if p.post_id == "post-017")
        for text, expected in (
            ("1장 장당 십오만 원", 150000), ("1장 양도가 이십삼만원", 230000),
            ("1장 양도가 12.5만 원", 125000), ("1장 장당 11만 원, 추가금 장당 2만 원", 130000),
            ("1장 장당 11만 원에 오만 추가", 160000), ("2장 합계 200,000원", 100000),
            ("2장 합계 200,001원", None), ("합계 200,000원", None), ("1장 추가금 5만원", None),
        ):
            with self.subTest(text=text):
                post = ref.model_copy(update={"title": SEED["events"][0]["name"], "body": "A-01-01 " + text})
                result = extract_local(prepare_listing(post, SEED["events"]))
                fields = result["fields"]
                self.assertEqual(fields["price_per_ticket_krw"], expected)
                self.assertEqual(bool(fields["evidence"]["price_per_ticket_krw"]), expected is not None)
                if expected is None:
                    self.assertEqual(result["status"], "review")

    async def test_all_ten_masking_cases_at_gemini_http_boundary(self):
        from backend.app.agent.extraction import LLM_FIELDS
        from backend.app.db import Database

        with tempfile.TemporaryDirectory() as temporary:
            db = Database(Path(temporary) / "x.sqlite3", ROOT / "data/seed.json")
            db.initialize()
            sent = []
            blank = {**{key: None for key in LLM_FIELDS}, "confidence": {key: 0.0 for key in LLM_FIELDS},
                     "evidence": {"seats": [], "quantity": [], "price_per_ticket_krw": []}}

            def handler(request):
                sent.append(json.loads(request.content))
                return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(blank)}]}}]})

            async with httpx.AsyncClient(base_url="https://generativelanguage.googleapis.com", transport=httpx.MockTransport(handler)) as client:
                ai = Gemini(db, client)
                for case in GOLD["masking_cases"]:
                    post = next(p for p in POSTS if p.post_id == case["post_id"])
                    await ai.extract(prepare_listing(post, SEED["events"]), skip_unpriced=False)
            self.assertEqual(len(sent), 10)
            for case, payload in zip(GOLD["masking_cases"], sent, strict=True):
                for value in case["synthetic_values"].values():
                    self.assertNotIn(value, json.dumps(payload, ensure_ascii=False))

    async def test_evaluation_resumes_successful_extractions_after_quota_error(self):
        from backend.app.agent.gemini import AIUnavailable, fingerprint
        from backend.app.db import Database
        from backend.app.evaluation.full import evaluate

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data/evaluation").mkdir(parents=True)
            (root / "data/seed.json").write_text(json.dumps(SEED))
            (root / "data/evaluation/evaluation_set.json").write_text(json.dumps(GOLD))
            db = Database(root / "usage.sqlite3", root / "data/seed.json")
            db.initialize()
            calls = []

            async def extract(listing, **kwargs):
                calls.append(listing.model_input)
                if len(calls) == 4:
                    return {"fields": None, "schema_valid": False, "status": "review", "reason": "gemini_http_429"}
                return {**extract_local(listing), "provider": "gemini", "source": "api",
                        "fingerprint": fingerprint(listing), "model_returned": "mock-gemini"}

            async def embed(texts):
                return {key: [1.0, 0.0] for key in texts}

            with patch("backend.app.evaluation.full.ROOT", root), patch.object(Gemini, "extract", side_effect=extract), patch.object(Gemini, "embed", side_effect=embed):
                with self.assertRaises(AIUnavailable):
                    await evaluate("gemini", db)
                progress = json.loads((root / "data/evaluation/gemini_progress.json").read_text())
                self.assertEqual(len(progress["extractions"]), 3)
                report = await evaluate("gemini", db)
                self.assertEqual(report["summary"]["resumed_extractions"], 3)
                self.assertEqual(len(calls), 86)
                self.assertTrue(all(report["summary"]["checks"].values()))

    async def test_masked_schema_retry_and_quota_stop(self):
        from backend.app.db import Database
        with tempfile.TemporaryDirectory() as temporary:
            db = Database(Path(temporary) / "x.sqlite3", ROOT / "data/seed.json")
            db.initialize()
            requests = []

            def handler(request):
                payload = json.loads(request.content)
                requests.append(payload)
                for case in GOLD["masking_cases"]:
                    for value in case["synthetic_values"].values():
                        self.assertNotIn(value, json.dumps(payload, ensure_ascii=False))
                self.assertIn("responseJsonSchema", payload["generationConfig"])
                return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]})

            async with httpx.AsyncClient(base_url="https://generativelanguage.googleapis.com", transport=httpx.MockTransport(handler)) as client:
                ai = Gemini(db, client)
                post = next(p for p in POSTS if p.post_id == "post-001")
                result = await ai.extract(prepare_listing(post, SEED["events"]))
                self.assertEqual(result["attempts"], 2)
                self.assertEqual(result["status"], "review")
                self.assertEqual(len(requests), 2)
                with patch.dict("os.environ", {"TRUETICKET_DAILY_REQUEST_LIMIT": "2"}):
                    blocked = await ai.extract(prepare_listing(post, SEED["events"]))
                    self.assertEqual(blocked["reason"], "daily_request_limit")
                    self.assertEqual(len(requests), 2)

    def test_local_baseline_handles_arbitrary_price_and_missing_fields(self):
        reference = next(p for p in POSTS if p.post_id == "post-017")
        post = reference.model_copy(update={"body": "2026 한빛 겨울 콘서트 1회차. A구역 1열 1번 1장, 장당 123,456원. 직거래 가능해요."})
        result = extract_local(prepare_listing(post, SEED["events"]))
        self.assertEqual(result["fields"]["price_per_ticket_krw"], 123456)
        self.assertEqual(result["fields"]["seats"], ["A-01-01"])
        self.assertEqual(result["source"], "local_rules")
