"""
Common OpenAI utilities
"""

import logging
import os
from typing import Any, Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)

logger = logging.getLogger(__name__)


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


def get_llm_model_light_fallback() -> str:
    return os.getenv("LLM_MODEL_LIGHT_FALLBACK", "google/gemma-2-9b-it")


async def chat_completion_with_fallback(
    client: AsyncOpenAI,
    tier: Literal["main", "light"],
    **kwargs: Any,
) -> Any:
    """
    Call chat.completions.create using the primary model for this tier; on failure,
    retry once with the configured fallback (Llama 70B for main, Gemma for light).
    """
    kwargs = {k: v for k, v in kwargs.items() if k != "model"}
    if tier == "main":
        primary = get_llm_model_main()
        fallback = get_llm_model_main_fallback()
    else:
        primary = get_llm_model_light()
        fallback = get_llm_model_light_fallback()
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
