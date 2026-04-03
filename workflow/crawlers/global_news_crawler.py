"""
Global News Crawler
Crawls news from sources listed in Countries sheet and saves to GlobalNews sheet
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.google_sheets import get_sources_list, get_news_worksheet, find_first_empty_row, batch_save_news_items
from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
from common import extract_html
from common.csv_storage import batch_save_global_news_to_csv


def remove_html_tags(html_content):
    """Remove HTML tags and return clean text"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def extract_links_from_html(html_string, base_url):
    """Extract all links from HTML and return as a formatted string"""
    soup = BeautifulSoup(html_string, "html.parser")
    links_on_page = ""
    
    for link in soup.find_all("a", href=True):
        url = link.get("href", "")
        link_text = link.get_text(strip=True)
        
        if url and link_text:
            # Resolve relative URLs
            if url.startswith("//"):
                url = urlparse(base_url).scheme + ":" + url
            elif url.startswith("/"):
                url = urljoin(base_url, url)
            elif not url.startswith("http"):
                url = urljoin(base_url, url)
            
            links_on_page += f" [{link_text}]({url})"
    
    return links_on_page


async def extract_main_headline(client, website, html_string_input):
    """Extract the main headline from a news website using LLM"""
    prompt = f"""
You are good at reading html text, visualize the content, and identify the headline of the day.
Given this HTML text from a news website: {html_string_input}

CRITICAL REQUIREMENTS:
1. Identify the main headline of the day - look for the most prominent story on the homepage
2. ALWAYS translate to English if the headline is in any other language
3. Output ONLY the English headline text, nothing else
4. Do not include any non-English words or phrases
5. Ensure the headline is in proper English grammar and spelling
6. If the headline contains any non-English characters or words, translate them to English
7. Focus on the main news story, not navigation items, advertisements, or secondary stories
8. The headline should be the most important news of the day from this source

IMPORTANT: The output must be 100% in English. If you cannot find or translate a headline to English, output "No headline found".
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        
        headline = response.choices[0].message.content.strip()
        
        # Clean up the headline - remove quotes if present
        headline = headline.strip('"').strip("'").strip()
        
        if headline.lower() == "no headline found" or not headline or len(headline) < 10:
            return None
        
        return headline
    except Exception as e:
        print(f"    WARNING: Error extracting headline: {e}")
        return None


async def match_headline_to_link(client, headline, links_on_page, website):
    """Match a headline to the most relevant link on the page"""
    if not links_on_page or not headline:
        return website  # Fallback to homepage
    
    prompt = f"""
Given this identified headline on a news website: "{headline}"
Note that the headline is being translated into English if the original text is non-English.

Please check if the link to that headline is in {links_on_page[:150000]}

If so, please output only the link. 
Note that sometimes only the relative url is included. If so, you need to output the absolute url with the root website {website}.
If no link is found, just output 'N/A'
Do not output anything else other than the link
Do not output any html tags e.g., '<a href=', '</a>'
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        
        url = response.choices[0].message.content.strip()
        
        # Clean up the URL (remove markdown formatting if present)
        url = url.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        url = url.replace("<a href=", "").replace("</a>", "").replace(">", "")
        url = url.strip()
        
        # Handle N/A or invalid responses
        if url.upper() == "N/A" or not url or url == website:
            return website
        
        # Validate and resolve relative URLs
        if url.startswith("http"):
            return url
        elif url.startswith("/"):
            return urljoin(website, url)
        elif url.startswith("//"):
            return urlparse(website).scheme + ":" + url
        else:
            # Try to resolve relative URL
            return urljoin(website, url)
    except Exception as e:
        print(f"    WARNING: Error matching link: {e}")
        return website


async def fetch_article_html(url):
    """Fetch the HTML content of an article page"""
    try:
        html_dict = extract_html.get_raw_html(url)
        if html_dict and html_dict.get("html"):
            return html_dict["html"]
        return None
    except Exception as e:
        print(f"    WARNING: Error fetching article HTML: {e}")
        return None


