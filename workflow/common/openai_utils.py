"""
Common OpenAI utilities

Light-tier fallback (crawlers, translation, etc.) uses Eden AI when the primary
provider fails. Set EDENAI_API_KEY in .env (never commit it). Optional:
EDENAI_BASE_URL (default https://api.edenai.run/v3/llm), LLM_MODEL_LIGHT_FALLBACK
(default @edenai smart routing).
"""

import logging
import os
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_EDEN_ASYNC_CLIENT: Optional[AsyncOpenAI] = None


def initialize_openai_client() -> AsyncOpenAI:
    """Initialize and return OpenAI client"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_base_url = os.getenv('BASE_URL')

    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    return AsyncOpenAI(
        base_url=openai_base_url,
        api_key=openai_api_key,
    )


def get_llm_model_main() -> str:
    """Primary model for heavier summarization / consolidation (default: GPT-4.1)."""
    return os.getenv("LLM_MODEL_MAIN", "openai/gpt-4.1")


def get_llm_model_light() -> str:
    """Primary model for crawlers, translation, relevance (default: GPT-4.1 nano)."""
    return os.getenv("LLM_MODEL_LIGHT", "openai/gpt-4.1-nano")


def get_llm_model_main_fallback() -> str:
    return os.getenv("LLM_MODEL_MAIN_FALLBACK", "meta-llama/llama-3.3-70b-instruct")


def get_llm_model_light_fallback_eden() -> str:
    """Model string for Eden AI when light-tier primary fails (default: smart router)."""
    return os.getenv("LLM_MODEL_LIGHT_FALLBACK", "@edenai")


def get_edenai_base_url() -> str:
    """OpenAI-compatible chat base (no trailing slash). Full path ends with /chat/completions."""
    return os.getenv("EDENAI_BASE_URL", "https://api.edenai.run/v3/llm").rstrip("/")


def extract_json_text_from_llm_response(content: str) -> str:
    """
    Normalize LLM output for json.loads. Some models wrap JSON in markdown fences
    despite instructions; strip those or take the outermost JSON object.
    """
    s = (content or "").strip()
    if not s:
        return s
    lower = s.lower()
    if "```json" in lower:
        idx = lower.find("```json")
        start = idx + 7
        end = s.find("```", start)
        if end != -1:
            return s[start:end].strip()
    if "```" in s:
        start = s.find("```") + 3
        end = s.find("```", start)
        if end != -1:
            return s[start:end].strip()
    lb = s.find("{")
    rb = s.rfind("}")
    if lb != -1 and rb != -1 and rb > lb:
        return s[lb : rb + 1]
    return s


def get_edenai_async_client() -> Optional[AsyncOpenAI]:
    """Separate client for Eden AI; uses EDENAI_API_KEY, not OPENAI_API_KEY."""
    global _EDEN_ASYNC_CLIENT
    api_key = os.getenv("EDENAI_API_KEY", "").strip()
    if not api_key:
        return None
    if _EDEN_ASYNC_CLIENT is None:
        _EDEN_ASYNC_CLIENT = AsyncOpenAI(
            api_key=api_key,
            base_url=get_edenai_base_url(),
        )
    return _EDEN_ASYNC_CLIENT


async def chat_completion_with_fallback(
    client: AsyncOpenAI,
    tier: Literal["main", "light"],
    **kwargs: Any,
) -> Any:
    """
    Call chat.completions.create using the primary model for this tier.
    On failure: main tier retries with LLM_MODEL_MAIN_FALLBACK; light tier retries
    via Eden AI if EDENAI_API_KEY is set, otherwise the original error is raised.
    """
    kwargs = {k: v for k, v in kwargs.items() if k != "model"}
    if tier == "light":
        primary = get_llm_model_light()
        try:
            return await client.chat.completions.create(model=primary, **kwargs)
        except Exception as e:
            eden = get_edenai_async_client()
            if eden is None:
                logger.warning(
                    "chat.completions light model %s failed (%s); no EDENAI_API_KEY, not retrying",
                    primary,
                    e,
                )
                raise
            fb = get_llm_model_light_fallback_eden()
            logger.warning(
                "chat.completions light model %s failed (%s); retrying via Eden AI (%s)",
                primary,
                e,
                fb,
            )
            return await eden.chat.completions.create(model=fb, **kwargs)
    primary = get_llm_model_main()
    fallback = get_llm_model_main_fallback()
    try:
        return await client.chat.completions.create(model=primary, **kwargs)
    except Exception as e:
        logger.warning(
            "chat.completions primary model %s failed (%s); retrying with %s",
            primary,
            e,
            fallback,
        )
        return await client.chat.completions.create(model=fallback, **kwargs)
