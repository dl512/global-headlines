"""
Test script to crawl specific websites
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.generic_news_crawler import process_news_site, generate_article_summary
from common.openai_utils import initialize_openai_client
from common.csv_storage import save_news_item_to_csv
from datetime import datetime

async def crawl_specific_sites():
    """Crawl only the two specified websites"""
    websites = [
        "https://www.eetimes.com/tag/semiconductors/",
        "https://asia.nikkei.com/business/tech/semiconductors"
    ]
    
    client = initialize_openai_client()
    date_filter_mode = "today_or_yesterday"
    
    all_news_items = []
    
    for website in websites:
        print(f"\n{'='*80}")
        print(f"Crawling: {website}")
        print('='*80)
        
        try:
            site_news = await process_news_site(client, website, date_filter_mode, special_handling=None)
            
            if site_news and site_news.news_items:
                print(f"\nFound {len(site_news.news_items)} articles from {website}")
                
                for item in site_news.news_items:
                    all_news_items.append({
                        'headline': item.headline,
                        'url': item.url,
                        'summary': '',  # Will be generated during batch save
                        'html': item.html
                    })
            else:
                print(f"No articles found from {website}")
        except Exception as e:
            print(f"Error crawling {website}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save to tech_news.csv
    if all_news_items:
        print(f"\n{'='*80}")
        print(f"Saving {len(all_news_items)} articles to tech_news.csv")
        print('='*80)
        
        today_obj = datetime.now()
        
        for i, item in enumerate(all_news_items, 1):
            print(f"  [{i}/{len(all_news_items)}] Processing: {item['headline'][:60]}...")
            
            # Generate summary
            summary = await generate_article_summary(client, item['headline'], item['url'], item['html'], news_type="tech_news")
            
            if summary:
                # Save to CSV (pass datetime object, not string)
                save_news_item_to_csv("tech_news", item['headline'], item['url'], summary, today_obj)
                print(f"    [OK] Saved to tech_news.csv")
            else:
                print(f"    [WARNING] No summary generated, skipping")
        
        print(f"\n[OK] Successfully saved {len(all_news_items)} articles to tech_news.csv")
    else:
        print("\n[WARNING] No articles to save")

if __name__ == "__main__":
    asyncio.run(crawl_specific_sites())

