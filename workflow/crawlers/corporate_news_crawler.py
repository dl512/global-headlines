"""
Master Corporate News Crawler
Orchestrates crawling from multiple sources (regulatory, Futu, press releases) for companies
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.regulatory_crawler_helper import crawl_regulatory_for_company
from crawlers.futu_crawler_helper import crawl_futu_for_company
from crawlers.press_release_crawler import crawl_press_release_for_company
from crawlers.google_news_crawler_helper import crawl_google_news_for_company
from common.openai_utils import initialize_openai_client


async def crawl_corporate_news(
    company_configs: List[Dict[str, Any]],
    google_news_simple_csv: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Master corporate news crawler that orchestrates crawling from multiple sources
    
    Args:
        company_configs: List of company configurations, each with:
            - company: Company name (e.g., "Alibaba", "TSMC")
            - stock_code: Optional 5-digit stock code for HK-listed stocks (e.g., "09988")
            - methods: List of methods to use ["regulatory", "futu", "press_release"]
            - websites: Optional list of websites for press_release method
        google_news_simple_csv: If set, Google News hits are saved to this news_type CSV (4 columns) instead of corporate_news.

    Returns:
        List of all news items found
    """
    print("=" * 80)
    print("MASTER CORPORATE NEWS CRAWLER")
    print("=" * 80)
    print(f"Processing {len(company_configs)} companies...")
    print()
    
    client = initialize_openai_client()
    all_news_items = []
    
    for i, company_config in enumerate(company_configs, 1):
        company = company_config.get("company", "")
        stock_code = company_config.get("stock_code", None)
        methods = company_config.get("methods", [])
        websites = company_config.get("websites", [])
        google_query = company_config.get("google_query", None)
        market = company_config.get("market", "HK")  # Default to HK, can be "SH" for A-shares
        
        if not company:
            print(f"[{i}/{len(company_configs)}] WARNING: Skipping invalid company config (no company name)")
            continue
        
        print(f"\n{'='*80}")
        print(f"[{i}/{len(company_configs)}] Processing: {company}")
        if stock_code:
            print(f"  Stock Code: {stock_code}")
        print(f"  Methods: {', '.join(methods)}")
        print('='*80)
        
        # Crawl using each specified method
        for method in methods:
            try:
                if method == "regulatory":
                    if not stock_code:
                        print(f"  WARNING: Skipping regulatory method - no stock_code provided for {company}")
                        continue
                    items = await crawl_regulatory_for_company(company, stock_code, client=client)
                    all_news_items.extend(items)
                
                elif method == "futu":
                    if not stock_code:
                        print(f"  WARNING: Skipping futu method - no stock_code provided for {company}")
                        continue
                    items = await crawl_futu_for_company(company, stock_code, client=client, market=market)
                    all_news_items.extend(items)
                
                elif method == "press_release":
                    if not websites:
                        print(f"  WARNING: Skipping press_release method - no websites provided for {company}")
                        continue
                    items = await crawl_press_release_for_company(company, websites, client=client)
                    all_news_items.extend(items)
                
                elif method == "google_news":
                    # Google News doesn't require any additional parameters
                    items = await crawl_google_news_for_company(
                        company,
                        stock_code=stock_code,
                        client=client,
                        search_query=google_query,
                        simple_csv_news_type=google_news_simple_csv,
                    )
                    all_news_items.extend(items)
                
                else:
                    print(f"  WARNING: Unknown method '{method}' - skipping")
            
            except Exception as e:
                print(f"  ERROR: Failed to crawl {company} using method '{method}': {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"\n{'='*80}")
    print(f"Master corporate news crawl complete")
    print(f"  Total companies processed: {len(company_configs)}")
    print(f"  Total news items found: {len(all_news_items)}")
    print('='*80)
    
    return all_news_items


async def crawl_corporate_news_from_config() -> List[Dict[str, Any]]:
    """Crawl corporate news based on configuration in component_config.json"""
    # Load component config
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "component_config.json"
    )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        component_config = json.load(f)
    
    if "corporate_news" not in component_config.get("components", {}):
        raise ValueError("Component 'corporate_news' not found in component_config.json")
    
    component = component_config["components"]["corporate_news"]
    crawler_config = component.get("crawler", {})
    inputs = crawler_config.get("inputs", {})
    
    # Extract company_configs
    company_configs_config = inputs.get("company_configs", {})
    company_configs = company_configs_config.get("value", company_configs_config.get("default", []))
    
    if not company_configs:
        print("WARNING: No company_configs configured")
        return []
    
    return await crawl_corporate_news(company_configs)


if __name__ == "__main__":
    asyncio.run(crawl_corporate_news_from_config())
