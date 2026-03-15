"""
Tech Stock Regulatory Announcement Summarizer
Reads from Regulatory CSV and filters by stock codes to generate summary for tech stocks only
Excludes semiconductor stocks (Hua Hong, SMIC, Biren)
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client
from common.csv_storage import read_news_items_from_csv


def get_today_dates(date: datetime) -> dict:
    """Get today's date in both DD/MM/YYYY and English format"""
    # DD/MM/YYYY format
    date_str_ddmm = f"{date.day:02d}/{date.month:02d}/{date.year}"
    
    # English format: "January 23, 2026"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    date_str_english = f"{month_names[date.month - 1]} {date.day}, {date.year}"
    
    return {
        'today_ddmm': date_str_ddmm,
        'today_english': date_str_english
    }


def filter_by_stock_codes(df, stock_codes: List[str]) -> 'pd.DataFrame':
    """Filter DataFrame to only include rows where Stock Code matches one of the provided codes"""
    import pandas as pd
    
    if df.empty:
        return df
    
    # Check if CSV has the new format with Stock Code column
    if 'Stock Code' in df.columns:
        # New format: filter by Stock Code column directly
        filtered = df[df['Stock Code'].isin(stock_codes)].copy()
    elif 'Company' in df.columns:
        # Fallback: if Company column exists but Stock Code doesn't, extract from headline
        # This handles edge cases during migration
        def extract_stock_code_from_headline(headline: str) -> Optional[str]:
            if not headline:
                return None
            match = re.match(r'^(\d{5})\s+', str(headline))
            if match:
                return match.group(1)
            return None
        
        df['_stock_code'] = df['Headline'].apply(extract_stock_code_from_headline)
        filtered = df[df['_stock_code'].isin(stock_codes)].copy()
        filtered = filtered.drop(columns=['_stock_code'])
    else:
        # Old format: extract from headline (backward compatibility)
        def extract_stock_code_from_headline(headline: str) -> Optional[str]:
            if not headline:
                return None
            match = re.match(r'^(\d{5})\s+', str(headline))
            if match:
                return match.group(1)
            return None
        
        df['_stock_code'] = df['Headline'].apply(extract_stock_code_from_headline)
        filtered = df[df['_stock_code'].isin(stock_codes)].copy()
        filtered = filtered.drop(columns=['_stock_code'])
    
    return filtered


