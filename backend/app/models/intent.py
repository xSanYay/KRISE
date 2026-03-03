"""Pydantic models for intent profiles and user preferences."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class TechnicalRequirement(BaseModel):
    """A single technical spec requirement extracted from user intent."""
    name: str
    min_value: Optional[str] = None
    preferred_value: Optional[str] = None
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    required: bool = False


class Constraint(BaseModel):
    """Budget, brand, or other constraints."""
    budget_max: Optional[float] = None
    budget_currency: str = "INR"
    budget_flexible: bool = True
    brand_preferences: list[str] = Field(default_factory=list)
    brand_aversions: list[str] = Field(default_factory=list)
    max_weight_kg: Optional[float] = None


class IntentProfile(BaseModel):
    """Complete user intent profile built through conversation."""
    primary_use_case: str = ""
    secondary_use_cases: list[str] = Field(default_factory=list)
    product_category: str = ""  # phone, laptop, tablet, etc.
    technical_requirements: list[TechnicalRequirement] = Field(default_factory=list)
    constraints: Constraint = Field(default_factory=Constraint)
    deal_breakers: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    conviction_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # Dynamic weights adjusted by swipe feedback
    scoring_weights: dict[str, float] = Field(default_factory=lambda: {
        "technical_match": 0.40,
        "sentiment": 0.30,
        "value_for_money": 0.20,
        "availability": 0.10,
    })

    # Brand scores adjusted by swipe feedback
    brand_scores: dict[str, float] = Field(default_factory=dict)
