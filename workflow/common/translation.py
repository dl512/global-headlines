"""
Common utilities for translating newsletters
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI

from .openai_utils import chat_completion_with_fallback, initialize_openai_client

load_dotenv(override=True)

async def translate_to_chinese(text: str, client: Optional[AsyncOpenAI] = None) -> str:
    """Translate English text to Traditional Chinese (繁體中文)
    
    Args:
        text: English text to translate
        client: Optional OpenAI client (will create one if not provided)
    
    Returns:
        Translated Traditional Chinese text
    """
    if client is None:
        client = initialize_openai_client()
    
    prompt = f"""Translate the following English newsletter content to Traditional Chinese (繁體中文). 
Maintain the markdown formatting, structure, and links exactly as they are.
Only translate the text content, not the markdown syntax or URLs.
Use Traditional Chinese characters (繁體字), not Simplified Chinese (简体字).

English content:
{text}

Translated Traditional Chinese content:"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=8000,
        )
        
        translated = response.choices[0].message.content.strip()
        return translated
    except Exception as e:
        print(f"ERROR: Translation failed: {e}")
        return text  # Return original text if translation fails


def translate_to_chinese_sync(text: str) -> str:
    """Synchronous wrapper for translate_to_chinese"""
    return asyncio.run(translate_to_chinese(text))

