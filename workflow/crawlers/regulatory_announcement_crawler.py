"""
Regulatory Announcement Crawler
Crawls HKEX listed company announcements with screening, PDF processing, and LLM summarization
"""

import asyncio
import sys
import os
import json
import tempfile
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
from common.csv_storage import save_regulatory_news_item_to_csv
from crawlers.hkex_listedco import fetch_hkex_announcements

# List of stock codes to track (5-digit format)
STOCK_CODES = [
    "09988",  # Alibaba
    "00700",  # Tencent
    "09888",  # Baidu
    "09618",  # JD
    "09999",  # Netease
    "01024",  # Kuaishou
    "03690",  # Meituan
    "01810",  # Xiaomi
    "01211",  # BYD
    "09866",  # NIO
    "09868",  # Xpeng
    "02015",  # Li Auto
    "09863",  # Leap Motor
    "00020",  # SenseTime
    "09660",  # Horizon Robotics
    "02525",  # Hesai
    "02665",  # Seyond
    "02498",  # Robosense
    "02590",  # Geekplus
    "02432",  # Dobot
    "09880",  # Ubtech
    "02026",  # Pony
    "00800",  # WeRide
    "01021",  # Huayan Robotics
    "00100",  # Minimax
    "02513",  # Zhipu
    "01347",  # Hua Hong
    "00981",  # SMIC
    "06082",  # Biren
]


def prescreen(title: str) -> bool:
    """Prescreen to exclude daily filings like 'Next Day Disclosure Return'"""
    if 'Next Day Disclosure Return' in title:
        return False
    return True


async def is_relevant(client, title: str) -> bool:
    """Use LLM to check if announcement is relevant"""
    prompt = f"""
You are a research analyst who is good at screening out minor and irrelevant news of a company by reading the title of an announcement.

IMPORTANT - These are ALWAYS RELEVANT (capital market activities):
- Share subscriptions (including subscription of new shares, domestic shares, etc.)
- Share placements, share issues, share allotments
- Fundraising activities (rights issues, private placements, etc.)
- Capital market transactions
- Major corporate actions affecting share capital

NOT RELEVANT (routine filings):
- Regular returns (e.g., Next Day Disclosure Returns)
- Proxy statements
- Amendments to articles of association (unless related to capital changes)
- Routine administrative filings

Given the title of the announcement: {title}, please output only 'relevant' or 'irrelevant'
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        
        result = response.choices[0].message.content.strip().lower()
        return result == "relevant"
    except Exception as e:
        print(f"    WARNING: Error checking relevance: {e}")
        return True  # Default to relevant if check fails


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file using PyPDF2 or fallback method"""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        # Fallback: try pdfplumber
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            # Last resort: return empty and let LLM handle URL directly
            print("    WARNING: No PDF library available (PyPDF2 or pdfplumber). Will summarize from URL only.")
            return ""


async def generate_pdf_summary(client, url: str) -> str:
    """Download PDF, extract text, generate summary, and delete PDF"""
    pdf_path = None
    try:
        # Download PDF to temporary file
        print(f"    Downloading PDF from {url}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
        
        # Extract text from PDF
        print(f"    Extracting text from PDF...")
        pdf_text = extract_text_from_pdf(pdf_path)
        
        if not pdf_text or len(pdf_text.strip()) < 100:
            # If PDF extraction failed, use LLM to summarize from URL
            print(f"    PDF extraction failed or too short, summarizing from URL...")
            prompt = f"""
Given this regulatory announcement PDF URL: {url}

Please provide a concise summary (4-8 bullet points) of the key information in this announcement.
Focus on:
- Main corporate action or development
- Financial details (if fundraising: placing price, discount to closing price, net proceeds, % of issued shares, placing agents/underwriters)
- Key dates and deadlines
- Material information for investors

Avoid legal jargon. Be concise and clear.
"""
        else:
            # Limit text length for LLM
            if len(pdf_text) > 15000:
                pdf_text = pdf_text[:15000] + "..."
            
            prompt = f"""
Given this regulatory announcement PDF content:

{pdf_text}

Please provide a concise summary (4-8 bullet points) of the key information in this announcement.
Focus on:
- Main corporate action or development
- Financial details (if fundraising: placing price, discount to closing price, net proceeds, % of issued shares, placing agents/underwriters)
- Key dates and deadlines
- Material information for investors

Avoid legal jargon. Be concise and clear.
"""
        
        # Generate summary using LLM
        print(f"    Generating summary with LLM...")
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"    WARNING: Error processing PDF: {e}")
        return f"Summary not available (Error: {str(e)})"
    finally:
        # Delete PDF file
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"    Deleted temporary PDF file")
            except Exception as e:
                print(f"    WARNING: Could not delete PDF file: {e}")


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


