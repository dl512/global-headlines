"""
Common OpenAI utilities
"""

import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)


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

