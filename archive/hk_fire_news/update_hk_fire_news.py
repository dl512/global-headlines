"""
Hong Kong Fire News Updater
This script searches for news related to the recent fire incident in Hong Kong from news websites and updates Sheet2.
Run this script to collect coverage of the Hong Kong fire incident from various news sources.

Features fallback to MCP scraper if traditional extraction fails.
"""

import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import sys
import os

# Add workflow directory to path for imports
workflow_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
sys.path.insert(0, workflow_dir)

import extract_html
import gspread
import json
import mcp_scraper
from openai import OpenAI
import os
import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm


# Load environment variables
load_dotenv(override=True)


class Headline(BaseModel):
    """Pydantic model for structured headline output from OpenAI"""
    headline: str
    link: str


def initialize_openai_client():
    """Initialize and return OpenAI client"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_base_url = os.getenv('BASE_URL')
    
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    return OpenAI(
        base_url=openai_base_url,
        api_key=openai_api_key,
    )


def download_google_sheet():
    """Download Sheet2 from Google Sheet as a DataFrame"""
    spreadsheet_id = "1oHKGMuBynXOJkkQpDTAtjfsv-jrTXpzI2jj29VCCDaM"
    
    # Get Sheet2's gid using gspread
    credentials_file = os.path.join(
        os.path.dirname(__file__),
        "global-headlines-474905-9494f258e0a5.json"
    )
    
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Google credentials file not found: {credentials_file}")
    
    gc = gspread.service_account(filename=credentials_file)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet("Sheet2")
    
    # Get the gid (worksheet ID) for Sheet2
    sheet_gid = str(worksheet.id)
    
    # Download as CSV using the gid
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_gid}"
    df = pd.read_csv(url)
    return df


def initialize_google_sheet():
    """Initialize and return Google Sheet worksheet (Sheet2)"""
    credentials_file = os.path.join(
        os.path.dirname(__file__),
        "global-headlines-474905-9494f258e0a5.json"
    )
    
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Google credentials file not found: {credentials_file}")
    
    gc = gspread.service_account(filename=credentials_file)
    spreadsheet_id = "1oHKGMuBynXOJkkQpDTAtjfsv-jrTXpzI2jj29VCCDaM"
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet("Sheet2")
    
    return worksheet


def find_row_number(df, country, website):
    """Find the row number for a specific country and website in the spreadsheet"""
    # Match both country and website URL
    matching_rows = df[(df['Country'] == country) & (df['Website'] == website)]
    if len(matching_rows) > 0:
        row_number = matching_rows.index[0]
        return row_number + 2  # Adding 2 for 0-indexing and header
    return None


def remove_html_tags(html_content):
    """Remove HTML tags and return clean text"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()




def extract_links_from_html(html_string):
    """Extract all links from HTML and format them for LLM matching"""
    soup = BeautifulSoup(html_string, "html.parser")
    
    # Extract all links
    links = {}
    for a in soup.find_all('a'):
        link_text = a.get_text().strip()
        link_url = a.get('href', '')
        if link_text and link_url:
            links[link_text] = link_url
    
    # Format links for LLM
    links_on_page = ""
    for link_text, url in links.items():
        links_on_page += f" [{link_text}]({url})"
    
    return links_on_page


def match_headline_to_link(client, headline, links_on_page, website, use_gpt4o=False):
    """Use LLM to match headline to corresponding link"""
    # Truncate links_on_page to avoid exceeding token limits
    truncated_links = links_on_page[:150000]
    
    prompt = f'''
    Given this identified headline on a news website: "{headline}"
    Note that the headline is being translated into English if the original text is non-English.
    Please check if the link to that headline is in {truncated_links}
    If so, please output only the link. 
    Note that sometime only the relative url is included. If so, you need to output the absolute url with the root website {website}.
    If no link is founded, just output 'N/A'
    Do not output anything else other than the link
    Do not output any html tags e.g., '<a href=', '</a>'
    '''
    
    model = "openai/gpt-4o" if use_gpt4o else "openai/gpt-4o-mini"
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()


