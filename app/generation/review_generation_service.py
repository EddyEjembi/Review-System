"""End-to-end review generation: persona on demand + retrieval + LLM JSON output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.constants import REVIEW_COMPLETION_TEMPERATURE, REVIEW_PROMPT_MAX_CHARS_DEFAULT
from app.generation.business_behavior_store import load_business_behavior_index
from app.generation.llm_client import LLMClient, NotImplementedLLMClient
from app.generation.openai_client import OpenAILLMClient
from app.generation.prompt_builder import build_review_json_prompt
from app.generation.review_context_builder import (
    build_review_search_query,
    format_business_behavior_block,
    format_business_tabular_row,
    format_similar_businesses_block,
    format_similar_reviews_block,
    format_user_behavior_json,
    format_user_history_block,
)
from app.generation.review_output_parser import parse_review_generation_result
from app.models.schemas import Persona, ReviewGenerationResult
from app.persona.behavior_store import load_user_behavior_index
from app.persona.ensure_persona import ensure_persona_for_test_user
from app.persona.test_users_store import find_test_user_bucket, load_test_users_payload
from app.retrieval.registry import RetrievalRegistry, default_embeddings_dir, default_processed_dir
from app.types.behavior import BusinessBehaviorProfile, UserBehaviorProfile


@dataclass
class ReviewGenConfig:
    """Tuning knobs for retrieval and LLM."""

    user_history_limit: int = 12
    similar_business_top_k: int = 6
    similar_review_top_k: int = 8
    max_llm_tokens: int = 2200


class ReviewGenerationService:
    """Builds PRD-shaped `ReviewGenerationResult` for `(user_id, business_id)`."""

    def __init__(
        self,
        llm: LLMClient,
        registry: RetrievalRegistry,
        user_behavior: dict[str, UserBehaviorProfile],
        business_behavior: dict[str, BusinessBehaviorProfile],
        processed_dir: Path,
        embeddings_dir: Path,
        config: ReviewGenConfig | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._user_behavior = user_behavior
        self._business_behavior = business_behavior
        self._processed_dir = processed_dir
        self._embeddings_dir = embeddings_dir
        self._config = config or ReviewGenConfig()

    def register_runtime_user_profile(self, profile: UserBehaviorProfile) -> None:
        """Insert or replace a behaviour profile for this process (e.g. after API user creation)."""
        self._user_behavior[profile.user_id] = profile

    @classmethod
    def from_default_paths(
        cls,
        processed_dir: Path | None = None,
        embeddings_dir: Path | None = None,
        llm: LLMClient | None = None,
        config: ReviewGenConfig | None = None,
    ) -> ReviewGenerationService:
        """Load Parquet, FAISS, and behaviour indices. No API key required at load time."""
        proc = processed_dir or default_processed_dir()
        emb = embeddings_dir or default_embeddings_dir()
        ub = load_user_behavior_index(proc / "user_behavior.jsonl")
        bb = load_business_behavior_index(proc / "business_behavior.jsonl")
        reg = RetrievalRegistry.load(processed_dir=proc, embeddings_dir=emb)
        llm_client: LLMClient = llm if llm is not None else NotImplementedLLMClient()
        return cls(llm_client, reg, ub, bb, proc, emb, config)

    def generate(
        self,
        user_id: str,
        business_id: str,
        *,
        temperature: float = REVIEW_COMPLETION_TEMPERATURE,
        max_chars: int = REVIEW_PROMPT_MAX_CHARS_DEFAULT,
        llm: LLMClient | None = None,
    ) -> ReviewGenerationResult:
        """Generate rating + review + reasoning for a registered test user and known business.

        When `llm` is provided, it is used for persona creation (if needed) and for the completion;
        otherwise the service default client (typically from environment variables) is used.

        Raises `ValueError` if `user_id` is not in `test_users.json` or `business_id` is unknown.
        Raises `KeyError` if behaviour files are missing rows for valid ids.
        """
        test_path = self._processed_dir / "test_users.json"
        ensure_persona_for_test_user(
            user_id,
            self._processed_dir,
            self._embeddings_dir,
            llm=llm,
        )

        payload = load_test_users_payload(test_path)
        bucket, index = find_test_user_bucket(payload, user_id)
        persona = Persona.model_validate(payload[bucket][index]["persona"])

        ub = self._user_behavior.get(user_id)
        if ub is None:
            raise KeyError(
                f"No user_behaviour row for user_id={user_id!r}. Re-run `python -m app.behavior.build_behavior`."
            )

        df = self._registry.businesses_df
        bhit = df[df["business_id"] == business_id]
        if bhit.empty:
            raise ValueError(
                f"Unknown business_id={business_id!r}: not present in businesses.parquet subset."
            )
        biz_row = bhit.iloc[0]

        bb = self._business_behavior.get(business_id)
        if bb is None:
            raise KeyError(
                f"No business_behaviour row for business_id={business_id!r}. Re-run behaviour pipeline."
            )

        history = self._registry.user_retriever.fetch_user_history(
            user_id,
            top_k=self._config.user_history_limit,
        )
        sim_biz = self._registry.business_retriever.find_similar_businesses(
            business_id,
            top_k=self._config.similar_business_top_k,
        )
        q = build_review_search_query(biz_row.to_dict())
        sim_rev_matches = self._registry.review_retriever.search(
            q,
            top_k=self._config.similar_review_top_k,
        )
        sim_rev_hydrated = self._registry.review_retriever.hydrate(sim_rev_matches)

        user_behavior_json = format_user_behavior_json(ub)
        user_history_block = format_user_history_block(history)
        business_tabular_block = format_business_tabular_row(biz_row)
        business_behavior_block = format_business_behavior_block(bb)
        similar_businesses_block = format_similar_businesses_block(self._registry, sim_biz)
        similar_reviews_block = format_similar_reviews_block(sim_rev_hydrated)

        system_prompt, user_prompt = build_review_json_prompt(
            persona=persona,
            user_behavior_json=user_behavior_json,
            user_history_block=user_history_block,
            business_tabular_block=business_tabular_block,
            business_behavior_block=business_behavior_block,
            similar_businesses_block=similar_businesses_block,
            similar_reviews_block=similar_reviews_block,
            max_chars=max_chars,
        )

        completion_client = llm if llm is not None else self._llm
        if isinstance(completion_client, NotImplementedLLMClient):
            raise ValueError(
                "No LLM configured. Pass Authorization: Bearer <api_key> on POST /reviews."
            )
        json_mode = isinstance(completion_client, OpenAILLMClient)
        raw = completion_client.complete(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=self._config.max_llm_tokens,
            json_mode=json_mode,
        )
        result = parse_review_generation_result(raw)
        result.metadata["user_id"] = user_id
        result.metadata["business_id"] = business_id
        result.metadata["max_chars"] = max_chars
        return result
