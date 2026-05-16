"""Project-wide constants.

Prefer adding values here when they are referenced from multiple modules.
Single-use literals should stay close to their usage site.
"""

from typing import Final

DEFAULT_TOP_K: Final[int] = 5
MIN_REVIEW_LENGTH: Final[int] = 20
MAX_REVIEW_LENGTH: Final[int] = 1024

USER_NAMESPACE: Final[str] = "users"
BUSINESS_NAMESPACE: Final[str] = "businesses"
REVIEW_NAMESPACE: Final[str] = "reviews"

SENTIMENT_LABELS: Final[tuple[str, ...]] = ("negative", "neutral", "positive")
STAR_RATINGS: Final[tuple[int, ...]] = (1, 2, 3, 4, 5)

# Review generation (fixed sampling; not exposed on the public review API.)
REVIEW_COMPLETION_TEMPERATURE: Final[float] = 0.68
# Soft cap hinted to the model for generated review length (API default when body omits `max_chars`).
REVIEW_PROMPT_MAX_CHARS_DEFAULT: Final[int] = 480

# `GET /businesses` pagination (Parquet holds thousands of rows).
BUSINESS_LIST_DEFAULT_LIMIT: Final[int] = 50
BUSINESS_LIST_MAX_LIMIT: Final[int] = 200