def extract_content_from_link(link):
    """Extract content from a link to test if it's accessible"""
    try:
        html_dict = extract_html.get_raw_html(link)
        if html_dict and html_dict.get("html"):
            return html_dict["html"]
        return None
    except Exception as e:
        print(f"  ⚠️  Error accessing link {link}: {e}")
        return None


def summarize_content(client, headline, content_html):
    """Summarize content using LLM"""
    clean_text = remove_html_tags(content_html)
    
    prompt = f'''
    You are a capable journalist. This is the headline of today: {headline}
    Please summarize in 2-3 English bullets to capture the key information. Each bullet should be very concise.
    The source may not be in English. But make sure the summary is in English.
    
    IMPORTANT: When referring to Donald Trump, always refer to him as "President Donald Trump" or "US President Donald Trump". He is the CURRENT President of the United States as of 2025. Do NOT label him as "Former President" or "Ex-President" - this is incorrect.
    '''
    
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()


def is_legit(client, input_type, input_item):
    """Check if a headline or link is legitimate using OpenAI"""
    
    # Quick pre-checks before calling API (saves costs)
    if input_type == "headline title":
        # Immediate rejections for obvious invalid headlines
        invalid_keywords = [
            "just a moment", "please wait", "loading", "error", "not found",
            "access denied", "access blocked", "request rejected", "captcha",
            "verify you are human", "cloudflare", "security check", "security challenge",
            "unable to access", "not accessible", "blocked", "verification",
            "cookies", "subscribe", "sign up", "newsletter",
            "headline of the day", "breaking news", "latest updates",
            "welcome to", "homepage", "no headline found",
            "security", "challenge", "protection"
        ]
        
        item_lower = input_item.lower().strip()
        
        # Check for obvious invalid patterns
        if len(item_lower) < 10:  # Too short to be a real headline
            return "N"
        
        if any(keyword in item_lower for keyword in invalid_keywords):
            return "N"
        
    
    elif input_type == "website":
        # Quick check for invalid links
        if not input_item or input_item.strip() in ["#", "", "javascript:void(0)", "N/A"]:
            return "N"
        if not input_item.startswith(("http://", "https://")):
            return "N"
        
        # Test if link is accessible by trying to extract content
        content = extract_content_from_link(input_item)
        if content is None:
            return "N"
    
    # If passed pre-checks, use AI for more nuanced validation
    if input_type == "headline title":
        prompt = f'''
        Check if this is a VALID news headline about the Hong Kong election recently: "{input_item}"
        
        Output "N" if it is any of these:
        - Loading messages (e.g., "Just a Moment...", "Please wait...", "Loading...")
        - Error messages (e.g., "Request Rejected", "Error 404", "Page not found")
        - Access/security messages (e.g., "Access Blocked", "Access Denied", "Captcha required")
        - Cloudflare/bot protection messages (e.g., "Unable to access due to Cloudflare", "Security challenge", "Cloudflare verification", "Unable to access due to security")
        - Website blocking messages (e.g., "Unable to access", "Not accessible due to", "Request rejected")
        - Generic site names or descriptions (e.g., "News from [Site]", "Welcome to [Site]", "[Site] Homepage")
        - Template/placeholder text (e.g., "Headline of the Day", "Breaking News", "Latest Updates")
        - Navigation elements (e.g., "Home", "About", "Contact Us", "Menu")
        - Cookie/privacy notices (e.g., "We use cookies", "Accept cookies", "Privacy Policy")
        - Subscription prompts (e.g., "Subscribe now", "Sign up for newsletter")
        - Empty or very short generic text (less than 10 characters)
        - Bot protection messages (e.g., "Verify you are human", "Cloudflare", "Security check")
        - "No headline found" or similar error messages
        - Any text that indicates technical problems accessing the website
        - NOT related to the Hong Kong election 
        
        Output "Y" ONLY if it is:
        - A specific, actual news story about the Hong Kong election
        - Contains substantive information about the election in Hong Kong
        - Reads like an actual news article headline about the Hong Kong election (who, what, where, when)
        - Written in proper English with correct grammar and spelling (or translated to English)
        
        CRITICAL: The headline MUST be related to the recent election in Hong Kong. Reject any headline that is not about this topic.
        Reject ANY headline that mentions "Cloudflare", "security challenge", "unable to access", "not accessible", or similar technical error messages.
        
        Think carefully. Be strict. Most system messages, errors, generic text, and unrelated content should be rejected.
        
        Output only "Y" or "N".
        '''
    
    elif input_type == "website":
        prompt = f'''
        Check if this is a VALID website URL/link: "{input_item}"
        
        Output "N" if:
        - It's just a symbol (e.g., "#", "javascript:void(0)")
        - It's empty or just whitespace
        - It's a relative path without domain (e.g., "/news", "/article")
        - It's a javascript: link
        - It's clearly not a URL
        
        Output "Y" if:
        - It's a full HTTP/HTTPS URL
        - It appears to be a valid news article link
        
        Output only "Y" or "N".
        '''
    else:
        prompt = f'''
        Check if "{input_item}" is a legit {input_type}.
        Output only "Y" or "N".
        '''
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error validating {input_type}: {e}")
        return "N"  # Default to INVALID if validation fails (safer)


