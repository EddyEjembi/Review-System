"""Parse structured JSON review output from the LLM."""

import json
from typing import Any

from app.core.constants import MAX_REVIEW_LENGTH, MIN_REVIEW_LENGTH
from app.models.schemas import ReviewGenerationResult, ReviewReasoning
from app.utils.json_utils import coerce_json_text, try_parse_json


def _load_first_json_object(raw: str) -> dict[str, Any]:
    """Parse the first JSON object from model text (tolerates leading/trailing noise)."""
    stripped = (raw or "").strip()
    if not stripped:
        raise ValueError("Empty model output")
    coerced = coerce_json_text(stripped)
    parsed = try_parse_json(coerced)
    if isinstance(parsed, dict):
        return parsed
    idx = stripped.find("{")
    if idx < 0:
        raise ValueError("Expected a JSON object from the model")
    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(stripped, idx)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from model: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("Expected a JSON object from the model")
    return obj


def parse_review_generation_result(raw: str) -> ReviewGenerationResult:
    """Parse and validate LLM JSON into `ReviewGenerationResult`."""
    data = _load_first_json_object(raw)

    raw_rating = data.get("rating")
    if raw_rating is None and isinstance(data.get("stars"), (int, float, str)):
        raw_rating = data.get("stars")
    if raw_rating is None:
        raise ValueError("Missing required field: rating")
    if isinstance(raw_rating, bool):
        raise ValueError(f"Invalid rating type: {raw_rating!r}")
    if isinstance(raw_rating, str) and raw_rating.strip().isdigit():
        raw_rating = int(raw_rating.strip())
    if isinstance(raw_rating, float):
        raw_rating = int(round(raw_rating))
    if not isinstance(raw_rating, int):
        raise ValueError(f"rating must be an integer 1-5, got {raw_rating!r}")
    rating = raw_rating
    if rating < 1 or rating > 5:
        raise ValueError(f"rating out of range: {rating}")

    review = str(data.get("review") or "").strip()
    if len(review) < MIN_REVIEW_LENGTH:
        raise ValueError(
            f"Review text too short ({len(review)} chars; minimum {MIN_REVIEW_LENGTH})"
        )
    if len(review) > MAX_REVIEW_LENGTH:
        review = review[:MAX_REVIEW_LENGTH].rstrip()

    raw_reason = data.get("reasoning") or {}
    if not isinstance(raw_reason, dict):
        raw_reason = {}
    pos = raw_reason.get("positive_factors") or []
    neg = raw_reason.get("negative_factors") or []
    if not isinstance(pos, list):
        pos = []
    if not isinstance(neg, list):
        neg = []
    reasoning = ReviewReasoning(
        positive_factors=[str(x) for x in pos],
        negative_factors=[str(x) for x in neg],
    )

    meta: dict[str, Any] = dict(data.get("metadata") or {}) if isinstance(data.get("metadata"), dict) else {}
    meta.pop("model", None)

    return ReviewGenerationResult(
        rating=rating,
        review=review,
        reasoning=reasoning,
        metadata=meta,
    )
