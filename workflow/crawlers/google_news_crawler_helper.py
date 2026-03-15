"""
Google News Crawler Helper
Crawls Google News RSS feeds for company news
"""

import asyncio
import sys
import os
import feedparser
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client
from common.csv_storage import save_corporate_news_item_to_csv
from common import extract_html
from crawlers.corporate_news_utils import is_news_about_company
from crawlers.generic_news_crawler import generate_article_summary
from common.link_cache import is_link_seen, save_seen_link


async def crawl_google_news_for_company(company: str, stock_code: Optional[str] = None, client=None) -> List[Dict[str, Any]]:
    """Crawl Google News RSS feed for a single company
    
    Args:
        company: Company name (e.g., "TSMC", "NVIDIA", "OpenAI")
        stock_code: Optional stock code (for context in relevance checking)
        client: Optional OpenAI client (will create if not provided)
    
    Returns:
        List of news items with company information
    """
    if client is None:
        client = initialize_openai_client()
    
    all_news_items = []
    
    # Construct Google News RSS URL
    # Format: https://news.google.com/rss/search?q=COMPANY+when:1d
    query = quote_plus(f"{company} when:1d")
    rss_url = f"https://news.google.com/rss/search?q={query}"
    
    print(f"\n  Crawling Google News for: {company}")
    print(f"  RSS URL: {rss_url}")
    
    try:
        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            print(f"    No news found for {company}")
            return all_news_items
        
        print(f"    Found {len(feed.entries)} articles in RSS feed, processing first 5...")
        
        # Get first 5 articles
        articles_to_process = feed.entries[:5]
        
        for i, entry in enumerate(articles_to_process, 1):
            title = entry.title
            link = entry.link
            published = entry.published if hasattr(entry, "published") else None
            source = entry.source.title if hasattr(entry, "source") else None
            
            print(f"    [{i}/5] Processing: {title[:60]}...")
            print(f"      URL: {link}")
            
            # Check cache first - if already cached, skip entirely
            # Use RSS URL as the website identifier for Google News
            if is_link_seen(rss_url, link):
                print(f"      [CACHE] Link already processed before - skipping")
                continue
            
            # Fetch article HTML
            try:
                html_dict = extract_html.get_raw_html(link)
                html_content = html_dict.get("html", "") if html_dict else ""
                
                if not html_content:
                    print(f"      ✗ SKIPPED: Failed to fetch HTML")
                    # Save to cache even if HTML fetch failed
                    save_seen_link(rss_url, link, title, was_relevant=False)
                    continue
                
                print(f"      ✓ Fetched HTML ({len(html_content):,} chars)")
                
            except Exception as e:
                print(f"      ✗ SKIPPED: Error fetching HTML: {e}")
                # Save to cache even if error
                save_seen_link(rss_url, link, title, was_relevant=False)
                continue
            
            # Check if news is about this company
            print(f"      Checking relevance for: {title[:60]}...")
            is_relevant = await is_news_about_company(client, title, link, html_content, company, stock_code=stock_code)
            
            if not is_relevant:
                print(f"      ✗ SKIPPED: Not primarily about {company}")
                # Save to cache (not relevant)
                save_seen_link(rss_url, link, title, was_relevant=False)
                continue
            
            print(f"      ✓ RELEVANT: About {company}")
            
            # Generate summary from article HTML
            summary = ""
            try:
                summary = await generate_article_summary(client, title, link, html_content)
                if not summary:
                    summary = "Summary not available"
                else:
                    print(f"      ✓ Generated summary ({len(summary):,} chars)")
            except Exception as e:
                print(f"      WARNING: Failed to generate summary: {e}")
                summary = "Summary not available"
            
            # Use current date (no date filtering for Google News)
            date_obj = datetime.now()
            
            try:
                save_corporate_news_item_to_csv(
                    company=company,
                    headline=title,
                    url=link,
                    summary=summary,
                    date=date_obj,
                    stock_code=stock_code,
                    source="google_news"
                )
                title_display = title[:60] if len(title) > 60 else title
                try:
                    print(f"      [OK] Saved: {title_display}...")
                except (UnicodeEncodeError, TypeError):
                    title_ascii = title_display.encode('ascii', 'ignore').decode('ascii')
                    print(f"      [OK] Saved: {title_ascii}...")
                # Save to cache (relevant)
                save_seen_link(rss_url, link, title, was_relevant=True)
            except Exception as e:
                print(f"      [ERROR] Error saving: {e}")
                # Save to cache even if save failed
                save_seen_link(rss_url, link, title, was_relevant=True)
            
            all_news_items.append({
                'company': company,
                'headline': title,
                'link': link,
                'summary': summary,
                'date': date_obj
            })
        
        print(f"    Processed {len(all_news_items)} relevant articles for {company}")
        
    except Exception as e:
        print(f"    [ERROR] Error crawling Google News for {company}: {e}")
        import traceback
        traceback.print_exc()
    
    return all_news_items


if __name__ == "__main__":
    # Test with a single company
    async def test():
        result = await crawl_google_news_for_company("OpenAI")
        print(f"\nFound {len(result)} items")
    
    asyncio.run(test())