def extract_hk_fire_news(client, website, html_dict, model="openai/gpt-4o-mini"):
    """Extract news about Hong Kong fire incident from HTML using specified model (Method 1) - headline only"""
    html_string = html_dict["html"]
    clean_text = remove_html_tags(html_string)

    # Keep HTML tags if size is not too large for better context
    if len(html_string) > 200000:
        html_string_input = clean_text
    else:
        html_string_input = html_string

    prompt = f'''
    You are good at reading html text, visualize the content, and identifying news articles.
    Given this HTML text from a news website: {html_string_input}
    
    CRITICAL REQUIREMENTS:
    1. Search for any news article related to the recent fire incident in Hong Kong
    2. This is a very recent incident - look for breaking news or recent coverage about a fire in Hong Kong
    3. If you find such news, identify the headline of that article
    4. ALWAYS translate to English if the headline is in any other language
    5. Output ONLY the English headline text, nothing else
    6. Do not include any non-English words or phrases
    7. Ensure the headline is in proper English grammar and spelling
    8. If the headline contains any non-English characters or words, translate them to English
    9. If NO news about the Hong Kong fire is found on this page, output "No Hong Kong fire news found"
    
    IMPORTANT: The output must be 100% in English. Only return a headline if it's about the Hong Kong fire incident. If you cannot find any news about the Hong Kong fire, output "No Hong Kong fire news found".
    '''

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    headline = response.choices[0].message.content.strip()
    
    # Check if no news was found
    if "No Hong Kong fire news found" in headline or headline == "":
        return {"headline": "", "link": ""}
    
    # Validate headline
    headline_valid = is_legit(client, "headline title", headline)
    if headline_valid == "N":
        print(f"  ⚠️  Invalid headline rejected: '{headline}'")
        headline = ""
    
    return {"headline": headline, "link": ""}


async def extract_headline_with_mcp(website):
    """Extract headline using MCP scraper (Method 2 - Fallback)"""
    try:
        print(f"  🔄 Trying MCP scraper (headless mode)...")
        headline_info = await mcp_scraper.scrape_website(
            url=website,
            headless=True
        )
        
        # Check if the headline is about Hong Kong fire
        if headline_info.get("headline"):
            # Use LLM to check if it's about Hong Kong fire
            client = initialize_openai_client()
            prompt = f'''
            Check if this headline is about the recent fire incident in Hong Kong: "{headline_info['headline']}"
            Output "Y" if it's about the Hong Kong fire, "N" if it's not.
            Output only "Y" or "N".
            '''
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            is_about_hk_fire = response.choices[0].message.content.strip() == "Y"
            
            if not is_about_hk_fire:
                return {"headline": "", "link": website}
        
        return headline_info
    except Exception as e:
        print(f"  ❌ MCP scraper failed: {e}")
        return {"headline": "", "link": website}


