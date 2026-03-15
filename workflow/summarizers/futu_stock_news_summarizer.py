"""
Futu Stock News Summarizer
Summarizes stock-specific news from Futu (futunn.com)
"""

import asyncio
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.csv_storage import read_news_items_from_csv


def filter_by_stock_codes(df: pd.DataFrame, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
    """Filter DataFrame by stock codes
    
    Args:
        df: DataFrame with news items
        stock_codes: List of 5-digit stock codes to filter (e.g., ["00981", "00100"])
                    If None, returns all rows
    
    Returns:
        Filtered DataFrame
    """
    if stock_codes is None or len(stock_codes) == 0:
        return df
    
    # Check if Stock Code column exists
    if "Stock Code" in df.columns:
        return df[df["Stock Code"].isin(stock_codes)]
    else:
        # Fallback: try to extract from Headline (for backward compatibility)
        # Format: "00981 - Company Name - Headline"
        filtered_rows = []
        for _, row in df.iterrows():
            headline = str(row.get("Headline", ""))
            for code in stock_codes:
                if code in headline:
                    filtered_rows.append(row)
                    break
        return pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame()


def filter_by_company_names(df: pd.DataFrame, company_names: Optional[List[str]] = None) -> pd.DataFrame:
    """Filter DataFrame by company names
    
    Args:
        df: DataFrame with news items
        company_names: List of company names to filter (e.g., ["SMIC", "Hua Hong"])
                      If None, returns all rows
    
    Returns:
        Filtered DataFrame
    """
    if company_names is None or len(company_names) == 0:
        return df
    
    # Check if Company column exists
    if "Company" in df.columns:
        return df[df["Company"].isin(company_names)]
    else:
        # Fallback: try to extract from Headline (for backward compatibility)
        filtered_rows = []
        for _, row in df.iterrows():
            headline = str(row.get("Headline", ""))
            for company in company_names:
                if company.lower() in headline.lower():
                    filtered_rows.append(row)
                    break
        return pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame()


async def summarize_futu_stock_news(
    stock_codes: Optional[List[str]] = None,
    company_names: Optional[List[str]] = None,
    section_title: str = "Futu Stock News"
) -> str:
    """Summarize Futu stock news from CSV
    
    Args:
        stock_codes: List of 5-digit stock codes to filter (e.g., ["00981", "00100"])
                    If None, includes all stocks
        company_names: List of company names to filter (e.g., ["SMIC", "Hua Hong"])
                       If provided, takes priority over stock_codes
        section_title: Title for the summary section
    
    Returns:
        Markdown-formatted summary
    """
    # Read from futu_stock_news.csv
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "news_csv",
        "futu_stock_news.csv"
    )
    
    if not os.path.exists(csv_path):
        return f"## {section_title}\n\nNo news data available.\n"
    
    # Read CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"ERROR: Failed to read CSV: {e}")
        return f"## {section_title}\n\nError reading news data.\n"
    
    if df.empty:
        return f"## {section_title}\n\nNo news data available.\n"
    
    # Filter by date (today only)
    today = datetime.now()
    
    # Get today's date in multiple formats
    today_str = today.strftime("%B %d, %Y")  # "January 23, 2026"
    today_dd_mm_yyyy = today.strftime("%d/%m/%Y")  # "23/01/2026"
    
    # Filter by date
    if "Date" in df.columns:
        # Check for both English and DD/MM/YYYY formats
        date_mask = (
            df["Date"].astype(str).str.contains(today_str, na=False) |
            df["Date"].astype(str).str.contains(today_dd_mm_yyyy, na=False) |
            df["Date"].astype(str).str.contains(f'"{today_str}"', na=False)
        )
        df = df[date_mask]
    
    if df.empty:
        return f"## {section_title}\n\nNo recent news available.\n"
    
    # Filter by stock codes or company names
    if company_names and len(company_names) > 0:
        df = filter_by_company_names(df, company_names)
        print(f"Filtered by company names: {company_names}")
    elif stock_codes and len(stock_codes) > 0:
        df = filter_by_stock_codes(df, stock_codes)
        print(f"Filtered by stock codes: {stock_codes}")
    
    if df.empty:
        return f"## {section_title}\n\nNo news matching the filter criteria.\n"
    
    # Note: All news in futu_stock_news.csv is from Futu, so no need to filter by URL
    
    print(f"Found {len(df)} Futu stock news items to summarize")
    
    # Convert DataFrame to list of news items for consolidation
    news_items = []
    for _, row in df.iterrows():
        headline = str(row.get("Headline", ""))
        url = str(row.get("Link", ""))
        summary = str(row.get("Summary", ""))
        
        # Include stock code and company in headline if available
        stock_code = str(row.get("Stock Code", ""))
        company = str(row.get("Company", ""))
        
        if stock_code and company:
            # Format: "Stock Code - Company - Headline"
            full_headline = f"{stock_code} - {company} - {headline}"
        elif company:
            full_headline = f"{company} - {headline}"
        else:
            full_headline = headline
        
        news_items.append({
            "headline": full_headline,
            "url": url,
            "summary": summary
        })
    
    # Use consolidation function to generate summary
    # Note: consolidate_and_summarize_from_csv expects (client, news_type, section_title)
    # But we have news_items list, so we need to create a custom summary
    import json
    from common.openai_utils import initialize_openai_client
    
    client = initialize_openai_client()
    
    # Create custom prompt for Futu stock news
    base_format_instruction = f"""
Format your response as:

## {section_title}

- [Key phrase linked to article] [rest of sentence with key details].
- [Key phrase linked to article] [rest of sentence with key details].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [TSMC announced](URL) plans to expand production capacity..."
   - WRONG: "[TSMC announced](URL) plans to expand production capacity..." (missing "- ")

2. **ONE SENTENCE PER ITEM**: Each news item should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.

2. **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL.

3. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence.

4. **SENTENCE STRUCTURE**: 
   - Include the key action/link
   - Add important details (amounts, names, strategic implications)
   - Keep it concise but informative (typically 15-30 words per sentence)

5. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple items describe the same event, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any news stories that are not in the provided data.
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available.
   - **DEDUPLICATION CHECK**: Review all sentences and remove any duplicates or near-duplicates.
"""
    
    prompt = f"""
You are a financial news journalist creating a summary of stock-specific news from Futu.

I have collected the following news items:

{json.dumps(news_items, indent=2)}

Please create a concise news-style summary.

{base_format_instruction}

- Focus on the most significant and impactful stock news
- **MAXIMUM LENGTH**: Keep the entire summary under 500 words total. Prioritize covering more unique stories over longer descriptions.
- Use the provided summaries to understand the context, but do not copy them verbatim - be concise

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
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"WARNING: Error generating summary: {e}")
        # Fallback
        markdown = f"## {section_title}\n\n"
        for item in news_items:
            headline = item.get("headline", "")
            url = item.get("url", "")
            if url:
                markdown += f"[{headline}]({url}).\n"
            else:
                markdown += f"{headline}.\n"
        return markdown


if __name__ == "__main__":
    # Test the summarizer
    summary = asyncio.run(summarize_futu_stock_news())
    print(summary)