async def summarize_tech_stock_regulatory_announcements(
    date: Optional[datetime] = None,
    stock_codes: Optional[List[str]] = None,
    company_names: Optional[List[str]] = None
) -> str:
    """Summarize tech stock regulatory announcements from Regulatory CSV using LLM
    
    Args:
        date: Optional date to filter announcements (defaults to today)
        stock_codes: List of 5-digit stock codes to include (defaults to tech stocks excluding semiconductors)
    
    Returns:
        Markdown formatted summary
    """
    if date is None:
        date = datetime.now()
    
    date_formats = get_today_dates(date)
    
    # Read data from CSV (no date filter, we'll filter manually)
    df = read_news_items_from_csv("regulatory", date=None)
    
    if df.empty:
        return "## Tech Stock Regulatory Announcements\n\nNo regulatory announcements for today.\n"
    
    # Filter by date - only include today
    # Convert Date column to string and strip quotes/spaces for comparison
    df['Date'] = df['Date'].astype(str).str.strip().str.strip('"').str.strip("'")
    
    # Check for dates in both DD/MM/YYYY and English formats
    date_matches = (
        (df['Date'] == date_formats['today_ddmm']) |
        (df['Date'] == date_formats['today_english'])
    )
    
    df_filtered = df[date_matches].copy()
    
    print(f"Filtering regulatory announcements for today's date:")
    print(f"  Today: {date_formats['today_ddmm']} or {date_formats['today_english']}")
    print(f"Found {len(df_filtered)} announcements matching today's date (out of {len(df)} total)")
    
    # Filter by company names or stock codes
    # Priority: if company_names is provided, use that; otherwise use stock_codes
    if company_names and len(company_names) > 0:
        # Filter by company names
        if 'Company' in df_filtered.columns:
            print(f"Filtering by company names: {company_names}")
            df_filtered = df_filtered[df_filtered['Company'].isin(company_names)].copy()
            print(f"Found {len(df_filtered)} announcements matching company names")
        else:
            print(f"WARNING: Company column not found in CSV, falling back to stock codes")
            # Fallback to stock codes if Company column doesn't exist
            if stock_codes is None:
                stock_codes = [
                    "09988", "00700", "09888", "09618", "09999", "01024",
                    "03690", "01810", "01211", "09866", "09868", "02015",
                    "09863", "00020", "09660", "02525", "02665", "02498",
                    "02590", "02432", "09880", "02026", "00800", "00100", "02513"
                ]
            df_filtered = filter_by_stock_codes(df_filtered, stock_codes)
            print(f"Found {len(df_filtered)} announcements matching stock codes")
    else:
        # Default stock codes: all tech stocks EXCEPT semiconductor stocks (Hua Hong, SMIC, Biren)
        if stock_codes is None:
            stock_codes = [
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
                "00100",  # Minimax
                "02513",  # Zhipu
                # Excluded: "01347" (Hua Hong), "00981" (SMIC), "06082" (Biren)
            ]
        
        # Filter by stock codes
        print(f"Filtering by stock codes: {len(stock_codes)} codes")
        df_filtered = filter_by_stock_codes(df_filtered, stock_codes)
        print(f"Found {len(df_filtered)} announcements matching stock codes")
    
    # Debug: Show unique date formats found in CSV
    if len(df_filtered) == 0:
        unique_dates = df['Date'].unique()[:10]
        print(f"DEBUG: Sample dates found in CSV: {unique_dates}")
    
    if df_filtered.empty:
        return "## Tech Stock Regulatory Announcements\n\nNo regulatory announcements for today.\n"
    
    # Prepare data for LLM
    announcements_data = []
    for _, row in df_filtered.iterrows():
        announcements_data.append({
            'headline': row.get('Headline', ''),
            'link': row.get('Link', ''),
            'summary': row.get('Summary', ''),
            'date': row.get('Date', '')
        })
    
    # Use LLM to create consolidated news-style summary
    client = initialize_openai_client()
    
    prompt = f"""
You are a financial news journalist tasked with creating a concise news-style summary of regulatory announcements from listed tech companies.

I have collected the following regulatory announcements:

{json.dumps(announcements_data, indent=2)}

Please create a concise news-style summary.

Format your response as:

## Tech Stock Regulatory Announcements

- [Company name] [key action phrase linked to article] [rest of sentence with key details].
- [Company name] [key action phrase linked to article] [rest of sentence with key details].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [Alibaba reported](URL) strong quarterly earnings, with revenue up 15% year-over-year."
   - WRONG: "[Alibaba reported](URL) strong quarterly earnings, with revenue up 15% year-over-year." (missing "- ")

2. **ONE SENTENCE PER ITEM**: Each announcement should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.

2. **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL. For example:
   - "Alibaba [reported strong quarterly earnings](URL), with revenue up 15% year-over-year."
   - "Tencent [announced a strategic partnership](URL) with a major cloud provider."

3. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence.

4. **SENTENCE STRUCTURE**: 
   - Start with company name
   - Include the key action/link
   - Add important details (amounts, strategic implications)
   - Keep it concise but informative (typically 15-30 words per sentence)

5. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple announcements describe the same event, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any announcements that are not in the provided data.
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available.
   - **MAXIMUM LENGTH**: Keep the entire summary under 300 words total (aim for 200-250 words).
   - **COMBINE SAME COMPANY**: If multiple announcements are from the same company, combine them into ONE sentence.
   - **DEDUPLICATION CHECK**: Review all sentences and remove any duplicates or near-duplicates.

Output only the summary, no additional commentary. 

FINAL CHECKLIST BEFORE OUTPUTTING:
- Every entry MUST start with "- " (dash and space)
- Every sentence must have at least one markdown link to the article URL
- Every entry should be exactly one sentence
- No line breaks within sentences
"""
    
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"WARNING: Error generating LLM summary: {e}")
        # Fallback to simple formatting
        markdown = "## Tech Stock Regulatory Announcements\n\n"
        for item in announcements_data:
            headline = item.get('headline', '')
            link = item.get('link', '')
            summary = item.get('summary', '')
            
            if link:
                markdown += f"- **[{headline}]({link})**: {summary}\n\n"
            else:
                markdown += f"- **{headline}**: {summary}\n\n"
        return markdown


if __name__ == "__main__":
    summary = asyncio.run(summarize_tech_stock_regulatory_announcements())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("tech_stock_regulatory", summary)
    print(f"\n✓ Summary saved to: {filepath}")