async def extract_headline_with_fallback(client, website, html_dict, model="openai/gpt-4o-mini", use_mcp=True):
    """
    Extract Hong Kong fire news with fallback strategy:
    1. Try traditional method (HTML + LLM) - headline only
    2. Extract links from HTML and match to headline
    3. If invalid and use_mcp=True, try MCP with Playwright (browser automation)
    
    Args:
        use_mcp: If True, fallback to MCP when traditional method fails. If False, only use traditional method.
    """
    
    # Method 1: Traditional extraction (headline only)
    print(f"  📝 Method 1: Traditional HTML extraction (searching for Hong Kong fire news) using {model}...")
    try:
        headline_info = extract_hk_fire_news(client, website, html_dict, model)
        
        # Check if we got valid headline
        if headline_info["headline"] and headline_info["headline"].strip():
            print("  ✅ Method 1 extracted headline successfully!")
            
            # Now extract and match links
            print("  🔗 Extracting and matching links...")
            links_on_page = extract_links_from_html(html_dict["html"])
            
            # Try matching link with retry
            matched_link = match_headline_to_link(client, headline_info["headline"], links_on_page, website)
            
            # If first attempt fails, try once more with GPT-4o
            if not matched_link or matched_link == "N/A":
                print("  🔄 First link matching failed, trying again with GPT-4o...")
                matched_link = match_headline_to_link(client, headline_info["headline"], links_on_page, website, use_gpt4o=True)
            
            if matched_link and matched_link != "N/A":
                print(f"  ✅ Found matching link: {matched_link}")
                headline_info["link"] = matched_link
                
                # Validate the matched link
                link_valid = is_legit(client, "website", matched_link)
                if link_valid == "N":
                    print(f"  ⚠️  Matched link is not accessible: {matched_link}")
                    headline_info["link"] = ""
                else:
                    print("  ✅ Link is accessible!")
            else:
                print("  ⚠️  No matching link found after 2 attempts, leaving link empty")
                headline_info["link"] = ""
            
            headline_info['method'] = 1
            return headline_info
        else:
            print("  ⚠️  Method 1 found no Hong Kong fire news", end="")
            if use_mcp:
                print(", trying MCP Playwright fallback...")
            else:
                print(", no fallback method configured.")
                return {"headline": "", "link": "", "method": 0}
    except Exception as e:
        print(f"  ❌ Method 1 failed: {e}", end="")
        if use_mcp:
            print(", trying MCP Playwright fallback...")
        else:
            print(", no fallback method configured.")
            return {"headline": "", "link": "", "method": 0}
    
    # Method 2: MCP with Playwright (browser automation) - only if use_mcp=True
    if use_mcp:
        print("  📝 Method 2: MCP with Playwright (browser automation)...")
        try:
            headline_info = await extract_headline_with_mcp(website)
            
            if headline_info["headline"] and headline_info["headline"].strip():
                # Validate headline using is_legit check
                headline_valid = is_legit(client, "headline title", headline_info["headline"])
                if headline_valid == "N":
                    print(f"  ⚠️  Invalid MCP headline rejected: '{headline_info['headline']}'")
                    print("  ❌ Both methods failed to extract headline")
                    return {"headline": "", "link": "", "method": 0}
                
                print("  ✅ Method 2 succeeded!")
                headline_info['method'] = 2
                return headline_info
            else:
                print("  ❌ Both methods failed to extract headline")
                return {"headline": "", "link": "", "method": 0}
        except Exception as e:
            print(f"  ❌ Method 2 failed: {e}")
            return {"headline": "", "link": "", "method": 0}
    else:
        return {"headline": "", "link": "", "method": 0}


