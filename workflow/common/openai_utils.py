"""
Common OpenAI utilities
"""

import logging
import os
from typing import Any, Literal

from openai import AsyncOpenAI

try:
    from .env_loader import load_project_dotenv
except ImportError:
    from common.env_loader import load_project_dotenv

load_project_dotenv()

logger = logging.getLogger(__name__)


def initialize_openai_client() -> AsyncOpenAI:
    """Initialize and return OpenAI client"""
    # Prefer Vercel AI Gateway when AI_GATEWAY_API_KEY is present.
    gateway_api_key = os.getenv("AI_GATEWAY_API_KEY")
    openai_api_key = gateway_api_key or os.getenv("OPENAI_API_KEY")
    openai_base_url = (
        os.getenv("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")
        if gateway_api_key
        else os.getenv("BASE_URL")
    )

    if not openai_api_key:
        raise ValueError(
            "Missing API key: set AI_GATEWAY_API_KEY (preferred) or OPENAI_API_KEY"
        )

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


async def chat_completion_with_fallback(
    client: AsyncOpenAI,
    tier: Literal["main", "light"],
    **kwargs: Any,
) -> Any:
    """
    Call chat.completions.create using the primary model for this tier.
    On failure, main tier retries with LLM_MODEL_MAIN_FALLBACK; light tier does not.
    """
    kwargs = {k: v for k, v in kwargs.items() if k != "model"}
    if tier == "light":
        return await client.chat.completions.create(
            model=get_llm_model_light(),
            **kwargs,
        )
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
