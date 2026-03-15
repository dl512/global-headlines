"""
Regulatory Crawler Helper
Crawls Futu announcement pages for HK-listed stocks (replaces HKEX website)
Extracted functions from regulatory_announcement_crawler for use in master corporate news crawler
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.generic_news_crawler import process_news_site, generate_article_summary
from crawlers.regulatory_announcement_crawler import (
    prescreen, is_relevant, generate_pdf_summary, get_trading_dates
)
from common.openai_utils import initialize_openai_client
from common.csv_storage import save_corporate_news_item_to_csv
from crawlers.corporate_news_utils import is_news_about_company
from common.link_cache import is_link_seen, save_seen_link


async def crawl_regulatory_for_company(company: str, stock_code: str, dates: List[str] = None, client=None) -> List[Dict[str, Any]]:
    """Crawl regulatory announcements for a single company from Futu announcement page
    
    Args:
        company: Company name (e.g., "Alibaba", "Hua Hong")
        stock_code: 5-digit stock code (e.g., "09988", "01347")
        dates: List of dates in DD/MM/YYYY format (not used for Futu, kept for compatibility)
        client: Optional OpenAI client (will create if not provided)
    
    Returns:
        List of announcement items
    """
    if client is None:
        client = initialize_openai_client()
    
    print(f"  Crawling regulatory announcements for {company} ({stock_code})")
    
    # Construct Futu announcement URL
    # Format: https://www.futunn.com/hk/stock/01347-HK/announcement
    # Normalize stock code to 5 digits (e.g., "01347" or "1347" -> "01347")
    normalized_code = stock_code.replace('.HK', '').zfill(5)
    futu_url = f"https://www.futunn.com/hk/stock/{normalized_code}-HK/announcement"
    
    # Date filter mode: today_or_yesterday
    date_filter_mode = "today_or_yesterday"
    
    # Special handling for Futu announcements
    special_handling = {
        "is_futu": True
    }
    
    try:
        # Use generic_news_crawler's process_news_site function
        # Enable early stop for Futu announcements (articles are ordered newest to oldest)
        # Skip caching in process_news_site - we'll handle caching after company relevance check
        site_news = await process_news_site(client, futu_url, date_filter_mode, special_handling=special_handling, enable_early_stop=True, skip_caching=True)
        
        if not site_news or not site_news.news_items:
            print(f"    No announcements found for {company} ({stock_code})")
            return []
        
        print(f"    Found {len(site_news.news_items)} announcement items")
        
        regulatory_items = []
        
        # Process each announcement item
        for news_item in site_news.news_items:
            headline = news_item.headline
            url = news_item.url
            html = news_item.html
            
            # Check cache first - if already cached, skip entirely
            if is_link_seen(futu_url, url):
                print(f"      [CACHE] Link already processed before - skipping")
                continue
            
            # Check if the announcement is actually about this company
            print(f"      Checking relevance for: {headline[:60]}...")
            is_relevant_company = await is_news_about_company(client, headline, url, html or "", company, stock_code=stock_code)
            
            if not is_relevant_company:
                print(f"      ✗ SKIPPED: Not primarily about {company}")
                # Save to cache (not relevant)
                save_seen_link(futu_url, url, headline, was_relevant=False)
                continue
            
            # Prescreen to exclude daily filings (using existing prescreen function)
            if not prescreen(headline):
                print(f"      ✗ SKIPPED: Daily filing (prescreened out)")
                # Save to cache (not relevant)
                save_seen_link(futu_url, url, headline, was_relevant=False)
                continue
            
            # Check if it's a relevant type of announcement (not routine filing)
            if not await is_relevant(client, headline):
                print(f"      ✗ SKIPPED: Routine filing (not relevant)")
                # Save to cache (not relevant)
                save_seen_link(futu_url, url, headline, was_relevant=False)
                continue
            
            print(f"      ✓ RELEVANT: About {company}")
            
            # Generate summary from article HTML
            summary = ""
            try:
                summary = await generate_article_summary(client, headline, url, html)
            except Exception as e:
                print(f"      WARNING: Failed to generate summary: {e}")
                # If URL is a PDF, try PDF summary
                if url and url.endswith('.pdf'):
                    try:
                        summary = await generate_pdf_summary(client, url)
                    except Exception as pdf_e:
                        print(f"      WARNING: Failed to generate PDF summary: {pdf_e}")
                        summary = f"Regulatory announcement: {headline}"
                else:
                    summary = f"Regulatory announcement: {headline}"
            
            # Get date from news_item if available, otherwise use current date
            date_obj = news_item.date if hasattr(news_item, 'date') and news_item.date else datetime.now()
            
            # Save to unified corporate_news CSV
            try:
                save_corporate_news_item_to_csv(
                    company=company,
                    headline=headline,
                    url=url,
                    summary=summary,
                    date=date_obj,
                    stock_code=normalized_code,
                    source="regulatory"
                )
                print(f"    ✓ Saved: {headline[:60]}...")
                # Save to cache (relevant)
                save_seen_link(futu_url, url, headline, was_relevant=True)
            except Exception as e:
                print(f"    WARNING: Failed to save to CSV: {e}")
                # Save to cache even if save failed
                save_seen_link(futu_url, url, headline, was_relevant=True)
            
            regulatory_items.append({
                'date': date_obj,
                'stock_code': normalized_code,
                'company': company,
                'headline': headline,
                'link': url,
                'summary': summary
            })
        
        return regulatory_items
    
    except Exception as e:
        print(f"    ERROR: Failed to crawl {company} ({stock_code}): {e}")
        import traceback
        traceback.print_exc()
        return []