def save_to_spreadsheet(worksheet, df, country, website, headline_info, summary=""):
    """Save headline information to Sheet2"""
    row_number = find_row_number(df, country, website)
    
    if not row_number:
        print(f"Row not found for Country '{country}' and Website '{website}' in spreadsheet")
        return
    
    date_column_number = 4
    headline_column_number = 5
    link_column_number = 6
    summary_column_number = 7  # Column G
    
    # Use DD/MM/YYYY format (e.g., 19/11/2025) to match newsletter generator
    today_obj = datetime.now()
    today = f"{today_obj.day:02d}/{today_obj.month:02d}/{today_obj.year}"
    
    worksheet.update_cell(row_number, date_column_number, today)
    worksheet.update_cell(row_number, headline_column_number, headline_info["headline"])
    worksheet.update_cell(row_number, link_column_number, headline_info["link"])
    worksheet.update_cell(row_number, summary_column_number, summary)


async def process_countries_pass(client, df, worksheet, countries, model, pass_number, use_mcp=True):
    # Note: countries parameter is kept for compatibility but not used - we iterate through all rows
    """Process countries for a single pass with specified model"""
    successful = 0
    failed = 0
    skipped = 0
    invalid_headlines = 0
    invalid_links = 0
    method_1_success = 0
    method_2_success = 0
    countries_without_headlines = []  # For backward compatibility in return dict
    failed_row_indices = []  # Track actual row indices that failed
    
    print(f"\n{'='*80}")
    print(f"PASS {pass_number}: Processing rows with {model}")
    if not use_mcp:
        print(f"MCP fallback: DISABLED (traditional method only)")
    print(f"{'='*80}")
    
    # For Sheet2, iterate through all rows (not just unique countries)
    # since one country can have multiple websites
    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Pass {pass_number} - Processing rows"):
        try:
            country = row['Country']
            website = row['Website']
            
            # Skip if no country or website
            if pd.isna(country) or country == "" or pd.isna(website) or website == "":
                skipped += 1
                continue
            
            print(f"\n{'='*60}")
            print(f"Processing: {country}")
            print(f"Website: {website}")
            print('='*60)
            
            # Extract HTML
            html_dict = extract_html.get_raw_html(website)
            
            if not html_dict:
                if use_mcp:
                    print(f"  ❌ Failed to retrieve HTML, trying MCP fallback...")
                else:
                    print(f"  ❌ Failed to retrieve HTML")
                html_dict = {"html": ""}  # Empty dict for MCP fallback
            
            # Extract headline with fallback
            headline_info = await extract_headline_with_fallback(client, website, html_dict, model, use_mcp=use_mcp)
            
            # Track which method succeeded
            if headline_info.get('method') == 1:
                method_1_success += 1
            elif headline_info.get('method') == 2:
                method_2_success += 1
            
            # Track rejections - store both country (for compatibility) and row index (for precise retry)
            if headline_info['headline'] == "":
                invalid_headlines += 1
                countries_without_headlines.append(country)  # For backward compatibility
                failed_row_indices.append(idx)  # Track actual row index for precise retry
            if headline_info['link'] == website:
                invalid_links += 1
            
            print(f"\n  📰 Final Headline: {headline_info['headline']}")
            print(f"  🔗 Final Link: {headline_info['link']}")
            
            # Generate summary if both headline and link are valid
            summary = ""
            
            # Check if MCP already provided a summary
            if headline_info.get('summary') and headline_info['summary'].strip():
                summary = headline_info['summary']
                print(f"  ✅ Using MCP-generated summary: {summary[:100]}...")
            elif (headline_info['headline'] and headline_info['headline'].strip() and 
                  headline_info['link'] and headline_info['link'] != website):
                
                print("  📝 Generating content summary...")
                try:
                    # Extract content from the link
                    content_html = extract_content_from_link(headline_info['link'])
                    if content_html:
                        summary = summarize_content(client, headline_info['headline'], content_html)
                        print(f"  ✅ Summary generated: {summary[:100]}...")
                    else:
                        print("  ⚠️  Could not extract content for summary")
                except Exception as e:
                    print(f"  ⚠️  Error generating summary: {e}")
            
            # Save to spreadsheet (pass both country and website to find correct row)
            save_to_spreadsheet(worksheet, df, country, website, headline_info, summary)
            successful += 1
            
        except Exception as e:
            print(f"  ❌ Failed to extract and save headline for {country}: {str(e)}")
            failed += 1
            countries_without_headlines.append(country)
    
    return {
        'successful': successful,
        'failed': failed,
        'skipped': skipped,
        'invalid_headlines': invalid_headlines,
        'invalid_links': invalid_links,
        'method_1_success': method_1_success,
        'method_2_success': method_2_success,
        'countries_without_headlines': countries_without_headlines,  # For backward compatibility
        'failed_row_indices': failed_row_indices,  # Actual row indices that failed
    }


