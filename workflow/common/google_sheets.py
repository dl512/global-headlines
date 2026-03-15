"""
Common utilities for Google Sheets operations
Handles initialization, reading, and writing to different sheets
"""

import os
import pandas as pd
import gspread
from datetime import datetime
from typing import Optional, List, Dict, Any


# Google Sheet configuration
SPREADSHEET_ID = "1oHKGMuBynXOJkkQpDTAtjfsv-jrTXpzI2jj29VCCDaM"
CREDENTIALS_FILENAME = "global-headlines-474905-9494f258e0a5.json"

# Sheet mapping for different news types
SHEET_MAPPING = {
    "global_news": "GlobalNews",
    "top_news": "TopNews",
    "financial_news": "NewsData",  # Shared sheet for top_news, financial_news, tech_news
    "market_snapshot": "Market",
    "tech_news": "NewsData",  # Shared with financial_news and top_news
    "regulatory": "Regulatory",
    "hk_ipo": "HKIPO",
    "sources": "Countries",  # Sources configuration (renamed from Sheet1)
}


def get_credentials_path() -> str:
    """Find the Google credentials file"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    workflow_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    credentials_file = os.path.join(root_dir, CREDENTIALS_FILENAME)
    
    if not os.path.exists(credentials_file):
        credentials_file = os.path.join(workflow_dir, CREDENTIALS_FILENAME)
    
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Google credentials file not found: {CREDENTIALS_FILENAME}\n"
            f"   Checked: {os.path.join(root_dir, CREDENTIALS_FILENAME)}\n"
            f"   Checked: {os.path.join(workflow_dir, CREDENTIALS_FILENAME)}"
        )
    
    return credentials_file


def get_spreadsheet():
    """Get the Google Spreadsheet object"""
    credentials_file = get_credentials_path()
    gc = gspread.service_account(filename=credentials_file)
    return gc.open_by_key(SPREADSHEET_ID)


def get_worksheet(sheet_name: str):
    """Get a specific worksheet by name, creating it if it doesn't exist"""
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Create the worksheet if it doesn't exist
        print(f"Creating new sheet: {sheet_name}")
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        # Add headers - check if it's NewsData (needs News Type column) or GlobalNews (needs Country and Newspaper)
        if sheet_name == "NewsData":
            worksheet.append_row(["Date", "Headline", "Link", "Summary", "News Type"])
        elif sheet_name == "GlobalNews":
            worksheet.append_row(["Date", "Country", "Newspaper", "Headline", "Link", "Summary"])
        else:
            worksheet.append_row(["Date", "Headline", "Link", "Summary"])
    return worksheet


def get_sources_worksheet():
    """Get the sources worksheet (Countries)"""
    return get_worksheet(SHEET_MAPPING["sources"])


def get_news_worksheet(news_type: str):
    """Get the worksheet for a specific news type"""
    sheet_name = SHEET_MAPPING.get(news_type)
    if not sheet_name:
        raise ValueError(f"Unknown news type: {news_type}")
    return get_worksheet(sheet_name)


def find_first_empty_row(worksheet) -> int:
    """Find the first empty row in a worksheet (after header)"""
    all_values = worksheet.col_values(1)
    
    if len(all_values) <= 1:
        return 2
    
    for i in range(2, len(all_values) + 2):
        if i > len(all_values):
            return len(all_values) + 1
        if not all_values[i - 1] or str(all_values[i - 1]).strip() == "":
            return i
    
    return len(all_values) + 1


