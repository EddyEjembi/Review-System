"""Core domain schemas shared across modules."""

from typing import Any

from pydantic import BaseModel, Field


class Persona(BaseModel):
    """Distilled representation of a Yelp reviewer."""

    user_id: str
    voice: str = Field(..., description="Short prose describing tone and style.")
    preferences: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)
    typical_length: int = Field(0, ge=0, description="Average review length in characters.")
    vocabulary_quirks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewReasoning(BaseModel):
    """Transparent factors supporting the predicted rating (PRD-style)."""

    positive_factors: list[str] = Field(
        default_factory=list,
        description="Short phrases explaining what supported a higher rating.",
    )
    negative_factors: list[str] = Field(
        default_factory=list,
        description="Short phrases explaining what pulled the rating down.",
    )


class ReviewGenerationResult(BaseModel):
    """Structured output: predicted rating, review text, and reasoning metadata."""

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Model-predicted star rating (1–5), consistent with the review text.",
    )
    review: str = Field(..., description="Single natural-language review in the user's persona.")
    reasoning: ReviewReasoning = Field(
        ...,
        description="Structured explanation of the rating (not necessarily shown in a consumer UI).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Echo fields such as `user_id`, `business_id`, and `max_chars`.",
    )


class BusinessContext(BaseModel):
    """Compact, prompt-ready description of a business."""

    business_id: str
    name: str
    categories: list[str] = Field(default_factory=list)
    avg_stars: float | None = None
    review_count: int = 0
    representative_reviews: list[str] = Field(default_factory=list)


