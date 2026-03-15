"""
Check Global News Coverage
Analyzes the last global news crawl and lists countries where headlines were not found
"""

import sys
import os
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.google_sheets import get_sources_list, download_worksheet_as_dataframe, SHEET_MAPPING


def check_global_news_coverage():
    """Check which countries didn't get headlines in the last crawl"""
    
    print("=" * 60)
    print("Global News Coverage Check")
    print("=" * 60)
    print()
    
    # Get all expected sources from Countries sheet
    print("1. Loading expected sources from Countries sheet...")
    sources = get_sources_list()
    print(f"   Found {len(sources)} sources to crawl")
    print()
    
    # Get all countries (may have multiple sources per country)
    expected_countries = {}
    for source in sources:
        country = source.get('Country', '').strip()
        newspaper = source.get('Newspaper', '').strip()
        website = source.get('Website', '').strip()
        
        if country:
            if country not in expected_countries:
                expected_countries[country] = []
            expected_countries[country].append({
                'newspaper': newspaper,
                'website': website
            })
    
    print(f"   Found {len(expected_countries)} unique countries")
    print()
    
    # Get actual headlines from GlobalNews sheet
    print("2. Loading actual headlines from GlobalNews sheet...")
    try:
        df = download_worksheet_as_dataframe(SHEET_MAPPING["global_news"])
        print(f"   Found {len(df)} total rows in GlobalNews sheet")
    except Exception as e:
        print(f"   ERROR: Failed to load GlobalNews sheet: {e}")
        return
    
    if df.empty:
        print("   WARNING: GlobalNews sheet is empty!")
        print()
        print("=" * 60)
        print("SUMMARY: No headlines found for any country")
        print("=" * 60)
        print("\nExpected countries:")
        for country in sorted(expected_countries.keys()):
            print(f"  - {country}")
        return
    
    # Check column names
    print(f"   Columns: {list(df.columns)}")
    print()
    
    # Get the most recent date (check last few rows)
    print("3. Finding most recent crawl date...")
    
    # Try to find date column
    date_col = None
    for col in ['Date', 'date', 'DATE']:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        print("   ERROR: Could not find Date column in GlobalNews sheet")
        print(f"   Available columns: {list(df.columns)}")
        return
    
    # Get unique dates and find the most recent
    df[date_col] = df[date_col].astype(str)
    unique_dates = df[date_col].unique()
    print(f"   Found {len(unique_dates)} unique dates")
    print(f"   Recent dates: {list(unique_dates[-5:])}")
    
    # Use the most recent date (last unique date)
    most_recent_date = unique_dates[-1] if len(unique_dates) > 0 else None
    print(f"   Most recent date: {most_recent_date}")
    print()
    
    # Filter to most recent date
    df_recent = df[df[date_col] == most_recent_date].copy()
    print(f"   Found {len(df_recent)} headlines for date: {most_recent_date}")
    print()
    
    # Get countries that have headlines
    country_col = None
    for col in ['Country', 'country', 'COUNTRY']:
        if col in df.columns:
            country_col = col
            break
    
    if not country_col:
        print("   ERROR: Could not find Country column in GlobalNews sheet")
        return
    
    # Get unique countries with headlines
    countries_with_headlines = set()
    for _, row in df_recent.iterrows():
        country = str(row.get(country_col, '')).strip()
        headline = str(row.get('Headline', '')).strip() if 'Headline' in df.columns else ''
        
        # Only count if there's actually a headline
        if country and headline and headline.lower() not in ['', 'nan', 'none', 'n/a']:
            countries_with_headlines.add(country)
    
    print(f"4. Found headlines for {len(countries_with_headlines)} countries:")
    for country in sorted(countries_with_headlines):
        print(f"   [OK] {country}")
    print()
    
    # Find countries without headlines
    countries_without_headlines = set(expected_countries.keys()) - countries_with_headlines
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total expected countries: {len(expected_countries)}")
    print(f"Countries with headlines: {len(countries_with_headlines)}")
    print(f"Countries WITHOUT headlines: {len(countries_without_headlines)}")
    print()
    
    if countries_without_headlines:
        print("COUNTRIES WITHOUT HEADLINES:")
        print("-" * 60)
        for country in sorted(countries_without_headlines):
            sources = expected_countries[country]
            print(f"\n  [MISSING] {country}")
            for source in sources:
                newspaper = source['newspaper'] or 'N/A'
                website = source['website']
                print(f"      - {newspaper}: {website}")
    else:
        print("[OK] All countries have headlines!")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    check_global_news_coverage()

