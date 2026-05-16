"""Tests for the generation layer."""

import json

import pytest

from app.generation.review_output_parser import parse_review_generation_result


def test_parse_review_generation_result_accepts_valid_json() -> None:
    raw = json.dumps(
        {
            "rating": 4,
            "review": "Solid spot; would come back for the wings alone.",
            "reasoning": {
                "positive_factors": ["good food"],
                "negative_factors": ["noisy room"],
            },
        }
    )
    out = parse_review_generation_result(raw)
    assert out.rating == 4
    assert "wings" in out.review
    assert "good food" in out.reasoning.positive_factors


def test_parse_review_generation_result_coerces_float_rating() -> None:
    raw = json.dumps(
        {
            "rating": 3.0,
            "review": "It was fine, nothing special but okay for lunch.",
            "reasoning": {"positive_factors": [], "negative_factors": []},
        }
    )
    out = parse_review_generation_result(raw)
    assert out.rating == 3


def test_parse_review_generation_result_rejects_short_review() -> None:
    raw = json.dumps(
        {
            "rating": 5,
            "review": "Great!",
            "reasoning": {"positive_factors": [], "negative_factors": []},
        }
    )
    with pytest.raises(ValueError):
        parse_review_generation_result(raw)