def save_news_item(worksheet, headline: str, url: str, summary: str, date: Optional[datetime] = None):
    """Save a news item to a worksheet
    
    Args:
        worksheet: Google Sheet worksheet object
        headline: News headline
        url: News article URL
        summary: Article summary
        date: Date of the news (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    date_str = f"{date.day:02d}/{date.month:02d}/{date.year}"
    row_number = find_first_empty_row(worksheet)
    
    # Update cells: Date (col 1), Headline (col 2), Link (col 3), Summary (col 4)
    worksheet.update_cell(row_number, 1, date_str)
    worksheet.update_cell(row_number, 2, headline)
    worksheet.update_cell(row_number, 3, url)
    worksheet.update_cell(row_number, 4, summary)
    
    return row_number


def download_worksheet_as_dataframe(sheet_name: str) -> pd.DataFrame:
    """Download a worksheet as a pandas DataFrame"""
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        sheet_gid = str(worksheet.id)
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={sheet_gid}"
        df = pd.read_csv(url)
        
        if df.empty:
            # Return appropriate default columns based on sheet type
            if sheet_name == "GlobalNews":
                return pd.DataFrame(columns=['Date', 'Country', 'Newspaper', 'Headline', 'Link', 'Summary'])
            elif sheet_name == "NewsData":
                return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary', 'News Type'])
            else:
                return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary'])
        
        return df
    except Exception as e:
        print(f"WARNING: Error downloading {sheet_name}: {e}")
        # Return appropriate default columns based on sheet type
        if sheet_name == "GlobalNews":
            return pd.DataFrame(columns=['Date', 'Country', 'Newspaper', 'Headline', 'Link', 'Summary'])
        elif sheet_name == "NewsData":
            return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary', 'News Type'])
        else:
            return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary'])


def batch_save_news_items(worksheet, news_items: List[List[str]], start_row: int, news_type: Optional[str] = None):
    """Save multiple news items to a worksheet in a single batch update.
    
    Args:
        worksheet: Google Sheet worksheet object.
        news_items: A list of lists, where each inner list is a row of data (Date, Headline, Link, Summary, [News Type]).
        start_row: The starting row number to write data.
        news_type: Optional. The type of news if saving to a shared sheet like "NewsData".
    """
    if not news_items:
        return
    
    # Determine if 'News Type' column is needed
    if worksheet.title == "NewsData" and news_type:
        # Ensure each item has 5 columns
        for i in range(len(news_items)):
            if len(news_items[i]) == 4:  # If only 4 columns (Date, Headline, Link, Summary)
                news_items[i].append(news_type)  # Add News Type
            elif len(news_items[i]) > 5:  # Trim if too many columns
                news_items[i] = news_items[i][:5]
    
    # Calculate the range to update
    end_row = start_row + len(news_items) - 1
    range_name = f"A{start_row}:E{end_row}" if worksheet.title == "NewsData" else f"A{start_row}:D{end_row}"
    
    try:
        worksheet.update(range_name, news_items)
        print(f"✓ Saved {len(news_items)} items to {worksheet.title} (rows {start_row}-{end_row})")
    except Exception as e:
        print(f"❌ Error saving batch to {worksheet.title}: {e}")


def get_sources_list() -> List[Dict[str, str]]:
    """Get the list of sources from Countries sheet
    
    Returns:
        List of dictionaries with keys: Country, Newspaper, Website
    """
    df = download_worksheet_as_dataframe(SHEET_MAPPING["sources"])
    
    # Debug: Print column names to help identify the correct column
    if not df.empty:
        print(f"Countries sheet columns: {list(df.columns)}")
    
    sources = []
    for _, row in df.iterrows():
        # Try to get Country (column A) - check multiple possible column names
        country = None
        for col in ['Country', 'country', 'Country Name', 'CountryName']:
            if col in df.columns and pd.notna(row.get(col)):
                country = str(row.get(col, '')).strip()
                break
        
        # Try to get Newspaper (column B) - check multiple possible column names
        newspaper = None
        for col in ['Newspaper', 'newspaper', 'News Site', 'NewsSite', 'Source', 'source', 'Site Name', 'SiteName', 'Publication', 'publication']:
            if col in df.columns and pd.notna(row.get(col)):
                newspaper = str(row.get(col, '')).strip()
                break
        
        # If column B exists but we didn't find it by name, try by position (column B = index 1)
        if not newspaper and len(df.columns) > 1:
            newspaper = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        
        # Try to get Website (column C) - check multiple possible column names
        website = None
        for col in ['Website', 'website', 'URL', 'url', 'Link', 'link']:
            if col in df.columns and pd.notna(row.get(col)):
                website = str(row.get(col, '')).strip()
                break
        
        # If column C exists but we didn't find it by name, try by position (column C = index 2)
        if not website and len(df.columns) > 2:
            website = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
        
        if country and website:
            sources.append({
                'Country': country,
                'Newspaper': newspaper if newspaper else '',
                'Website': website
            })
    
    return sources

