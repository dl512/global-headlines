"""
Futu Stock News Crawler
Crawls stock-specific news from Futu (futunn.com) for HK-listed stocks
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.generic_news_crawler import process_news_site
from common.openai_utils import initialize_openai_client
from common.csv_storage import save_futu_stock_news_item_to_csv

# Stock code to company name mapping (for HK-listed stocks)
STOCK_CODE_TO_COMPANY = {
    "09988": "Alibaba",
    "00700": "Tencent",
    "09888": "Baidu",
    "09618": "JD",
    "09999": "Netease",
    "01024": "Kuaishou",
    "03690": "Meituan",
    "01810": "Xiaomi",
    "01211": "BYD",
    "09866": "NIO",
    "09868": "Xpeng",
    "02015": "Li Auto",
    "09863": "Leap Motor",
    "00020": "SenseTime",
    "09660": "Horizon Robotics",
    "02525": "Hesai",
    "02665": "Seyond",
    "02498": "Robosense",
    "02590": "Geekplus",
    "02432": "Dobot",
    "09880": "Ubtech",
    "02026": "Pony",
    "00800": "WeRide",
    "01021": "Huayan Robotics",
    "00100": "Minimax",
    "02513": "Zhipu",
    "01347": "Hua Hong",
    "00981": "SMIC",
    "06082": "Biren",
}


def get_company_name(stock_code: str) -> str:
    """Get company name from stock code"""
    return STOCK_CODE_TO_COMPANY.get(stock_code, f"Stock {stock_code}")


async def crawl_futu_stock_news(stock_codes: List[str] = None) -> List[Dict[str, Any]]:
    """Crawl stock-specific news from Futu for given stock codes
    
    Args:
        stock_codes: List of 5-digit stock codes (e.g., ["00981", "00100"])
                    If None, will load from component_config.json
    
    Returns:
        List of news items with stock code and company information
    """
    print("Starting Futu stock news crawl...")
    
    # Load stock codes from config if not provided
    if stock_codes is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "component_config.json"
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                regulatory_config = config.get("components", {}).get("regulatory", {})
                crawler_inputs = regulatory_config.get("crawler", {}).get("inputs", {})
                stock_codes_config = crawler_inputs.get("stock_codes", {})
                
                if stock_codes_config.get("source") == "inline":
                    stock_codes = stock_codes_config.get("default", [])
                else:
                    print("ERROR: Could not load stock codes from config")
                    return []
        except Exception as e:
            print(f"ERROR: Failed to load stock codes from config: {e}")
            return []
    
    if not stock_codes:
        print("ERROR: No stock codes provided")
        return []
    
    print(f"Processing {len(stock_codes)} stocks...")
    
    client = initialize_openai_client()
    all_news_items = []
    
    # Date filter mode: today_or_yesterday (same as top_news approach)
    date_filter_mode = "today_or_yesterday"
    
    # Special handling for Futu news (similar to financial_news)
    special_handling = {
        "is_futu_news": True
    }
    
    for stock_code in stock_codes:
        company = get_company_name(stock_code)
        
        # Construct Futu URL: https://www.futunn.com/hk/stock/00981-HK/news
        futu_url = f"https://www.futunn.com/hk/stock/{stock_code}-HK/news"
        
        print(f"\n{'='*80}")
        print(f"Processing: {company} ({stock_code})")
        print(f"  URL: {futu_url}")
        print('='*80)
        
        try:
            # Use generic_news_crawler's process_news_site function
            # Enable early stop for Futu news (articles are ordered newest to oldest)
            site_news = await process_news_site(client, futu_url, date_filter_mode, special_handling=special_handling, enable_early_stop=True)
            
            if not site_news or not site_news.news_items:
                print(f"    No news found for {company} ({stock_code})")
                continue
            
            print(f"    Found {len(site_news.news_items)} news items")
            
            # Save each news item with stock code and company name
            for news_item in site_news.news_items:
                headline = news_item.headline
                url = news_item.url
                html = news_item.html
                
                # Generate summary from article HTML
                summary = ""
                try:
                    from crawlers.generic_news_crawler import generate_article_summary
                    summary = await generate_article_summary(client, headline, url, html)
                except Exception as e:
                    print(f"    WARNING: Failed to generate summary: {e}")
                    summary = ""
                
                # Save to CSV
                save_futu_stock_news_item_to_csv(stock_code, company, headline, url, summary)
                print(f"    ✓ Saved: {headline[:60]}...")
                
                all_news_items.append({
                    "stock_code": stock_code,
                    "company": company,
                    "headline": headline,
                    "url": url,
                    "summary": summary
                })
        
        except Exception as e:
            print(f"    ERROR: Failed to crawl {company} ({stock_code}): {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*80}")
    print(f"Futu stock news crawl completed")
    print(f"  Total stocks processed: {len(stock_codes)}")
    print(f"  Total news items found: {len(all_news_items)}")
    print('='*80)
    
    return all_news_items


async def crawl_futu_stock_news_from_config() -> List[Dict[str, Any]]:
    """Convenience function to crawl Futu stock news using config"""
    return await crawl_futu_stock_news(None)


if __name__ == "__main__":
    # Test the crawler
    asyncio.run(crawl_futu_stock_news_from_config())

