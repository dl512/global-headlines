"""
HK IPO News Crawler
Crawls HK IPO news from AAStocks and saves to HKIPO sheet
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.csv_storage import batch_save_news_items_to_csv
from crawlers.aastocks_ipo import fetch_aastocks_ipo_news


def get_trading_dates() -> List[str]:
    """Get today and previous trading day dates in DD/MM/YYYY format"""
    today = datetime.now()
    
    # Find previous trading day (skip weekends)
    if today.weekday() == 0:  # Monday
        previous_weekday = today - timedelta(days=3)  # Go back to Friday
    else:
        previous_weekday = today - timedelta(days=1)  # Go back one day
    
    formatted_today = today.strftime('%d/%m/%Y')
    formatted_previous = previous_weekday.strftime('%d/%m/%Y')
    
    return [formatted_previous, formatted_today]


async def crawl_hk_ipo_news(dates: List[str] = None) -> List[Dict[str, Any]]:
    """Crawl HK IPO news from AAStocks and save to CSV
    
    Args:
        dates: List of dates in DD/MM/YYYY format to filter news (defaults to today and previous trading day)
    
    Returns:
        List of IPO news items
    """
    print("Starting HK IPO news crawl...")
    
    # Get trading dates if not provided
    if dates is None:
        dates = get_trading_dates()
    
    print(f"Filtering for dates: {dates}")
    
    # Fetch IPO news using existing AAStocks scraper
    ipo_items_raw = await fetch_aastocks_ipo_news(dates=dates)
    
    # Collect all items for batch writing
    all_news_data_for_batch = []
    ipo_items = []
    
    for item in ipo_items_raw:
        headline = item.get('headline', '')
        url = item.get('url', '')
        summary = item.get('summary', '')
        date_str = item.get('date', '')
        
        # Parse date
        try:
            if date_str:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            else:
                date_obj = datetime.now()
        except:
            date_obj = datetime.now()
        
        # Use unambiguous English date format: "January 8, 2025"
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        date_str_formatted = f"{month_names[date_obj.month - 1]} {date_obj.day}, {date_obj.year}"
        
        # Prepare batch item: [date, headline, url, summary]
        all_news_data_for_batch.append([
            date_str_formatted,
            headline,
            url,
            summary
        ])
        
        ipo_items.append({
            'date': date_obj,
            'headline': headline,
            'link': url,
            'summary': summary,
            'raw_data': item
        })
    
    # Perform batch save after processing all items
    if all_news_data_for_batch:
        try:
            batch_save_news_items_to_csv("hk_ipo", all_news_data_for_batch)
            print(f"✓ Saved {len(all_news_data_for_batch)} HK IPO news items to hk_ipo.csv")
        except Exception as e:
            print(f"❌ Error saving batch to CSV: {e}")
    
    print(f"HK IPO news crawl complete. Found {len(ipo_items)} items")
    return ipo_items


if __name__ == "__main__":
    asyncio.run(crawl_hk_ipo_news())

