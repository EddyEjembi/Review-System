"""Response models used by the API layer."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import ReviewGenerationResult


class NewUserUsageHint(BaseModel):
    """How to submit a newly defined user when generating a review."""

    endpoint: str = Field(..., description="HTTP method and path.")
    method: str
    body_field: str = Field(..., description="Place the user object under this key in the JSON body.")
    also_required: list[str] = Field(
        default_factory=list,
        description="Other top-level fields required on the same request.",
    )
    mutually_exclusive_with: list[str] = Field(
        default_factory=list,
        description="Do not send these fields together with `new_user`.",
    )
    auth: str = Field(..., description="Authorization header requirement.")


class NewUserSchemaResponse(BaseModel):
    """JSON Schema and examples for `new_user` on `POST /reviews`."""

    description: str
    json_schema: dict[str, Any] = Field(..., description="JSON Schema (draft 2020-12) for the `new_user` object.")
    required: list[str]
    example: dict[str, Any]
    nested_field_hints: dict[str, dict[str, str]] = Field(
        ...,
        description="Common keys inside optional object fields (not enforced by validation).",
    )
    usage: NewUserUsageHint


class GenerateReviewResponse(BaseModel):
    """Successful response for `POST /reviews/generate`.

    Echoes the requested identifiers and returns the structured generation payload under `result`.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "Hi10sGSZNxQH3NLyWSZ1oA",
                    "business_id": "Pns2l4eNsfO8kk83dixA6A",
                    "result": {
                        "rating": 4,
                        "review": "Food was very nice and affordable honestly.",
                        "reasoning": {
                            "positive_factors": ["good portions", "affordable pricing"],
                            "negative_factors": ["slow service"],
                        },
                        "metadata": {
                            "user_id": "Hi10sGSZNxQH3NLyWSZ1oA",
                            "business_id": "Pns2l4eNsfO8kk83dixA6A",
                        },
                    },
                }
            ]
        }
    )

    user_id: str = Field(..., description="Same `user_id` as in the request (registered test user).")
    business_id: str = Field(..., description="Same `business_id` as in the request.")
    result: ReviewGenerationResult = Field(
        ...,
        description="Predicted rating, review text, reasoning factors, and optional metadata.",
    )
