"""
Test script to crawl AAStocks only
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.crawlers.generic_news_crawler import process_news_site
from workflow.common.openai_utils import initialize_openai_client


async def test_aastocks():
    """Test crawling AAStocks only"""
    print("=" * 80)
    print("Testing AAStocks Crawler")
    print("=" * 80)
    print()
    
    # Initialize client
    client = initialize_openai_client()
    
    # AAStocks URL
    aastocks_url = "http://www.aastocks.com/sc/mobile/news.aspx"
    
    # Process AAStocks with today's date filter
    result = await process_news_site(
        client=client,
        website=aastocks_url,
        date_filter_mode="today",
        special_handling=None
    )
    
    if result:
        print(f"\n{'='*80}")
        print(f"SUCCESS: Found {len(result.news_items)} articles from AAStocks")
        print(f"{'='*80}")
        for i, item in enumerate(result.news_items, 1):
            try:
                print(f"\n[{i}] {item.headline}")
                print(f"    URL: {item.url}")
            except UnicodeEncodeError:
                # Fallback for Windows console encoding issues
                headline_ascii = item.headline.encode('ascii', 'ignore').decode('ascii')
                print(f"\n[{i}] {headline_ascii}")
                print(f"    URL: {item.url}")
    else:
        print("\nNo articles found or error occurred")


if __name__ == "__main__":
    asyncio.run(test_aastocks())

