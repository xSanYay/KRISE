"""API request/response schemas."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

from app.models.intent import IntentProfile
from app.models.product import ProductScore


# ── Requests ──────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    language: str = "en"


class SendMessageRequest(BaseModel):
    content: str
    type: str = "text"  # text or voice


class SwipeRequest(BaseModel):
    product_id: str
    direction: str  # left, right, up, down
    reason: Optional[str] = None


# ── Responses ─────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    status: str = "active"
    phase: str


class WidgetRequest(BaseModel):
    """Request for the frontend to render an interactive widget."""
    widget_type: str  # budget_slider, category_picker, brand_picker
    label: str = ""
    options: list[str] = Field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None


class MessageResponse(BaseModel):
    type: str  # question, recommendations, info, error
    content: str = ""
    intent_profile: Optional[IntentProfile] = None
    products: list[ProductScore] = Field(default_factory=list)
    conviction_score: float = 0.0
    widget: Optional[WidgetRequest] = None


class SwipeResponse(BaseModel):
    next_product: Optional[ProductScore] = None
    remaining_count: int = 0
    updated_weights: dict[str, float] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
