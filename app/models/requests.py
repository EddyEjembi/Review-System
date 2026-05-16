"""Request models used by the API layer."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import REVIEW_PROMPT_MAX_CHARS_DEFAULT

NEW_DEMO_USER_EXAMPLE: dict[str, Any] = {
    "archetype": "ibadan_family_diner",
    "demographics": {
        "city": "Ibadan",
        "country": "Nigeria",
        "age_band": "40-50",
        "language": "Nigerian English, occasional Yoruba phrases",
    },
    "preferences": {
        "budget": "mid",
        "cuisines": ["Amala", "Ewedu", "Buka-style", "Family restaurants"],
        "tone": "warm and descriptive",
        "review_style": "medium-length, focuses on portion sizes and family suitability",
    },
    "service_expectations": {
        "wait_time_tolerance": "high",
        "price_sensitivity": "medium",
        "portion_size_importance": "very high",
    },
    "notes": "Will praise generous portions and family-friendly seating.",
}

NEW_DEMO_USER_NESTED_HINTS: dict[str, dict[str, str]] = {
    "demographics": {
        "city": "Home city or region for cultural context in reviews.",
        "country": "Country name.",
        "age_band": "e.g. 25-34, 40-50.",
        "language": "Primary language or dialect notes for the persona LLM.",
    },
    "preferences": {
        "budget": "e.g. low, low-to-mid, mid, high.",
        "cuisines": "List of cuisine types or restaurant styles they seek.",
        "tone": "Overall voice when writing (casual, formal, warm, critical).",
        "review_style": "Length and focus habits for generated reviews.",
    },
    "service_expectations": {
        "wait_time_tolerance": "low | medium | high.",
        "price_sensitivity": "low | medium | high.",
        "portion_size_importance": "Optional; how much portion size matters in reviews.",
    },
}


class NewDemoUserPayload(BaseModel):
    """Cold-start user definition; persisted under `cold_start` in `test_users.json`."""

    model_config = ConfigDict(json_schema_extra={"examples": [NEW_DEMO_USER_EXAMPLE]})

    archetype: str = Field(..., min_length=1, max_length=160, description="Short id for the synthetic reviewer.")
    demographics: dict[str, Any] = Field(
        default_factory=dict,
        description="e.g. city, country, age_band, language — stored on the manifest row.",
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="e.g. budget, cuisines, tone, review_style.",
    )
    service_expectations: dict[str, Any] = Field(
        default_factory=dict,
        description="e.g. wait_time_tolerance, price_sensitivity.",
    )
    notes: str | None = Field(None, max_length=4000, description="Free-form designer notes for prompts.")


class MakeReviewRequest(BaseModel):
    """JSON body for `POST /reviews`: existing `user_id` **or** `new_user`, plus `business_id`."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "Hi10sGSZNxQH3NLyWSZ1oA",
                    "business_id": "Pns2l4eNsfO8kk83dixA6A",
                },
                {
                    "new_user": {
                        "archetype": "weekend_brunch_seeker",
                        "demographics": {"city": "Lagos", "country": "Nigeria", "age_band": "25-34"},
                        "preferences": {
                            "budget": "mid",
                            "cuisines": ["Brunch", "Cafe"],
                            "tone": "warm",
                            "review_style": "medium-length, practical",
                        },
                        "service_expectations": {"wait_time_tolerance": "medium"},
                        "notes": "Likes natural light and outdoor seating.",
                    },
                    "business_id": "Pns2l4eNsfO8kk83dixA6A",
                    "max_chars": 400,
                },
            ]
        }
    )

    business_id: str = Field(
        ...,
        min_length=1,
        description="Must exist in `businesses.parquet` and `business_behavior.jsonl` for this demo.",
    )
    user_id: str | None = Field(
        default=None,
        description="Registered demo user id from `GET /users`. Omit when sending `new_user`.",
    )
    new_user: NewDemoUserPayload | None = Field(
        default=None,
        description="When set, a new cold-start user is created and appended before review generation.",
    )
    max_chars: int | None = Field(
        default=None,
        ge=50,
        le=4000,
        description="Soft upper bound (characters) for the review text; omit to use the server default.",
    )

    @model_validator(mode="after")
    def exactly_one_user_source(self) -> Self:
        """Require either `user_id` or `new_user`, never both, never neither."""
        uid = (self.user_id or "").strip()
        has_uid = bool(uid)
        has_new = self.new_user is not None
        if has_uid and has_new:
            raise ValueError("Provide only one of `user_id` or `new_user`, not both.")
        if not has_uid and not has_new:
            raise ValueError("Provide either `user_id` (existing demo user) or `new_user` (create then review).")
        if has_uid:
            object.__setattr__(self, "user_id", uid)
        return self

    def resolved_max_chars(self) -> int:
        """Return `max_chars` from the body or the configured default when omitted."""
        if self.max_chars is not None:
            return int(self.max_chars)
        return REVIEW_PROMPT_MAX_CHARS_DEFAULT
