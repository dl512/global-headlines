"""
Global News Summarizer
Reads from Countries sheet and generates markdown summary using LLM
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
from common.csv_storage import read_news_items_from_csv


def download_google_sheet():
    """Download the GlobalNews sheet as a DataFrame"""
    from common.google_sheets import download_worksheet_as_dataframe, SHEET_MAPPING
    df = download_worksheet_as_dataframe(SHEET_MAPPING["global_news"])
    return df


def load_global_news_data(date: Optional[datetime] = None):
    """Load global news data, trying CSV first, then Google Sheets as fallback"""
    # Try CSV first (more reliable and faster)
    try:
        print("Trying to load data from CSV...")
        df = read_news_items_from_csv("global_news", date)
        if not df.empty and 'Country' in df.columns:
            print(f"  [OK] Loaded {len(df)} headlines from CSV")
            return df
        else:
            print("  [WARNING] CSV is empty or missing Country column, trying Google Sheets...")
    except Exception as e:
        print(f"  [WARNING] Failed to load from CSV: {e}")
        print("  Trying Google Sheets as fallback...")
    
    # Fallback to Google Sheets
    try:
        df = download_google_sheet()
        print(f"  [OK] Loaded {len(df)} headlines from Google Sheets")
        return df
    except Exception as e:
        print(f"  [ERROR] Failed to load from Google Sheets: {e}")
        raise


async def summarize_global_news(date: Optional[datetime] = None) -> str:
    """Summarize global news from Countries sheet using LLM
    
    Args:
        date: Optional date to filter news (defaults to today)
    
    Returns:
        Markdown formatted summary
    """
    print("Generating global news summary...")
    
    # Initialize OpenAI client
    client = initialize_openai_client()

    # Load data (tries CSV first, then Google Sheets)
    print("Loading headline data...")
    try:
        df = load_global_news_data(date if date else datetime.now())
    except Exception as e:
        error_msg = f"Failed to load global news data: {e}"
        print(f"  [ERROR] {error_msg}")
        return f"## Regional Stories (directly from local news)\n\n{error_msg}\n"
    
    # Debug: Print column names and sample data
    print(f"Columns in sheet: {list(df.columns)}")
    print(f"Total rows: {len(df)}")
    
    # Filter to only today's headlines
    # The sheet may use various date formats, so we check multiple formats
    today_obj = datetime.now()
    
    # Generate dates in multiple formats for matching
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    # Format 1: English format "January 9, 2026" (new format)
    today_str_english = f"{month_names[today_obj.month - 1]} {today_obj.day}, {today_obj.year}"
    
    # Format 2: DD/MM/YYYY format (with leading zeros) - old format
    today_str_padded = f"{today_obj.day:02d}/{today_obj.month:02d}/{today_obj.year}"
    
    # Format 3: DD/MM/YYYY format (without leading zeros) - old format
    today_str_unpadded = f"{today_obj.day}/{today_obj.month}/{today_obj.year}"
    
    # Format 4: MM/DD/YYYY format (US format, in case)
    today_str_us = f"{today_obj.month:02d}/{today_obj.day:02d}/{today_obj.year}"
    
    print(f"Looking for dates: {today_str_english}, {today_str_padded}, {today_str_unpadded}, or {today_str_us} (today only)")
    
    # Get only today's headlines (check all date formats)
    df_filtered = df[
        (df['Date'].astype(str) == today_str_english) |
        (df['Date'].astype(str) == today_str_padded) |
        (df['Date'].astype(str) == today_str_unpadded) |
        (df['Date'].astype(str) == today_str_us)
    ].copy()
    
    # Filter out rows without headlines
    df_filtered = df_filtered[df_filtered['Headline'].notna() & (df_filtered['Headline'] != '')]
    
    print(f"Found {len(df_filtered)} headlines to process")
    
    if len(df_filtered) == 0:
        print("No headlines found for today!")
        print(f"Today's date formats checked: {today_str_english}, {today_str_padded}, {today_str_unpadded}, {today_str_us}")
        print("Showing first few dates in sheet for debugging:")
        if 'Date' in df.columns:
            print(df[['Date']].head(10) if 'Country' not in df.columns else df[['Country', 'Date']].head(10))
        else:
            print("Available columns:", list(df.columns))
            print(df.head(10))
        print(f"\nUnique date formats found in sheet: {df['Date'].unique()[:10] if 'Date' in df.columns else 'N/A'}")
        return "## Regional Stories (directly from local news)\n\nNo global news available for today.\n"
    
    # Convert to JSON format for the agent
    print("Preparing headline data for summary generation...")
    global_headlines_json = df_filtered.to_json(orient='records')
    
    # Create summary generation instructions
    instructions = f'''
You are a global news curator responsible for creating a comprehensive summary based on the latest headlines from every country. Your goal is to summarize the most significant news stories, focusing on global politics, major local developments, natural disasters, and other impactful events.

SUMMARY STRUCTURE - FOLLOW THIS EXACT FORMAT:

NOTE: This is a component that will be combined with other summaries to create a final newsletter. Do NOT include headers, titles, or introduction paragraphs. Start directly with the content sections.

1. REGIONAL STORIES (REQUIRED):
Organize individual news stories by geographic region. Use this exact format:

## Regional Stories (directly from local news)

### Africa / Middle East:
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)

### Americas:
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)

### Asia:
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)

### Europe:
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)

### Oceania:
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)
- [Key phrase linked to article] [rest of sentence with details]. (Source, Location)

CRITICAL FORMATTING REQUIREMENTS FOR REGIONAL STORIES:
- **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
  - CORRECT: "- [Ukraine peace plan creates tensions](URL) as President Trump's proposal sparks international debate. (BBC, United Kingdom)"
  - WRONG: "[Ukraine peace plan creates tensions](URL) as President Trump's proposal sparks international debate. (BBC, United Kingdom)" (missing "- ")
- **ONE SENTENCE PER ITEM**: Each news item should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.
- **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL. For example:
  - "[Ukraine peace plan creates tensions](URL) as President Trump's proposal sparks international debate. (BBC, United Kingdom)"
  - "[Earthquake hits Japan](URL), a magnitude 7.2 quake causing significant damage. (NHK, Japan)"
- **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence.
- **SENTENCE STRUCTURE**: Include key details, keep it concise (typically 15-30 words per sentence).
- **SOURCE AND LOCATION**: At the end of each sentence, include the news source and location in parentheses: (Source Name, Country Name)
- The classification of location should be based on where the event took place, NOT the location of the news source
- Include ALL significant headlines from the provided data, organized by region
- Include as many news items as possible - do not skip or omit headlines unless they are completely irrelevant or duplicates
- Prioritize breadth - include news from as many different countries and regions as possible

GENERAL REQUIREMENTS:

- **CRITICAL - PREVENT DUPLICATION**: Before including any news item, check if you have already covered the same story. If multiple headlines describe the same event or story, include only ONE sentence and combine the information. Do NOT repeat the same news story multiple times, even if it appears in different sources.
- **CONCISENESS IS ESSENTIAL**: Keep each sentence concise (typically 15-30 words). Be brief and direct. Avoid lengthy explanations or redundant details.
- Prioritize the most important news stories that have global relevance or significant local impact
- Include news from lesser-known countries to give readers a broader perspective
- Provide minimal context only when essential - assume readers have basic knowledge
- CRITICAL: Only summarize the news items provided in the data above. Do NOT invent, make up, or add any news stories that are not in the provided data. Every story you include must come directly from the news items provided. Do not invent your own facts - only use information from the provided headlines
- IMPORTANT: When referring to Donald Trump, always refer to him as "President Donald Trump" or "US President Donald Trump". He is the CURRENT President of the United States as of 2025. Do NOT label him as "Former President" or "Ex-President" - this is incorrect

FINAL OUTPUT REQUIREMENTS:
- Format: Markdown
- **MAXIMUM LENGTH**: Keep the entire summary under 800 words total. Prioritize breadth (more news items) over depth (longer descriptions).
- Must include the "Regional Stories (directly from local news)" section with significant news items
- Do NOT include any header, title, or introduction paragraph - start directly with "## Regional Stories (directly from local news)"
- Use proper markdown formatting for headers, links, and emphasis
- **DEDUPLICATION CHECK**: Before finalizing, review all sentences and remove any duplicates or near-duplicates covering the same story
- **VERIFICATION CHECK**: Before finalizing, verify that EVERY sentence has at least one markdown link to the article URL
- **COMPLETENESS CHECK**: Ensure you have processed all unique headlines from the provided data
- **BULLET POINT CHECK**: Before finalizing, verify that EVERY entry starts with "- " (dash and space). No entry should be missing the bullet point.
'''
    
    print(f"Prepared {len(df_filtered)} headlines for summary generation")
    print()

    # Build prompt and call OpenAI (no external agents package)
    user_content = f"""Apply the instructions below to summarize the following headline data.

HEADLINE DATA (JSON):
{global_headlines_json}

{instructions}
"""
    print("Generating global news summary (this may take a few minutes)...")
    try:
        response = await chat_completion_with_fallback(
            client,
            "main",
            messages=[{"role": "user", "content": user_content}],
            temperature=0.3,
            max_tokens=8000,
        )
        summary = (response.choices[0].message.content or "").strip()

        if not summary:
            print("  [WARNING] Summary is empty")
            return "## Regional Stories (directly from local news)\n\nNo global news available.\n"

        print("Global news summary generated successfully!")
        return summary
    except Exception as e:
        error_msg = f"Error generating summary: {e}"
        print(f"  [ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return f"## Regional Stories (directly from local news)\n\n{error_msg}\n"


if __name__ == "__main__":
    summary = asyncio.run(summarize_global_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("global_news", summary)
    print(f"\n✓ Summary saved to: {filepath}")
