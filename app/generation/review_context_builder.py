"""Assemble human-readable context blocks for review-generation prompts."""

import json
from typing import Any

import pandas as pd

from app.retrieval.registry import RetrievalRegistry
from app.retrieval.vector_store import VectorMatch
from app.types.behavior import BusinessBehaviorProfile, UserBehaviorProfile


def format_user_behavior_json(profile: UserBehaviorProfile) -> str:
    """Serialise a user behaviour profile for the prompt."""
    return json.dumps(profile.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)


def format_user_history_block(reviews: list[dict[str, Any]], max_snippet: int = 450) -> str:
    """Format recent review dicts into a bounded verbatim block."""
    if not reviews:
        return "(No review history in subset for this user.)"
    parts: list[str] = []
    for r in reviews:
        text = str(r.get("text") or "").strip().replace("\n", " ")
        if not text:
            continue
        if len(text) > max_snippet:
            text = text[: max_snippet - 3] + "..."
        parts.append(
            f"[stars={r.get('stars')} date={r.get('date')} biz={r.get('business_id')}] {text}"
        )
    return "\n\n".join(parts) if parts else "(No non-empty review texts.)"


def format_business_tabular_row(row: pd.Series | dict[str, Any]) -> str:
    """Turn a `businesses.parquet` row into a short bullet list."""
    if isinstance(row, pd.Series):
        d = row.to_dict()
    else:
        d = row
    lines = [
        f"business_id: {d.get('business_id')}",
        f"name: {d.get('name')}",
        f"city: {d.get('city')}, state: {d.get('state')}",
        f"categories: {d.get('categories')}",
        f"yelp_stars: {d.get('stars')}",
        f"yelp_review_count: {d.get('review_count')}",
        f"price_range: {d.get('price_range')}",
    ]
    return "\n".join(str(x) for x in lines if x is not None)


def format_business_behavior_block(profile: BusinessBehaviorProfile) -> str:
    """Summarise deterministic business behaviour + theme hits."""
    base = json.dumps(profile.stats, ensure_ascii=False, indent=2)
    lines = [base, "", "Praise themes (subset):"]
    for t in profile.praise_themes[:5]:
        snip = " | ".join(t.snippets[:2]) if t.snippets else "(no snippets)"
        lines.append(f"  - {t.label} (score={t.score:.2f}): {snip}")
    lines.extend(["", "Complaint themes (subset):"])
    for t in profile.complaint_themes[:5]:
        snip = " | ".join(t.snippets[:2]) if t.snippets else "(no snippets)"
        lines.append(f"  - {t.label} (score={t.score:.2f}): {snip}")
    return "\n".join(lines)


def format_similar_businesses_block(
    registry: RetrievalRegistry,
    matches: list[VectorMatch],
    max_rows: int = 5,
) -> str:
    """Hydrate neighbour business rows for the prompt."""
    if not matches:
        return "(No similar businesses retrieved.)"
    df = registry.businesses_df
    lines: list[str] = []
    for m in matches[:max_rows]:
        bid = m.id
        hit = df[df["business_id"] == bid]
        if hit.empty:
            lines.append(f"- {bid} (score={m.score:.3f}) {m.metadata}")
            continue
        row = hit.iloc[0]
        lines.append(
            f"- {row.get('name')} ({row.get('city')}) score={m.score:.3f} | "
            f"{(str(row.get('categories') or ''))[:120]}"
        )
    return "\n".join(lines)


def format_similar_reviews_block(hydrated: list[dict[str, Any]], max_rows: int = 6) -> str:
    """Format retrieved review rows (already joined with scores)."""
    if not hydrated:
        return "(No similar reviews retrieved.)"
    lines: list[str] = []
    for r in hydrated[:max_rows]:
        text = str(r.get("text") or "").strip().replace("\n", " ")[:320]
        lines.append(
            f"- score={r.get('score', 0):.3f} stars={r.get('stars')} "
            f"biz={r.get('business_id')}: {text}"
        )
    return "\n".join(lines)


def build_review_search_query(business_row: dict[str, Any]) -> str:
    """Build a short query string for semantic review search."""
    name = str(business_row.get("name") or "")
    cats = str(business_row.get("categories") or "")
    city = str(business_row.get("city") or "")
    return f"{name} {cats} {city} restaurant food service experience".strip()
