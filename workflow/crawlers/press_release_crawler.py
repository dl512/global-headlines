"""
Press Release Crawler
Crawls press releases from company websites using generic_news_crawler
Extracted from corporate_news_crawler for use in master corporate news crawler
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.generic_news_crawler import process_news_site
from common.openai_utils import initialize_openai_client
from common.csv_storage import save_corporate_news_item_to_csv
from common.link_cache import save_seen_link


async def crawl_press_release_for_company(company: str, websites: List[str], client=None) -> List[Dict[str, Any]]:
    """Crawl press releases for a single company from its websites
    
    Args:
        company: Company name (e.g., "TSMC", "NVIDIA")
        websites: List of website URLs to crawl
        client: Optional OpenAI client (will create if not provided)
    
    Returns:
        List of news items with company information
    """
    if client is None:
        client = initialize_openai_client()
    
    all_news_items = []
    
    # Date filter mode: today_or_yesterday (same as top_news approach)
    date_filter_mode = "today_or_yesterday"
    
    for website in websites:
        print(f"\n  Crawling: {website}")
        try:
            # Use generic_news_crawler's process_news_site function
            # Enable early stop for press releases (articles are ordered newest to oldest)
            site_news = await process_news_site(client, website, date_filter_mode, special_handling=None, enable_early_stop=True)
            
            if not site_news or not site_news.news_items:
                print(f"    No news found for {company} from {website}")
                continue
            
            print(f"    Found {len(site_news.news_items)} news items")
            
            # Process all news items (press releases from company websites are already about the company)
            for news_item in site_news.news_items:
                headline = news_item.headline
                url = news_item.url
                html = news_item.html
                
                # Generate summary from article HTML
                summary = ""
                try:
                    from crawlers.generic_news_crawler import generate_article_summary
                    summary = await generate_article_summary(client, headline, url, html)
                    if not summary:
                        summary = "Summary not available"
                except Exception as e:
                    print(f"      WARNING: Failed to generate summary: {e}")
                    summary = "Summary not available"
                
                # Extract actual publication date from article HTML
                date_obj = None
                try:
                    from crawlers.generic_news_crawler import extract_publication_date
                    date_obj = await extract_publication_date(client, html, url)
                except Exception as e:
                    print(f"      WARNING: Failed to extract publication date: {e}")
                
                # Verify extracted date is within acceptable range (today or yesterday)
                today = datetime.now()
                yesterday = today - timedelta(days=1)
                
                if date_obj is not None:
                    # Check if extracted date is today or yesterday
                    if date_obj.date() != today.date() and date_obj.date() != yesterday.date():
                        print(f"      ✗ REJECTED: Extracted date {date_obj.date()} is not today or yesterday - skipping")
                        # Save to cache (not relevant for today/yesterday)
                        save_seen_link(website, url, headline, was_relevant=False)
                        continue
                    print(f"      ✓ Date verified: {date_obj.date()} is within acceptable range")
                else:
                    # Fallback to today's date if extraction failed
                    date_obj = datetime.now()
                    print(f"      WARNING: Using today's date as fallback (could not extract publication date)")
                
                try:
                    save_corporate_news_item_to_csv(
                        company=company,
                        headline=headline,
                        url=url,
                        summary=summary,
                        date=date_obj,
                        stock_code=None,  # Press releases don't have stock codes
                        source="press_release"
                    )
                    headline_display = headline[:60] if len(headline) > 60 else headline
                    try:
                        print(f"      [OK] Saved: {headline_display}...", encoding='utf-8')
                    except (UnicodeEncodeError, TypeError):
                        headline_ascii = headline_display.encode('ascii', 'ignore').decode('ascii')
                        print(f"      [OK] Saved: {headline_ascii}...")
                    # Save to cache (relevant - press releases are always about the company)
                    save_seen_link(website, url, headline, was_relevant=True)
                except Exception as e:
                    print(f"      [ERROR] Error saving: {e}")
                    # Save to cache even if save failed
                    save_seen_link(website, url, headline, was_relevant=True)
                
                all_news_items.append({
                    'company': company,
                    'headline': headline,
                    'link': url,
                    'summary': summary,
                    'date': date_obj
                })
        
        except Exception as e:
            print(f"    [ERROR] Error crawling {website}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return all_news_items


if __name__ == "__main__":
    # Test with a single company
    async def test():
        result = await crawl_press_release_for_company("TSMC", ["https://pr.tsmc.com/english/latest-news"])
        print(f"\nFound {len(result)} items")
    
    asyncio.run(test())

