"""OpenAI-backed implementation of `LLMClient` for persona and review generation."""

import os
from typing import Any, Final

from openai import APIStatusError, AuthenticationError, OpenAI

_DEFAULT_MODEL: Final[str] = "gpt-4o-mini"


class OpenAILLMClient:
    """Thin wrapper around the OpenAI Chat Completions API (default host: api.openai.com)."""

    def __init__(
        self,
        model: str | None = None,
        client: OpenAI | None = None,
        api_key: str | None = None,
        *,
        allow_env_fallback: bool = True,
    ) -> None:
        """Build the SDK client.

        When `api_key` is a non-empty string, **only** that key is used (`allow_env_fallback` is ignored).
        When `api_key` is omitted or blank and `allow_env_fallback` is True, uses `AI_API_KEY` then
        `OPENAI_API_KEY` from the process environment.
        When `api_key` is blank and `allow_env_fallback` is False, raises `ValueError`.
        """
        if client is not None:
            self._client = client
        else:
            explicit_key = (api_key or "").strip()
            if explicit_key:
                resolved_key = explicit_key
            elif allow_env_fallback:
                resolved_key = (os.getenv("AI_API_KEY") or "").strip()
            else:
                resolved_key = ""
            if not resolved_key:
                raise ValueError(
                    "No API key provided. Send Authorization: Bearer <key> on POST /reviews, "
                    "or set AI_API_KEY / OPENAI_API_KEY in the environment."
                )
            self._client = OpenAI(api_key=resolved_key, max_retries=5)
        self._model = model or os.getenv("AI_MODEL", _DEFAULT_MODEL)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 512,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant message content for a single turn."""
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            #"extra_body": {"chat_template_kwargs":{"thinking":False}}
        }
        #print(f"Going to call OpenAI with kwargs: {kwargs}")
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._client.chat.completions.create(**kwargs)
        except APIStatusError as exc:
            if exc.status_code == 502:
                raise RuntimeError(
                    "LLM provider returned HTTP 502 Bad Gateway. Retry in a few minutes."
                ) from exc
            if exc.status_code == 503:
                raise RuntimeError(
                    "LLM provider returned HTTP 503 Service Unavailable. Retry shortly."
                ) from exc
            if exc.status_code == 504:
                raise RuntimeError(
                    "LLM provider returned HTTP 504 Gateway Timeout. Retry or lower max_tokens."
                ) from exc
            raise
        choice = response.choices[0]
        content = choice.message.content
        if content is None:
            return ""
        return content
