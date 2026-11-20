"""Gemini REST adapter. Only masked synthetic text crosses this boundary."""

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from time import monotonic

import httpx

from .extraction import BASE_PROMPT, LISTING_SCHEMA, MIN_CONFIDENCE, MONEY_TEXT, UNSET_PRICE, PreparedListing, _parse_output


MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"


class AIUnavailable(Exception):
    """A safe, payload-free error code for API/configuration failures."""


def service_interrupted(reason: str | None) -> bool:
    return bool(reason and (reason.startswith("gemini_http_") or reason in {
        "daily_request_limit", "gemini_api_key_required", "gemini_connection_error",
    }))


def api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def fingerprint(listing: PreparedListing) -> str:
    contract = json.dumps([MODEL, BASE_PROMPT, LISTING_SCHEMA], sort_keys=True, ensure_ascii=False)
    return sha256((contract + listing.model_input).encode()).hexdigest()


class Gemini:
    def __init__(self, db, client: httpx.AsyncClient | None = None):
        self.db = db
        self.client = client
        self.last_request = 0.0
        self.requests = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.returned_models: set[str] = set()

    async def call(self, model: str, method: str, payload: dict) -> dict:
        if not api_key() and self.client is None:
            raise AIUnavailable("gemini_api_key_required")
        interval = max(0.0, float(os.getenv("TRUETICKET_REQUEST_INTERVAL", "12")))
        if self.client is None:
            await asyncio.sleep(max(0.0, interval - (monotonic() - self.last_request)))
        day = datetime.now(timezone.utc).date().isoformat()
        self.db.reserve_api_request(day)
        self.last_request = monotonic()
        self.requests += 1
        try:
            if self.client is not None:
                response = await self.client.post(f"/v1beta/models/{model}:{method}", json=payload)
            else:
                async with httpx.AsyncClient(
                    base_url="https://generativelanguage.googleapis.com",
                    headers={"x-goog-api-key": api_key()},
                    timeout=httpx.Timeout(60, connect=8), follow_redirects=False,
                ) as client:
                    response = await client.post(f"/v1beta/models/{model}:{method}", json=payload)
        except httpx.RequestError:
            raise AIUnavailable("gemini_connection_error") from None
        if not response.is_success:
            raise AIUnavailable(f"gemini_http_{response.status_code}")
        try:
            data = response.json()
            usage = data.get("usageMetadata", {})
            self.input_tokens += int(usage.get("promptTokenCount", 0))
            self.output_tokens += int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0))
            if data.get("modelVersion"):
                self.returned_models.add(data["modelVersion"])
            return data
        except (ValueError, TypeError, AttributeError):
            raise AIUnavailable("gemini_invalid_response") from None

    async def structured(self, instructions: str, text: str, schema: dict) -> tuple[str, dict]:
        data = await self.call(MODEL, "generateContent", {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "responseMimeType": "application/json", "responseJsonSchema": schema,
                "maxOutputTokens": 2400,
            },
        })
        candidates = data.get("candidates", [])
        if not isinstance(candidates, list) or (candidates and not isinstance(candidates[0], dict)):
            raise AIUnavailable("gemini_invalid_response")
        if not candidates or candidates[0].get("finishReason") != "STOP":
            raise AIUnavailable("gemini_incomplete_response")
        content = candidates[0].get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list) or any(
            not isinstance(part, dict) or not isinstance(part.get("text", ""), str) for part in parts
        ):
            raise AIUnavailable("gemini_invalid_response")
        return "".join(p.get("text", "") for p in parts if not p.get("thought")), data

    async def extract(self, listing: PreparedListing, *, skip_unpriced: bool = True) -> dict:
        result = {
            "fields": None, "status": "review", "reason": None, "attempts": 0,
            "schema_valid": False, "source": "api", "provider": "gemini",
            "model_requested": MODEL, "model_returned": None,
            "fingerprint": fingerprint(listing), "slang": listing.slang,
            "input_tokens": 0, "output_tokens": 0,
        }
        text = listing.title + "\n" + listing.body
        if skip_unpriced and UNSET_PRICE.search(text) and not MONEY_TEXT.search(text):
            return {**result, "reason": "price_unspecified", "source": "prefilter"}
        before_input, before_output = self.input_tokens, self.output_tokens
        for attempt in range(2):
            result["attempts"] += 1
            try:
                instructions = BASE_PROMPT + ("\n원문 근거와 JSON 형식을 다시 확인한다." if attempt else "")
                text, data = await self.structured(instructions, listing.model_input, LISTING_SCHEMA)
                fields, error = _parse_output({
                    "status": "completed", "output": [{"type": "message", "content": [
                        {"type": "output_text", "text": text},
                    ]}],
                }, listing)
                result["reason"] = error
                result["model_returned"] = data.get("modelVersion")
                if fields is None:
                    continue
                result["fields"] = fields.model_dump()
                result["schema_valid"] = True
                if fields.price_per_ticket_krw is None or not fields.seats:
                    result["reason"] = "missing_price_or_seats"
                elif min(fields.confidence.price_per_ticket_krw, fields.confidence.seats) < MIN_CONFIDENCE:
                    result["reason"] = "low_confidence"
                else:
                    result["status"] = "extracted"
                break
            except AIUnavailable as error:
                result["reason"] = str(error)
                if str(error) in {"gemini_invalid_response", "gemini_incomplete_response"}:
                    continue
                break
        result["input_tokens"] = self.input_tokens - before_input
        result["output_tokens"] = self.output_tokens - before_output
        return result

    async def embed(self, texts: dict[str, str]) -> dict[str, list[float]]:
        if not texts:
            return {}
        data = await self.call(EMBEDDING_MODEL, "batchEmbedContents", {"requests": [
            {"model": f"models/{EMBEDDING_MODEL}", "content": {"parts": [{"text": text}]},
             "taskType": "CLUSTERING", "outputDimensionality": 768}
            for text in texts.values()
        ]})
        items = data.get("embeddings")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise AIUnavailable("gemini_invalid_embeddings")
        vectors = [item.get("values") for item in items]
        if len(vectors) != len(texts) or any(
            not isinstance(vector, list) or len(vector) != 768 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in vector)
            for vector in vectors
        ):
            raise AIUnavailable("gemini_invalid_embeddings")
        return dict(zip(texts, vectors, strict=True))
