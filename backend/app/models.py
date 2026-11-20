from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NewMarketPost(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(min_length=1, max_length=64)
    channel: Literal["가상 중고거래", "가상 SNS"]
    author_handle: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=3000)
    price: int | None = Field(default=None, ge=0, le=100_000_000)


class MarketPost(NewMarketPost):
    post_id: str
    created_at: str


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str | None = Field(default=None, min_length=1, max_length=64)
    mode: Literal["local", "gemini"] | None = None


ActionType = Literal["request_explanation", "close_normal", "cancel_redistribute", "draft_report"]


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    type: ActionType


class ActionRequest(ApprovalRequest):
    approved: bool = Field(default=False, strict=True)
    approval_id: str | None = Field(default=None, max_length=80)
    edited_text: str | None = Field(default=None, max_length=16000)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    type: Literal["deadline_elapsed", "explanation_received"]
    text: str | None = Field(default=None, max_length=3000)
