"""Pydantic models for session management."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime

from app.models.intent import IntentProfile
from app.models.product import ProductScore


class SessionPhase(str, Enum):
    INTENT_MAPPING = "intent_mapping"
    SOCRATIC_FRICTION = "socratic_friction"
    FETCHING_PRODUCTS = "fetching_products"
    PRODUCT_RECOMMENDATION = "product_recommendation"


class SessionMode(str, Enum):
    STANDARD = "standard"
    SOCRATIC_DECISION = "socratic_decision"


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class SwipeAction(BaseModel):
    product_id: str
    direction: str  # left, right, up, down
    reason: Optional[str] = None  # too_expensive, wrong_brand, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DecisionOutcome(BaseModel):
    verdict: str = ""
    rationale: str = ""
    recommendation: str = ""
    non_consumer_alternative: str = ""
    key_tradeoffs: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """User session tracking the entire conversation journey."""
    id: str
    language: str = "en"
    mode: SessionMode = SessionMode.STANDARD
    phase: SessionPhase = SessionPhase.INTENT_MAPPING
    intent_profile: IntentProfile = Field(default_factory=IntentProfile)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    swipe_history: list[SwipeAction] = Field(default_factory=list)
    product_deck: list[ProductScore] = Field(default_factory=list)
    shortlist: list[str] = Field(default_factory=list)  # product IDs
    socratic_turn_count: int = 0
    asked_pre_search_clarification: bool = False
    initial_statement: str = ""
    decision_turn_count: int = 0
    decision_stage: str = "opening"
    decision_complete: bool = False
    decision_outcome: Optional[DecisionOutcome] = None
    progress_steps: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
