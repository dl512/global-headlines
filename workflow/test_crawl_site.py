"""
Test helper script to crawl a single website using the generic news crawler.

Usage (from the project root):
    cd workflow
    python test_crawl_site.py https://example.com/news [date_filter_mode] [news_type]

Examples:
    # Crawl a site treating it as tech news, filtering for today or yesterday
    python test_crawl_site.py https://asia.nikkei.com/business/tech/semiconductors today_or_yesterday tech_news

Notes:
    - This script:
        * Uses the same `process_news_site` function as the main pipeline
        * Mirrors the exact logic from `generic_news_crawler.py` (same date format, batch saving, etc.)
        * Saves results to `test_crawl_results.csv` (safe for experimentation, won't affect production data)
        * Prints out basic stats, headlines, and URLs so you can inspect results
"""

import asyncio
import os
import sys
from typing import Optional


def _add_workflow_to_path() -> None:
    """Ensure `workflow` package is on sys.path when run from project root."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Add parent directory of `workflow` to path so imports like `crawlers.*` work
    sys.path.insert(0, script_dir)


_add_workflow_to_path()

from crawlers.generic_news_crawler import process_news_site, generate_article_summary  # noqa: E402
from common.openai_utils import initialize_openai_client  # noqa: E402
from common.csv_storage import batch_save_news_items_to_csv  # noqa: E402
from datetime import datetime  # noqa: E402


async def crawl_single_site(
    website: str,
    date_filter_mode: str = "today_or_yesterday",
    news_type: Optional[str] = None,
) -> None:
    """
    Crawl a single website and print extracted headlines and URLs.

    Args:
        website: Full URL of the listing page to crawl.
        date_filter_mode: "today_or_yesterday", "today", or "none".
        news_type: Optional logical news type (e.g., "tech_news", "top_news").
                   Passed into `special_handling` so the crawler can use
                   the appropriate prompt style. If None, no special handling.
    """
    print("=" * 80)
    print(f"TEST CRAWL: {website}")
    print("=" * 80)
    print(f"Date filter mode: {date_filter_mode}")
    if news_type:
        print(f"News type hint: {news_type}")
    print()

    client = initialize_openai_client()

    special_handling = {}
    if news_type:
        # This key is what the generic crawler expects to choose prompts
        special_handling["news_type"] = news_type

    # IMPORTANT: enable_early_stop=False so we never stop after the first old article
    site_news = await process_news_site(
        client,
        website,
        date_filter_mode,
        special_handling=special_handling,
        enable_early_stop=False,
    )

    if not site_news or not site_news.news_items:
        print()
        print("⚠ No articles returned by process_news_site()")
        return

    items = site_news.news_items
    print()
    print(f"Total articles returned: {len(items)}")
    print("-" * 80)

    # Mirror the exact logic from generic_news_crawler.py
    today_obj = datetime.now()
    # Use unambiguous English date format: "January 8, 2025" (same as main crawler)
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str = f"{month_names[today_obj.month - 1]} {today_obj.day}, {today_obj.year}"
    
    batch_items = []  # Collect items for batch save (same as main crawler)
    
    print(f"\n{'='*80}")
    print(f"GENERATING SUMMARIES AND SAVING TO TEST CSV")
    print('='*80)
    print()
    
    for idx, item in enumerate(items, start=1):
        headline = getattr(item, "headline", "")
        url = getattr(item, "url", "")
        html = getattr(item, "html", "")
        # Truncate very long headlines for display
        headline_display = headline[:60] if len(headline) > 60 else headline

        try:
            print(f"    [{idx}/{len(items)}] Processing article: {headline_display}...")
            print(f"      >> Generating summary from HTML...")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            headline_ascii = headline_display.encode("ascii", "ignore").decode("ascii")
            print(f"    [{idx}/{len(items)}] Processing article: {headline_ascii}...")
            print(f"      >> Generating summary from HTML...")
        
        # Generate summary (same as main crawler)
        summary = await generate_article_summary(
            client, 
            headline, 
            url, 
            html,
            news_type=news_type
        )
        
        if summary:
            summary_size = len(summary)
            print(f"      [OK] Generated summary ({summary_size:,} chars)")
            
            # Add to batch (same format as main crawler: [date_str, headline, url, summary])
            batch_items.append([date_str, headline, url, summary])
            print(f"      >> Added to CSV batch ({len(batch_items)} items so far)")
        else:
            print(f"      [FAIL] Failed to generate summary, skipping article")
        
        print()

    # Batch save to CSV (same as main crawler)
    test_csv_type = "test_crawl_results"
    if batch_items:
        print(f"\n>> Saving {len(batch_items)} items to test CSV...")
        try:
            batch_save_news_items_to_csv(test_csv_type, batch_items)
            test_csv_path = os.path.join(os.path.dirname(__file__), "data", "news_csv", f"{test_csv_type}.csv")
            print(f"[OK] Saved {len(batch_items)} items to {test_csv_path}")
        except Exception as e:
            print(f"❌ Error saving batch to CSV: {e}")
    else:
        print(f"\n⚠ No items to save to CSV")
    
    print("-" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_crawl_site.py URL [date_filter_mode] [news_type]")
        print()
        print("Examples:")
        print("  python test_crawl_site.py https://asia.nikkei.com/business/tech/semiconductors")
        print("  python test_crawl_site.py https://www.eetimes.com/tag/semiconductors/ today_or_yesterday tech_news")
        sys.exit(1)

    url_arg = sys.argv[1]
    date_mode = sys.argv[2] if len(sys.argv) > 2 else "today_or_yesterday"
    news_type_arg = sys.argv[3] if len(sys.argv) > 3 else None

    asyncio.run(crawl_single_site(url_arg, date_mode, news_type_arg))


