"""CLI: generate a PRD-shaped review JSON for `(user_id, business_id)`.

Loads FAISS + Parquet, ensures `persona` exists in `test_users.json` (same as Phase 4),
then calls the LLM with structured JSON output (`rating`, `review`, `reasoning`).

Unknown `user_id` (not under `existing` / `cold_start` in test_users.json) exits with an error.

Usage:

    uv run python -m app.generation.build_review --user-id USER --business-id BIZ

Requires embeddings, behaviour JSONL, and API credentials (see `OpenAILLMClient`).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.generation.openai_client import OpenAILLMClient
from app.generation.review_generation_service import ReviewGenerationService
from app.retrieval.registry import default_embeddings_dir, default_processed_dir

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user-id", required=True, help="Must be listed in test_users.json")
    parser.add_argument(
        "--business-id",
        required=True,
        help="Must exist in businesses.parquet (subset) and business_behavior.jsonl",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=480,
        help="Soft cap hinted to the model (server review API uses the same default when omitted).",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Override app/data/processed",
    )
    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default=None,
        help="Override app/data/embeddings",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point: print JSON result to stdout."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    proc = args.processed_dir or default_processed_dir()
    emb = args.embeddings_dir or default_embeddings_dir()
    try:
        service = ReviewGenerationService.from_default_paths(processed_dir=proc, embeddings_dir=emb)
        llm = OpenAILLMClient(allow_env_fallback=True)
        result = service.generate(
            args.user_id,
            args.business_id,
            max_chars=args.max_chars,
            llm=llm,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
    except KeyError as exc:
        logger.error("%s", exc)
        return 2
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 3
    payload = {
        "user_id": args.user_id,
        "business_id": args.business_id,
        "result": result.model_dump(mode="json"),
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
