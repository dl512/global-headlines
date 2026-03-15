"""
Market Snapshot Crawler
Fetches market data from yfinance API and saves to local JSON file
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import yfinance as yf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# List of assets to track
ASSETS = [
    {"name": "Hang Seng Index", "ticker": "^HSI", "is_index": True},
    {"name": "Hang Seng TECH Index", "ticker": "HSTECH.HK", "is_index": True},
    {"name": "S&P 500", "ticker": "^GSPC", "is_index": True},
    {"name": "Nasdaq 100", "ticker": "^NDX", "is_index": True},
    {"name": "Tencent", "ticker": "0700.HK", "is_index": False},
    {"name": "Baidu", "ticker": "9888.HK", "is_index": False},
    {"name": "JD", "ticker": "9618.HK", "is_index": False},
    {"name": "Alibaba", "ticker": "9988.HK", "is_index": False},
    {"name": "Netease", "ticker": "9999.HK", "is_index": False},
    {"name": "Kuaishou", "ticker": "1024.HK", "is_index": False},
    {"name": "Meituan", "ticker": "3690.HK", "is_index": False},
    {"name": "Xiaomi", "ticker": "1810.HK", "is_index": False},
    {"name": "BYD", "ticker": "1211.HK", "is_index": False},
    {"name": "NIO", "ticker": "9866.HK", "is_index": False},
    {"name": "Xpeng", "ticker": "9868.HK", "is_index": False},
    {"name": "Li Auto", "ticker": "2015.HK", "is_index": False},
    {"name": "Leap Motor", "ticker": "9863.HK", "is_index": False},
    {"name": "SenseTime", "ticker": "0020.HK", "is_index": False},
    {"name": "Horizon Robotics", "ticker": "9660.HK", "is_index": False},
    {"name": "Hesai", "ticker": "2525.HK", "is_index": False},
    {"name": "Seyond", "ticker": "2665.HK", "is_index": False},
    {"name": "Robosense", "ticker": "2498.HK", "is_index": False},
    {"name": "Geekplus", "ticker": "2590.HK", "is_index": False},
    {"name": "Dobot", "ticker": "2432.HK", "is_index": False},
    {"name": "Ubtech", "ticker": "9880.HK", "is_index": False},
    {"name": "Pony", "ticker": "2026.HK", "is_index": False},
    {"name": "WeRide", "ticker": "0800.HK", "is_index": False},
    {"name": "Minimax", "ticker": "0100.HK", "is_index": False},
    {"name": "Zhipu", "ticker": "2513.HK", "is_index": False},
]


def get_price_stats(ticker: str, is_index: bool = False, max_retries: int = 3, retry_delay: float = 2.0) -> Dict[str, Any]:
    """Get price statistics for a ticker with retry logic
    
    Args:
        ticker: Stock/index ticker symbol
        is_index: True if this is an index, False if it's a stock
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 2.0)
    
    Returns:
        Dictionary with price data, or None if all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get current price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('regularMarketPreviousClose')
            
            if current_price is None:
                # Try to get from history
                hist = stock.history(period="2d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
            
            # Get historical data for previous close (use 2 days to get yesterday's close)
            hist = stock.history(period="2d")
            if hist.empty:
                return None
            
            # Previous close is the second-to-last close (yesterday)
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
            else:
                prev_close = hist['Close'].iloc[-1] if len(hist) > 0 else None
            
            # Get YTD close (last trading day of previous year)
            # Get data from start of current year
            current_year = datetime.now().year
            hist_ytd = stock.history(start=f"{current_year}-01-01", end=datetime.now().strftime("%Y-%m-%d"))
            
            ytd_close = None
            if not hist_ytd.empty:
                # Get the first trading day of the year
                ytd_close = hist_ytd['Close'].iloc[0]
            else:
                # Fallback: get 1 year history and use first value
                hist_year = stock.history(period="1y")
                if not hist_year.empty:
                    ytd_close = hist_year['Close'].iloc[0]
            
            # Calculate changes
            pct_change = ((current_price - prev_close) / prev_close * 100) if prev_close else None
            ytd_change = ((current_price - ytd_close) / ytd_close * 100) if ytd_close else None
            
            # Get market cap (for stocks only, not indices)
            market_cap_usd_bn = None
            if not is_index:
                market_cap = info.get('marketCap')
                currency = info.get('currency', 'USD')
                
                if market_cap:
                    if currency == 'USD':
                        # Already in USD, no conversion needed
                        market_cap_usd_bn = market_cap / 1e9
                    else:
                        # Convert from foreign currency to USD using live exchange rate from yfinance
                        try:
                            # Fetch exchange rate using yfinance: {CURRENCY}USD=X format
                            # This gives us the rate: 1 {CURRENCY} = X USD
                            # For example: HKDUSD=X gives us how many USD per 1 HKD
                            exchange_ticker = f"{currency}USD=X"
                            exchange_stock = yf.Ticker(exchange_ticker)
                            exchange_info = exchange_stock.info
                            
                            # Try different possible fields for exchange rate
                            exchange_rate = (
                                exchange_info.get('regularMarketPrice') or
                                exchange_info.get('previousClose') or
                                exchange_info.get('ask') or
                                exchange_info.get('bid')
                            )
                            
                            if exchange_rate and exchange_rate > 0:
                                # Convert: market_cap in {currency} * exchange_rate = market_cap in USD
                                # exchange_rate is: 1 {currency} = X USD
                                market_cap_usd = market_cap * exchange_rate
                                market_cap_usd_bn = market_cap_usd / 1e9
                                print(f"    Converted {currency} to USD using rate: {exchange_rate:.4f}")
                            else:
                                # Fallback: try reverse lookup (USD{CURRENCY}=X)
                                reverse_ticker = f"USD{currency}=X"
                                reverse_stock = yf.Ticker(reverse_ticker)
                                reverse_info = reverse_stock.info
                                reverse_rate = (
                                    reverse_info.get('regularMarketPrice') or
                                    reverse_info.get('previousClose')
                                )
                                
                                if reverse_rate and reverse_rate > 0:
                                    # Reverse rate: 1 USD = X {currency}, so 1 {currency} = 1/X USD
                                    exchange_rate = 1.0 / reverse_rate
                                    market_cap_usd = market_cap * exchange_rate
                                    market_cap_usd_bn = market_cap_usd / 1e9
                                    print(f"    Converted {currency} to USD using reverse rate: {exchange_rate:.4f}")
                                else:
                                    print(f"    WARNING: Could not fetch exchange rate for {currency}, assuming USD")
                                    market_cap_usd_bn = market_cap / 1e9
                        except Exception as e:
                            print(f"    WARNING: Error fetching exchange rate for {currency}: {e}")
                            print(f"    Assuming market cap is already in USD")
                            market_cap_usd_bn = market_cap / 1e9
            
            return {
                'current_price': current_price,
                'prev_close': prev_close,
                'pct_change': pct_change,
                'ytd_change': ytd_change,
                'market_cap_usd_bn': market_cap_usd_bn
            }
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            # Check if it's a network connectivity error
            is_network_error = (
                "Failed to connect" in error_msg or
                "Could not connect" in error_msg or
                "Connection" in error_msg or
                "timeout" in error_msg.lower() or
                "curl" in error_msg.lower()
            )
            
            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = retry_delay * (2 ** attempt)
                if is_network_error:
                    print(f"  [RETRY {attempt + 1}/{max_retries}] Network error for {ticker}, retrying in {delay:.1f}s...")
                else:
                    print(f"  [RETRY {attempt + 1}/{max_retries}] Error fetching {ticker}: {error_msg[:100]}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                # Final attempt failed
                if is_network_error:
                    print(f"  [ERROR] Network connectivity issue for {ticker} after {max_retries} attempts. Please check your internet connection.")
                else:
                    print(f"  [ERROR] Failed to fetch data for {ticker} after {max_retries} attempts: {error_msg[:200]}")
                return None
    
    # Should not reach here, but just in case
    return None


def get_market_data_file_path(file_suffix: str = None) -> str:
    """Get the path to the market data JSON file
    
    Args:
        file_suffix: Optional suffix for user-specific files (e.g., "user_b" -> "market_data_user_b.json")
    
    Returns:
        Path to market data JSON file
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(script_dir, "data", "market_snapshot")
    os.makedirs(data_dir, exist_ok=True)
    
    if file_suffix:
        filename = f"market_data_{file_suffix}.json"
    else:
        filename = "market_data.json"
    
    return os.path.join(data_dir, filename)


def crawl_market_snapshot(assets: List[Dict[str, Any]] = None, output_file_suffix: str = None) -> List[Dict[str, Any]]:
    """Crawl market snapshot data and save to local JSON file
    
    Args:
        assets: Optional custom list of assets to track. If None, uses default ASSETS.
                Format: [{"name": "...", "ticker": "...", "is_index": bool}, ...]
        output_file_suffix: Optional suffix for output file (e.g., "user_b" -> "market_data_user_b.json")
    
    Returns:
        List of market data items
    """
    print("Starting market snapshot crawl...")
    
    # Use custom assets if provided, otherwise use default
    assets_to_track = assets if assets is not None else ASSETS
    
    if assets is not None:
        print(f"Using custom asset list: {len(assets_to_track)} assets")
    else:
        print(f"Using default asset list: {len(assets_to_track)} assets")
    
    if output_file_suffix:
        print(f"Output file suffix: {output_file_suffix}")
    
    market_data = []
    today = datetime.now()
    successful_count = 0
    failed_count = 0
    
    for idx, asset in enumerate(assets_to_track, 1):
        ticker = asset['ticker']
        name = asset['name']
        is_index = asset.get('is_index', False)
        
        print(f"[{idx}/{len(assets_to_track)}] Fetching data for {name} ({ticker})...")
        stats = get_price_stats(ticker, is_index=is_index)
        
        if stats:
            market_data.append({
                'name': name,
                'ticker': ticker,
                'is_index': is_index,
                'current_price': stats.get('current_price'),
                'prev_close': stats.get('prev_close'),
                'pct_change': stats.get('pct_change'),
                'ytd_change': stats.get('ytd_change'),
                'market_cap_usd_bn': stats.get('market_cap_usd_bn'),
                'date': today.strftime("%Y-%m-%d"),
                'timestamp': today.isoformat()
            })
            pct_str = f"{stats.get('pct_change'):+.2f}%" if stats.get('pct_change') is not None else "N/A"
            print(f"  [OK] {name}: {stats.get('current_price'):.2f} ({pct_str})")
            successful_count += 1
        else:
            print(f"  [FAILED] Could not fetch data for {name}")
            failed_count += 1
        
        # Add a small delay between requests to avoid overwhelming the API
        if idx < len(assets_to_track):
            time.sleep(0.5)
    
    print(f"\nSummary: {successful_count} successful, {failed_count} failed out of {len(assets_to_track)} total")
    
    # Save to local JSON file
    file_path = get_market_data_file_path(output_file_suffix)
    
    # Load existing data if it exists
    existing_data = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    
    # Append today's data
    existing_data.append({
        'date': today.strftime("%Y-%m-%d"),
        'timestamp': today.isoformat(),
        'data': market_data
    })
    
    # Save updated data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nMarket snapshot crawl complete. Found {len(market_data)} items")
    print(f"Data saved to: {file_path}")
    
    return market_data


if __name__ == "__main__":
    crawl_market_snapshot()

