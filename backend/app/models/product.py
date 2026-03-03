"""Pydantic models for products and scoring."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class PriceInfo(BaseModel):
    current: float
    original: Optional[float] = None
    currency: str = "INR"
    discount_percent: Optional[float] = None


class SentimentData(BaseModel):
    """Aggregated sentiment from multiple sources."""
    overall_score: float = Field(default=0.5, ge=0.0, le=1.0)
    reddit_score: Optional[float] = None
    youtube_score: Optional[float] = None
    marketplace_score: Optional[float] = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    hidden_issues: list[str] = Field(default_factory=list)
    sample_size: int = 0
    summary: str = ""


class Product(BaseModel):
    """A product with all scraped and computed data."""
    id: str = ""
    title: str
    brand: str = ""
    model: str = ""
    price: PriceInfo
    specifications: dict[str, str] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    url: str = ""
    source: str = ""  # amazon, flipkart, etc.
    availability: str = "unknown"  # in_stock, out_of_stock, pre_order
    rating: Optional[float] = None
    review_count: Optional[int] = None
    sentiment: SentimentData = Field(default_factory=SentimentData)


class ProductScore(BaseModel):
    """Scored product with breakdown."""
    product: Product
    total_score: float = 0.0
    technical_match: float = 0.0
    sentiment_score: float = 0.0
    value_for_money: float = 0.0
    availability_score: float = 0.0
    explanation: str = ""  # "Why this product?" text
