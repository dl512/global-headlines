"""
Market Snapshot Summarizer
Reads from local JSON file and generates markdown table (no LLM needed - just format the data)
"""

import sys
import os
import json
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_market_data_file_path(file_suffix: str = None) -> str:
    """Get the path to the market data JSON file
    
    Args:
        file_suffix: Optional suffix for user-specific files (e.g., "user_b" -> "market_data_user_b.json")
    
    Returns:
        Path to market data JSON file
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(script_dir, "data", "market_snapshot")
    
    if file_suffix:
        filename = f"market_data_{file_suffix}.json"
    else:
        filename = "market_data.json"
    
    return os.path.join(data_dir, filename)


def load_latest_market_data(date: Optional[datetime] = None, file_suffix: str = None) -> list:
    """Load the latest market data from JSON file
    
    Args:
        date: Optional date to filter data (defaults to today)
        file_suffix: Optional suffix for user-specific files
    
    Returns:
        List of market data items
    """
    file_path = get_market_data_file_path(file_suffix)
    
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return []
        
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Find data for the specified date
        for entry in reversed(all_data):  # Start from most recent
            if entry.get('date') == date_str:
                return entry.get('data', [])
        
        # If not found, return the most recent data
        if all_data:
            return all_data[-1].get('data', [])
        
        return []
    except Exception as e:
        print(f"WARNING: Error loading market data: {e}")
        return []


def format_number(value, decimals=2):
    """Format a number with specified decimal places"""
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def format_percentage(value):
    """Format a percentage value"""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_market_cap(value):
    """Format market cap in USD billions"""
    if value is None:
        return "—"
    return f"{value:.1f}"


def summarize_market_snapshot(date: Optional[datetime] = None, file_suffix: str = None) -> str:
    """Summarize market snapshot from local JSON file
    
    Args:
        date: Optional date to filter data (defaults to today)
        file_suffix: Optional suffix for user-specific files
    
    Returns:
        Markdown formatted table
    """
    if date is None:
        date = datetime.now()
    
    # Load market data
    market_data = load_latest_market_data(date, file_suffix)
    
    if not market_data:
        return "## Market Snapshot\n\nNo market data available.\n"
    
    # Format as markdown table
    markdown = "## Market Snapshot\n\n"
    markdown += "| Asset | Ticker | Last | Chg vs prev close | YTD | Mkt cap (USD bn) |\n"
    markdown += "|---|---|---:|---:|---:|---:|\n"
    
    for item in market_data:
        name = item.get('name', '')
        ticker = item.get('ticker', '')
        current_price = item.get('current_price')
        pct_change = item.get('pct_change')
        ytd_change = item.get('ytd_change')
        market_cap = item.get('market_cap_usd_bn')
        
        # Format values
        price_str = format_number(current_price, decimals=1)
        pct_str = format_percentage(pct_change)
        ytd_str = format_percentage(ytd_change)
        mkt_cap_str = format_market_cap(market_cap)
        
        markdown += f"| {name} | {ticker} | {price_str} | {pct_str} | {ytd_str} | {mkt_cap_str} |\n"
    
    markdown += "\n*Notes: YTD is measured vs last trading close of the previous calendar year. Market cap is shown for stocks only.*\n"
    
    return markdown


if __name__ == "__main__":
    summary = summarize_market_snapshot()
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("market_snapshot", summary)
    print(f"\n✓ Summary saved to: {filepath}")

