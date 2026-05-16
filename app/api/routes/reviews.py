"""Endpoint for generating synthetic reviews (`POST /reviews`)."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import AuthenticationError

from app.generation.openai_client import OpenAILLMClient
from app.generation.review_generation_service import ReviewGenerationService
from app.models.requests import MakeReviewRequest
from app.models.responses import GenerateReviewResponse
from app.persona.api_user_registration import persist_new_cold_start_demo_user
from app.retrieval.registry import default_processed_dir

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _review_generation_service() -> ReviewGenerationService:
    """Load retrieval data once per process (no API key at startup)."""
    return ReviewGenerationService.from_default_paths()


def _api_key_from_bearer(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Read the token from `Authorization: Bearer <key>` (Swagger Authorize or curl)."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: Authorization: Bearer <your_openai_api_key>",
        )
    key = (credentials.credentials or "").strip()
    if not key:
        raise HTTPException(status_code=401, detail="Empty Bearer token in Authorization header.")
    return key


@router.post("", response_model=GenerateReviewResponse)
def make_review(
    payload: MakeReviewRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> GenerateReviewResponse:
    """Generate a review. Requires `Authorization: Bearer <openai_api_key>`."""
    llm = OpenAILLMClient(api_key=_api_key_from_bearer(credentials), allow_env_fallback=False)
    service = _review_generation_service()
    resolved_user_id: str
    if payload.new_user is not None:
        nu = payload.new_user
        try:
            new_id, profile = persist_new_cold_start_demo_user(
                default_processed_dir(),
                archetype=nu.archetype,
                demographics=nu.demographics,
                preferences=nu.preferences,
                service_expectations=nu.service_expectations,
                notes=nu.notes,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service.register_runtime_user_profile(profile)
        resolved_user_id = new_id
    else:
        resolved_user_id = (payload.user_id or "").strip()
    max_chars = payload.resolved_max_chars()
    try:
        result = service.generate(
            resolved_user_id,
            payload.business_id,
            max_chars=max_chars,
            llm=llm,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Unknown user_id=") or message.startswith("Unknown business_id="):
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=502, detail=message) from exc
    except KeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GenerateReviewResponse(
        user_id=resolved_user_id,
        business_id=payload.business_id,
        result=result,
    )
