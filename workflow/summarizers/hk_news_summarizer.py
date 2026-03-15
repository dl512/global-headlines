"""
Hong Kong News Summarizer
Reads from CSV and generates markdown summary using LLM
Focuses on most important news related to politics, social, and economy
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


async def summarize_hk_news(date: Optional[datetime] = None) -> str:
    """Summarize Hong Kong news from CSV using LLM
    
    Args:
        date: Optional date to filter news (defaults to today)
    
    Returns:
        Markdown formatted summary
    """
    client = initialize_openai_client()
    
    # Use CSV-based consolidation logic with custom prompt for HK news
    summary = await consolidate_and_summarize_from_csv(
        client, 
        news_type="hk_news", 
        section_title="Hong Kong News"
    )
    
    if not summary:
        return "## Hong Kong News\n\nNo Hong Kong news available.\n"
    
    return summary


if __name__ == "__main__":
    summary = asyncio.run(summarize_hk_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("hk_news", summary)
    print(f"\n✓ Summary saved to: {filepath}")