async def generate_brief_summary(client, headline, url):
    """Generate a brief summary by fetching the article and summarizing it"""
    # First, try to fetch the article HTML
    article_html = await fetch_article_html(url)
    
    if article_html:
        # Extract clean text from article
        clean_text = remove_html_tags(article_html)
        
        # Limit text length for LLM
        if len(clean_text) > 10000:
            clean_text = clean_text[:10000] + "..."
        
        prompt = f"""
You are a capable journalist. This is the headline: "{headline}"
And this is the article content: {clean_text}

Please summarize in 2-3 English bullets to capture the key information. Each bullet should be very concise.
You may assume your readers know nothing about the country's news and politics.
The source may not be in English. But make sure the summary is in English.
"""
    else:
        # Fallback: try to generate from headline only
        prompt = f"""
Given this news headline: "{headline}"
From this source: {url}

Generate a brief 1-2 sentence summary of what this news is about. 
If you cannot determine the content from the headline alone, write: "Summary not available."
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"    WARNING: Error generating summary: {e}")
        return "Summary not available."


async def process_global_news_source(client, source, worksheet):
    """Process a single global news source"""
    website = source.get('Website', '')
    country = source.get('Country', '')
    newspaper = source.get('Newspaper', '')
    
    if not website:
        return None
    
    print(f"Processing {country} - {newspaper}: {website}")
    
    try:
        # Step 1: Extract HTML
        html_dict = extract_html.get_raw_html(website)
        
        if not html_dict or not html_dict.get("html"):
            print(f"  ERROR: Failed to retrieve HTML from {website}")
            return None
        
        html_string = html_dict["html"]
        clean_text = remove_html_tags(html_string)
        
        # Use clean text if HTML is too large
        if len(html_string) > 200000:
            html_string_input = clean_text[:200000]  # Limit size
        else:
            html_string_input = html_string
        
        # Step 2: Extract main headline
        headline = await extract_main_headline(client, website, html_string_input)
        
        if not headline or headline == "No headline found":
            print(f"  WARNING: No headline extracted from {website}")
            return None
        
        print(f"  Headline: {headline}")
        
        # Step 3: Extract links and match to headline
        links_on_page = extract_links_from_html(html_string, website)
        url = await match_headline_to_link(client, headline, links_on_page, website)
        
        print(f"  Link: {url}")
        
        # Step 4: Generate brief summary
        summary = await generate_brief_summary(client, headline, url)
        
        # Return data for batch saving (don't save individually to avoid rate limits)
        date_obj = datetime.now()
        # Use unambiguous English date format: "January 8, 2025"
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        date_str = f"{month_names[date_obj.month - 1]} {date_obj.day}, {date_obj.year}"
        
        return {
            "date": date_str,
            "country": country,
            "newspaper": newspaper,
            "headline": headline,
            "link": url,
            "summary": summary,
            "date_obj": date_obj
        }
        
    except Exception as e:
        print(f"  ERROR: Failed to process {website}: {e}")
        return None


async def crawl_global_news() -> List[Dict[str, Any]]:
    """Crawl global news from sources in Countries sheet and save to GlobalNews sheet
    
    Returns:
        List of news items with keys: date, headline, link, summary
    """
    print("Starting global news crawl...")
    
    # Get sources from Countries sheet
    sources = get_sources_list()
    print(f"Found {len(sources)} sources to crawl")
    
    # Get worksheet for saving
    worksheet = get_news_worksheet("global_news")
    
    # Initialize OpenAI client
    client = initialize_openai_client()
    
    news_items = []
    
    # Process each source (with concurrency limit to avoid rate limits)
    semaphore = asyncio.Semaphore(5)  # Process 5 sources concurrently
    
    async def process_with_semaphore(source):
        async with semaphore:
            return await process_global_news_source(client, source, worksheet)
    
    # Process all sources
    tasks = [process_with_semaphore(source) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect successful results and prepare for batch save
    all_news_data_for_batch = []
    successful_count = 0
    error_count = 0
    none_count = 0
    
    print(f"\nProcessing {len(results)} results from sources...")
    for idx, result in enumerate(results):
        if isinstance(result, dict) and result:
            # Check if dict has required fields (headline is required)
            headline = result.get('headline', '')
            if headline and headline != "No headline found":
                news_items.append(result)
                # Prepare batch item: [Date, Country, Newspaper, Headline, Link, Summary]
                batch_item = [
                    result.get('date', ''),
                    result.get('country', ''),
                    result.get('newspaper', ''),
                    headline,
                    result.get('link', ''),
                    result.get('summary', '')
                ]
                all_news_data_for_batch.append(batch_item)
                successful_count += 1
                print(f"  [OK] Result {idx+1}: {result.get('country', 'N/A')} - {headline[:50]}...")
            else:
                print(f"  [SKIP] Result {idx+1}: Missing headline or 'No headline found' (headline: {headline})")
                none_count += 1
        elif isinstance(result, Exception):
            print(f"  [ERROR] Result {idx+1}: Exception occurred: {result}")
            import traceback
            traceback.print_exc()
            error_count += 1
        elif result is None:
            print(f"  [SKIP] Result {idx+1}: Returned None")
            none_count += 1
        else:
            print(f"  [WARNING] Result {idx+1}: Unexpected type: {type(result)}, value: {str(result)[:100]}")
            none_count += 1
    
    print(f"\nSummary: {successful_count} successful, {error_count} errors, {none_count} skipped/None")
    print(f"Prepared {len(all_news_data_for_batch)} items for batch save")
    
    # Save to CSV first (more reliable), then Google Sheets
    csv_success = False
    sheets_success = False
    
    if all_news_data_for_batch:
        print(f"\n>> Saving {len(all_news_data_for_batch)} global news items to CSV...")
        try:
            batch_save_global_news_to_csv(all_news_data_for_batch)
            print(f"[OK] Saved {len(all_news_data_for_batch)} global news items to global_news.csv")
            csv_success = True
        except Exception as e:
            print(f"[ERROR] Error saving batch to CSV: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[WARNING] No items to save to CSV (all_news_data_for_batch is empty)")
    
    # Perform batch save to Google Sheets after processing all sources
    if all_news_data_for_batch:
        print(f"\n>> Saving {len(all_news_data_for_batch)} global news items to Google Sheets...")
        try:
            start_row = find_first_empty_row(worksheet)
            # Calculate the range to update (6 columns: Date, Country, Newspaper, Headline, Link, Summary)
            end_row = start_row + len(all_news_data_for_batch) - 1
            range_name = f"A{start_row}:F{end_row}"
            
            print(f"  Updating range: {range_name}")
            worksheet.update(range_name, all_news_data_for_batch)
            print(f"[OK] Saved {len(all_news_data_for_batch)} global news items to GlobalNews sheet (rows {start_row}-{end_row})")
            sheets_success = True
        except Exception as e:
            print(f"[ERROR] Error saving batch to Google Sheets: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[WARNING] No items to save to Google Sheets (all_news_data_for_batch is empty)")
    
    # Final status
    if all_news_data_for_batch:
        if csv_success and sheets_success:
            print(f"\n[SUCCESS] All {len(all_news_data_for_batch)} items saved to both CSV and Google Sheets")
        elif csv_success:
            print(f"\n[PARTIAL] {len(all_news_data_for_batch)} items saved to CSV, but Google Sheets save failed")
        elif sheets_success:
            print(f"\n[PARTIAL] {len(all_news_data_for_batch)} items saved to Google Sheets, but CSV save failed")
        else:
            print(f"\n[FAILURE] Failed to save {len(all_news_data_for_batch)} items to both CSV and Google Sheets")
    
    print(f"\nGlobal news crawl complete. Found {len(news_items)} items")
    return news_items


if __name__ == "__main__":
    asyncio.run(crawl_global_news())

