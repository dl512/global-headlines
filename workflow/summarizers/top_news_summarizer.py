"""
Top News Summarizer
Reads from NewsData sheet and generates markdown summary using LLM
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client
from common.news_consolidation import consolidate_and_summarize_from_csv


async def summarize_top_news(date: Optional[datetime] = None) -> str:
    """Summarize top news from NewsData sheet using LLM
    
    Args:
        date: Optional date to filter news (defaults to today)
    
    Returns:
        Markdown formatted summary
    """
    client = initialize_openai_client()
    
    # Use CSV-based consolidation logic
    summary = await consolidate_and_summarize_from_csv(client, news_type="top_news", section_title="Most Important Stories")
    
    if not summary:
        return "## Top News\n\nNo top news available.\n"
    
    return summary


if __name__ == "__main__":
    summary = asyncio.run(summarize_top_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("top_news", summary)
    print(f"\n✓ Summary saved to: {filepath}")

