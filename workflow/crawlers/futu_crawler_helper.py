"""
Futu Crawler Helper
Extracted functions from futu_stock_news_crawler for use in master corporate news crawler
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.generic_news_crawler import process_news_site
from common.openai_utils import initialize_openai_client
from common.csv_storage import save_corporate_news_item_to_csv
from crawlers.corporate_news_utils import is_news_about_company
from common.link_cache import is_link_seen, save_seen_link


async def crawl_futu_for_company(company: str, stock_code: str, client=None, market: str = "HK") -> List[Dict[str, Any]]:
    """Crawl Futu stock news for a single company
    
    Args:
        company: Company name (e.g., "Alibaba", "Moore Threads")
        stock_code: Stock code (e.g., "09988" for HK, "688795" for A-share)
        client: Optional OpenAI client (will create if not provided)
        market: Market identifier - "HK" for Hong Kong stocks, "SH" for Shanghai A-shares (default: "HK")
    
    Returns:
        List of news items with company information
    """
    if client is None:
        client = initialize_openai_client()
    
    print(f"  Crawling Futu news for {company} ({stock_code})")
    
    # Construct Futu URL based on market
    # HK-listed: https://www.futunn.com/hk/stock/00981-HK/news
    # A-share (Shanghai): https://www.futunn.com/stock/688795-SH/news
    if market == "SH":
        futu_url = f"https://www.futunn.com/stock/{stock_code}-SH/news"
    else:
        futu_url = f"https://www.futunn.com/hk/stock/{stock_code}-HK/news"
    
    # Date filter mode: today_or_yesterday
    date_filter_mode = "today_or_yesterday"
    
    # Special handling for Futu news
    special_handling = {
        "is_futu_news": True
    }
    
    try:
        # Use generic_news_crawler's process_news_site function
        # Enable early stop for Futu news (articles are ordered newest to oldest)
        # Skip caching in process_news_site - we'll handle caching after company relevance check
        site_news = await process_news_site(client, futu_url, date_filter_mode, special_handling=special_handling, enable_early_stop=True, skip_caching=True)
        
        if not site_news or not site_news.news_items:
            print(f"    No news found for {company} ({stock_code})")
            return []
        
        print(f"    Found {len(site_news.news_items)} news items")
        
        all_news_items = []
        
        # Check each news item for company relevance before saving
        for news_item in site_news.news_items:
            headline = news_item.headline
            url = news_item.url
            html = news_item.html
            
            # Check cache first - if already cached, skip entirely
            if is_link_seen(futu_url, url):
                print(f"      [CACHE] Link already processed before - skipping")
                continue
            
            # CRITICAL: Check if the news is actually about this company
            print(f"      Checking relevance for: {headline[:60]}...")
            is_relevant = await is_news_about_company(client, headline, url, html or "", company, stock_code=stock_code)
            
            if not is_relevant:
                print(f"      ✗ SKIPPED: Not primarily about {company}")
                # Cache as not relevant (don't process, but cache to avoid checking again)
                save_seen_link(futu_url, url, headline, was_relevant=False)
                continue
            
            print(f"      ✓ RELEVANT: About {company}")
            
            # Generate summary from article HTML
            summary = ""
            try:
                from crawlers.generic_news_crawler import generate_article_summary
                summary = await generate_article_summary(client, headline, url, html)
            except Exception as e:
                print(f"      WARNING: Failed to generate summary: {e}")
                summary = ""
            
            # Save to unified corporate_news CSV
            try:
                save_corporate_news_item_to_csv(
                    company=company,
                    headline=headline,
                    url=url,
                    summary=summary,
                    date=datetime.now(),
                    stock_code=stock_code,
                    source="futu"
                )
                print(f"    ✓ Saved: {headline[:60]}...")
                # Save to cache (relevant)
                save_seen_link(futu_url, url, headline, was_relevant=True)
            except Exception as e:
                print(f"    WARNING: Failed to save to CSV: {e}")
                # Save to cache even if save failed
                save_seen_link(futu_url, url, headline, was_relevant=True)
            
            all_news_items.append({
                "stock_code": stock_code,
                "company": company,
                "headline": headline,
                "url": url,
                "summary": summary
            })
        
        return all_news_items
    
    except Exception as e:
        print(f"    ERROR: Failed to crawl {company} ({stock_code}): {e}")
        import traceback
        traceback.print_exc()
        return []

