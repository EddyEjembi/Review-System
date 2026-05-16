"""Retrieve context relevant to a specific business."""

from typing import Any

import pandas as pd

from app.retrieval.vector_store import FaissVectorStore, VectorMatch


class BusinessRetriever:
    """Look up a business's profile, top reviews, and find similar businesses."""

    def __init__(
        self,
        businesses_df: pd.DataFrame,
        reviews_df: pd.DataFrame,
        store: FaissVectorStore,
    ) -> None:
        self._businesses_df = businesses_df
        self._reviews_df = reviews_df
        self._store = store

    def fetch_business_profile(self, business_id: str) -> dict[str, Any] | None:
        """Return the business's row from `businesses.parquet` as a plain dict."""
        mask = self._businesses_df["business_id"] == business_id
        if not mask.any():
            return None
        return self._businesses_df.loc[mask].iloc[0].to_dict()

    def fetch_representative_reviews(
        self,
        business_id: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Return this business's top reviews by community engagement.

        Engagement is `useful + funny + cool`. Ties are broken by recency.
        """
        df = self._reviews_df
        biz_reviews = df[df["business_id"] == business_id].copy()
        if biz_reviews.empty:
            return []
        biz_reviews["_engagement"] = (
            biz_reviews["useful"].fillna(0)
            + biz_reviews["funny"].fillna(0)
            + biz_reviews["cool"].fillna(0)
        )
        biz_reviews = biz_reviews.sort_values(
            by=["_engagement", "date"],
            ascending=[False, False],
        ).head(top_k)
        biz_reviews = biz_reviews.drop(columns=["_engagement"])
        return biz_reviews.to_dict(orient="records")

    def find_similar_businesses(
        self,
        business_id: str,
        top_k: int = 5,
    ) -> list[VectorMatch]:
        """Return businesses semantically similar to `business_id`.

        Uses the business's pre-computed vector; returns `[]` if not indexed.
        """
        vec = self._store.get_vector(business_id)
        if vec is None:
            return []
        results = self._store.search(vec, top_k=top_k + 1)
        return [r for r in results if r.id != business_id][:top_k]
