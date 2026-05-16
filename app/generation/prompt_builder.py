"""Compose prompts for review generation (Phase 5)."""

import json

from app.models.schemas import Persona
from app.templates.review import REVIEW_JSON_SYSTEM_PROMPT, REVIEW_JSON_USER_TEMPLATE


def format_persona_block(persona: Persona) -> str:
    """Render a `Persona` as a stable block for downstream LLM prompts."""
    lines = [
        f"User id: {persona.user_id}",
        f"Voice & tone: {persona.voice}",
        f"Typical review length (chars): {persona.typical_length}",
    ]
    if persona.preferences:
        lines.append("Preferences: " + "; ".join(persona.preferences))
    if persona.dealbreakers:
        lines.append("Dealbreakers: " + "; ".join(persona.dealbreakers))
    if persona.vocabulary_quirks:
        lines.append("Vocabulary quirks: " + "; ".join(persona.vocabulary_quirks))
    if persona.metadata:
        lines.append("Extra metadata (JSON): " + json.dumps(persona.metadata, ensure_ascii=False))
    return "\n".join(lines)


def build_review_json_prompt(
    persona: Persona,
    user_behavior_json: str,
    user_history_block: str,
    business_tabular_block: str,
    business_behavior_block: str,
    similar_businesses_block: str,
    similar_reviews_block: str,
    max_chars: int = 800,
) -> tuple[str, str]:
    """Return `(system_prompt, user_prompt)` for JSON rating+review generation."""
    persona_block = format_persona_block(persona)
    user_prompt = REVIEW_JSON_USER_TEMPLATE.format(
        persona_block=persona_block,
        user_behavior_json=user_behavior_json,
        user_history_block=user_history_block,
        business_tabular_block=business_tabular_block,
        business_behavior_block=business_behavior_block,
        similar_businesses_block=similar_businesses_block,
        similar_reviews_block=similar_reviews_block,
        max_chars=max_chars,
    )
    return REVIEW_JSON_SYSTEM_PROMPT.strip(), user_prompt.strip()
