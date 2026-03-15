"""
CSV Storage Utility
Handles saving and reading news items from CSV files
"""

import os
import csv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


# Base directory for CSV files
CSV_BASE_DIR = Path(__file__).parent.parent / "data" / "news_csv"


def ensure_csv_dir():
    """Ensure the CSV directory exists"""
    CSV_BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_csv_path(news_type: str) -> Path:
    """Get the CSV file path for a news type"""
    ensure_csv_dir()
    return CSV_BASE_DIR / f"{news_type}.csv"


def save_news_item_to_csv(news_type: str, headline: str, url: str, summary: str, date: Optional[datetime] = None):
    """Save a news item to CSV file
    
    Args:
        news_type: Type of news (e.g., "top_news", "tech_news", "financial_news", "regulatory", "hk_ipo")
        headline: News headline
        url: News article URL
        summary: Article summary
        date: Date of the news (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    # Use unambiguous English date format: "January 8, 2025"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str = f"{month_names[date.month - 1]} {date.day}, {date.year}"
    
    csv_path = get_csv_path(news_type)
    file_exists = csv_path.exists()
    
    # Prepare row data
    row_data = [date_str, headline, url, summary]
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Headline', 'Link', 'Summary'])
        writer.writerow(row_data)


def batch_save_news_items_to_csv(news_type: str, news_items: List[List[str]]):
    """Save multiple news items to CSV file in a single batch
    
    Args:
        news_type: Type of news (e.g., "top_news", "tech_news", "financial_news", "regulatory", "hk_ipo")
        news_items: List of lists, where each inner list is [date, headline, url, summary]
    """
    if not news_items:
        return
    
    csv_path = get_csv_path(news_type)
    file_exists = csv_path.exists()
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Headline', 'Link', 'Summary'])
        writer.writerows(news_items)


def save_regulatory_news_item_to_csv(stock_code: str, company: str, headline: str, url: str, summary: str, date: Optional[datetime] = None):
    """Save a regulatory announcement to CSV file with Company and Stock Code columns
    
    Args:
        stock_code: 5-digit stock code (e.g., "09988")
        company: Company name (e.g., "Alibaba")
        headline: News headline (without stock code/company prefix)
        url: News article URL
        summary: Article summary
        date: Date of the news (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    # Use unambiguous English date format: "January 8, 2025"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str = f"{month_names[date.month - 1]} {date.day}, {date.year}"
    
    csv_path = get_csv_path("regulatory")
    file_exists = csv_path.exists()
    
    # Prepare row data: Date, Stock Code, Company, Headline, Link, Summary
    row_data = [date_str, stock_code, company, headline, url, summary]
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Stock Code', 'Company', 'Headline', 'Link', 'Summary'])
        writer.writerow(row_data)


def save_futu_stock_news_item_to_csv(stock_code: str, company: str, headline: str, url: str, summary: str, date: Optional[datetime] = None):
    """Save a Futu stock news item to CSV file with Company and Stock Code columns
    
    Args:
        stock_code: 5-digit stock code (e.g., "09988")
        company: Company name (e.g., "Alibaba")
        headline: News headline (without stock code/company prefix)
        url: News article URL
        summary: Article summary
        date: Date of the news (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    # Use unambiguous English date format: "January 8, 2025"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str = f"{month_names[date.month - 1]} {date.day}, {date.year}"
    
    csv_path = get_csv_path("futu_stock_news")
    file_exists = csv_path.exists()
    
    # Prepare row data: Date, Stock Code, Company, Headline, Link, Summary
    row_data = [date_str, stock_code, company, headline, url, summary]
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Stock Code', 'Company', 'Headline', 'Link', 'Summary'])
        writer.writerow(row_data)


def save_corporate_news_item_to_csv(company: str, headline: str, url: str, summary: str, date: Optional[datetime] = None, stock_code: Optional[str] = None, source: Optional[str] = None):
    """Save a corporate news item to CSV file with Company column (unified format for all corporate news)
    
    Args:
        company: Company name (e.g., "TSMC", "NVIDIA", "Alibaba")
        headline: News headline
        url: News article URL
        summary: Article summary
        date: Date of the news (defaults to today)
        stock_code: Optional 5-digit stock code (e.g., "09988") for HK-listed stocks
        source: Optional source identifier (e.g., "regulatory", "futu", "press_release")
    """
    if date is None:
        date = datetime.now()
    
    # Use unambiguous English date format: "January 8, 2025"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str = f"{month_names[date.month - 1]} {date.day}, {date.year}"
    
    csv_path = get_csv_path("corporate_news")
    file_exists = csv_path.exists()
    
    # Prepare row data: Date, Company, Stock Code, Source, Headline, Link, Summary
    # Stock Code and Source are optional columns
    row_data = [date_str, company, stock_code or "", source or "", headline, url, summary]
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Company', 'Stock Code', 'Source', 'Headline', 'Link', 'Summary'])
        writer.writerow(row_data)


def batch_save_global_news_to_csv(news_items: List[List[str]]):
    """Save global news items to CSV file with 6 columns (Date, Country, Newspaper, Headline, Link, Summary)
    
    Args:
        news_items: List of lists, where each inner list is [date, country, newspaper, headline, url, summary]
    """
    if not news_items:
        return
    
    csv_path = get_csv_path("global_news")
    file_exists = csv_path.exists()
    
    # Write to CSV
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is new
        if not file_exists:
            writer.writerow(['Date', 'Country', 'Newspaper', 'Headline', 'Link', 'Summary'])
        writer.writerows(news_items)


def read_news_items_from_csv(news_type: str, date: Optional[datetime] = None) -> pd.DataFrame:
    """Read news items from CSV file
    
    Args:
        news_type: Type of news (e.g., "top_news", "tech_news", "financial_news", "regulatory", "hk_ipo", "global_news")
        date: Optional date to filter news (defaults to today). If None, returns all items.
    
    Returns:
        DataFrame with columns: Date, Headline, Link, Summary (or Date, Country, Newspaper, Headline, Link, Summary for global_news)
    """
    csv_path = get_csv_path(news_type)
    
    # Determine expected columns based on news_type
    if news_type == "global_news":
        expected_columns = ['Date', 'Country', 'Newspaper', 'Headline', 'Link', 'Summary']
    elif news_type == "regulatory" or news_type == "futu_stock_news":
        # Regulatory and Futu stock news have: Date, Stock Code, Company, Headline, Link, Summary
        # But handle backward compatibility with old format (Date, Headline, Link, Summary)
        expected_columns = ['Date', 'Stock Code', 'Company', 'Headline', 'Link', 'Summary']
    elif news_type == "corporate_news":
        # Corporate news has: Date, Company, Stock Code, Source, Headline, Link, Summary
        # (Stock Code and Source are optional, for backward compatibility)
        expected_columns = ['Date', 'Company', 'Stock Code', 'Source', 'Headline', 'Link', 'Summary']
    else:
        expected_columns = ['Date', 'Headline', 'Link', 'Summary']
    
    if not csv_path.exists():
        return pd.DataFrame(columns=expected_columns)
    
    # For corporate_news, handle mixed formats (old 5-column vs new 7-column format)
    if news_type == "corporate_news":
        try:
            # Read CSV line by line to handle mixed column counts
            import csv as csv_module
            rows = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv_module.reader(f)
                header = next(reader, None)  # Skip header
                for row in reader:
                    # Normalize row to 7 columns
                    if len(row) == 5:
                        # Old format: Date, Company, Headline, Link, Summary
                        # Convert to: Date, Company, Stock Code, Source, Headline, Link, Summary
                        rows.append([row[0], row[1], "", "", row[2], row[3], row[4]])
                    elif len(row) == 7:
                        # New format: Date, Company, Stock Code, Source, Headline, Link, Summary
                        rows.append(row)
                    elif len(row) > 7:
                        # Too many columns - take first 7
                        rows.append(row[:7])
                    # Skip rows with fewer than 5 columns (likely corrupted)
            df = pd.DataFrame(rows, columns=['Date', 'Company', 'Stock Code', 'Source', 'Headline', 'Link', 'Summary'])
        except Exception as e:
            print(f"WARNING: Error reading corporate_news CSV line by line: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to empty DataFrame
            df = pd.DataFrame(columns=['Date', 'Company', 'Stock Code', 'Source', 'Headline', 'Link', 'Summary'])
    
    # Skip the rest of the try block processing for corporate_news since we already handled it
    if news_type == "corporate_news":
        # Filter by date if provided
        if date is not None:
            # Generate English date format for comparison
            month_names = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"]
            today_str_english = f"{month_names[date.month - 1]} {date.day}, {date.year}"
            
            # Also check for old format (DD/MM/YYYY) for backward compatibility
            today_str_padded = f"{date.day:02d}/{date.month:02d}/{date.year}"
            today_str_unpadded = f"{date.day}/{date.month}/{date.year}"
            
            if 'Date' in df.columns:
                date_mask = (
                    (df['Date'].astype(str).str.strip().str.strip('"').str.strip("'") == today_str_english) |
                    (df['Date'].astype(str).str.strip().str.strip('"').str.strip("'") == today_str_padded) |
                    (df['Date'].astype(str).str.strip().str.strip('"').str.strip("'") == today_str_unpadded)
                )
                df = df[date_mask].copy()
        
        return df
    
    # For other news types, continue with normal processing
    else:
        # For other news types, read normally
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
        except TypeError:
            # Older pandas version
            try:
                df = pd.read_csv(csv_path, encoding='utf-8', error_bad_lines=False, warn_bad_lines=False)
            except TypeError:
                df = pd.read_csv(csv_path, encoding='utf-8')
        
        if df.empty:
            return pd.DataFrame(columns=expected_columns)
        
        # Handle backward compatibility for regulatory and futu_stock_news CSV
        # Old format: Date, Headline, Link, Summary
        # New format: Date, Stock Code, Company, Headline, Link, Summary
        if (news_type == "regulatory" or news_type == "futu_stock_news") and 'Stock Code' not in df.columns:
            # Old format detected - extract stock code and company from headline
            import re
            def extract_stock_code_and_company(headline):
                """Extract stock code and company from headline format: '{code} {company}: {title}'"""
                if pd.isna(headline) or not headline:
                    return None, None
                match = re.match(r'^(\d{5})\s+([^:]+?):\s*(.+)$', str(headline))
                if match:
                    return match.group(1), match.group(2).strip()
                return None, None
            
            df[['Stock Code', 'Company']] = df['Headline'].apply(
                lambda x: pd.Series(extract_stock_code_and_company(x))
            )
            # Reorder columns to match expected format
            df = df[['Date', 'Stock Code', 'Company', 'Headline', 'Link', 'Summary']]
        
        # Filter by date if provided
        if date is not None:
            # Generate English date format for comparison
            month_names = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"]
            today_str_english = f"{month_names[date.month - 1]} {date.day}, {date.year}"
            
            # Also check for old format (DD/MM/YYYY) for backward compatibility
            today_str_padded = f"{date.day:02d}/{date.month:02d}/{date.year}"
            today_str_unpadded = f"{date.day}/{date.month}/{date.year}"
            
            if 'Date' in df.columns:
                date_mask = (
                    (df['Date'].astype(str) == today_str_english) |
                    (df['Date'].astype(str) == today_str_padded) |
                    (df['Date'].astype(str) == today_str_unpadded)
                )
                df = df[date_mask].copy()
        
        return df