async def crawl_regulatory_announcements(dates: List[str] = None) -> List[Dict[str, Any]]:
    """Crawl HKEX regulatory announcements with screening and PDF summarization
    
    Args:
        dates: List of dates in DD/MM/YYYY format to filter announcements (defaults to today and previous trading day)
    
    Returns:
        List of announcement items
    """
    print("Starting regulatory announcement crawl...")
    
    # Get trading dates if not provided
    if dates is None:
        dates = get_trading_dates()
    
    print(f"Filtering for dates: {dates}")
    print(f"Tracking stock codes: {len(STOCK_CODES)} codes")
    
    client = initialize_openai_client()
    
    # Fetch all announcements for the date range
    print("Fetching announcements from HKEX...")
    all_announcements = await fetch_hkex_announcements(dates=dates)
    print(f"Found {len(all_announcements)} total announcements for date range")
    
    # Step 1: Filter by stock codes
    print("Step 1: Filtering by stock codes...")
    filtered_by_code = [
        ann for ann in all_announcements 
        if ann.get('code', '').replace('.HK', '').zfill(5) in STOCK_CODES
    ]
    print(f"  Found {len(filtered_by_code)} announcements matching stock codes")
    
    # Step 2: Prescreen to exclude daily filings
    print("Step 2: Prescreening to exclude daily filings...")
    prescreened = [
        ann for ann in filtered_by_code 
        if prescreen(ann.get('title', ''))
    ]
    print(f"  Found {len(prescreened)} announcements after prescreening")
    
    # Step 3: Check relevance with LLM
    print("Step 3: Checking relevance with LLM...")
    relevant_announcements = []
    for i, ann in enumerate(prescreened, 1):
        title = ann.get('title', '')
        print(f"  [{i}/{len(prescreened)}] Checking: {title[:60]}...")
        if await is_relevant(client, title):
            relevant_announcements.append(ann)
            print(f"    ✓ Relevant")
        else:
            print(f"    ✗ Irrelevant")
    
    print(f"  Found {len(relevant_announcements)} relevant announcements")
    
    # Step 4: Process each relevant announcement (download PDF, summarize, save)
    print("\nStep 4: Processing announcements (downloading PDFs, generating summaries)...")
    regulatory_items = []
    
    for i, ann in enumerate(relevant_announcements, 1):
        code = ann.get('code', '')
        company = ann.get('company', '')
        title = ann.get('title', '')
        url = ann.get('link', '')
        
        print(f"\n  [{i}/{len(relevant_announcements)}] Processing: {code} {company}")
        print(f"    Title: {title[:80]}...")
        
        # Generate headline (without stock code/company prefix for cleaner storage)
        headline = title
        
        # Generate summary from PDF
        summary = ""
        if url and url.endswith('.pdf'):
            summary = await generate_pdf_summary(client, url)
        else:
            print(f"    WARNING: No PDF link found, skipping summary generation")
            summary = f"Category: {ann.get('category', '')} | Date: {ann.get('date', '')} {ann.get('time', '')}"
        
        # Parse date for saving
        date_str = ann.get('date', '')
        try:
            if date_str:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            else:
                date_obj = datetime.now()
        except:
            date_obj = datetime.now()
        
        # Normalize stock code to 5-digit format
        stock_code_5digit = code.replace('.HK', '').zfill(5)
        
        # Save to CSV with separate Company and Stock Code columns
        try:
            save_regulatory_news_item_to_csv(stock_code_5digit, company, headline, url, summary, date=date_obj)
            print(f"    ✓ Saved to regulatory.csv (Code: {stock_code_5digit}, Company: {company})")
        except Exception as e:
            print(f"    WARNING: Failed to save to CSV: {e}")
        
        regulatory_items.append({
            'date': date_obj,
            'stock_code': stock_code_5digit,
            'company': company,
            'headline': headline,
            'link': url,
            'summary': summary,
            'raw_data': ann
        })
    
    print(f"\nRegulatory announcement crawl complete. Found {len(regulatory_items)} items")
    return regulatory_items


if __name__ == "__main__":
    asyncio.run(crawl_regulatory_announcements())