async def process_countries(client, df, worksheet, quick_run=False):
    """Process all rows with single pass"""
    print(f"\n{'='*80}")
    if quick_run:
        print("SINGLE PASS MODE (Traditional scraping ONLY, no MCP)")
    else:
        print("SINGLE PASS MODE (Traditional scraping + MCP fallback)")
    print(f"{'='*80}")
    print("Processing all rows with GPT-4o-mini")
    if not quick_run:
        print("MCP fallback enabled for failed extractions")
    print(f"{'='*80}")
    
    # Single pass: Process all rows with GPT-4o-mini
    results = await process_countries_pass(
        client, df, worksheet, None,  # countries parameter not used anymore
        model="openai/gpt-4o-mini", 
        pass_number=1,
        use_mcp=not quick_run  # Use MCP fallback if not quick run
    )
    
    return results


async def update_hk_fire_news_async(quick_run=False):
    """Async wrapper for updating Hong Kong fire news (can be called from other async contexts)"""
    print("=" * 80)
    if quick_run:
        print("Hong Kong Fire News Updater (QUICK RUN - No MCP)")
    else:
        print("Hong Kong Fire News Updater (with MCP Fallback)")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize services
    print("Initializing OpenAI client...")
    client = initialize_openai_client()
    
    print("Downloading Google Sheet data...")
    df = download_google_sheet()
    
    print("Connecting to Google Sheet (Sheet2)...")
    worksheet = initialize_google_sheet()
    
    # Count total rows to process
    total_rows = len(df)
    print(f"Found {total_rows} rows to process")
    print()
    
    # Process all rows
    results = await process_countries(client, df, worksheet, quick_run=quick_run)
    
    # Print summary
    print()
    print("=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Total rows: {len(df)}")
    print(f"Successfully updated: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Skipped (no website): {results['skipped']}")
    print()
    
    print("Extraction Methods:")
    print(f"  Method 1 (Traditional HTML + LLM): {results['method_1_success']}")
    print(f"  Method 2 (MCP + Playwright): {results['method_2_success']}")
    print()
    
    print("Validation Results:")
    print(f"  Invalid headlines rejected: {results['invalid_headlines']}")
    print(f"  Invalid links rejected: {results['invalid_links']}")
    print()
    print("Workflow Features:")
    print("  • Single pass processing with GPT-4o-mini")
    if not quick_run:
        print("  • MCP Playwright fallback available for failed extractions")
    print("  • Searching for Hong Kong fire news instead of main headlines")
    print("  • Headlines extracted separately from links")
    print("  • Links matched using LLM analysis")
    print("  • Link accessibility tested before validation")
    print("  • Content summaries generated for valid articles")
    print("  • Summaries saved to column G")
    print("  • Data saved to Sheet2")
    print()
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return results


def main():
    """Main function to update all Hong Kong fire news"""
    import sys
    
    # Check for quick run flag
    quick_run = '--quick' in sys.argv or '-q' in sys.argv
    
    # Process countries with async support
    asyncio.run(update_hk_fire_news_async(quick_run=quick_run))


if __name__ == "__main__":
    main()

