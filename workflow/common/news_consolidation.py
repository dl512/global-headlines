"""
Shared utility for consolidating and summarizing news from Google Sheets
"""

import json
import os
import sys
from datetime import datetime
import pandas as pd
import gspread

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client


def initialize_google_sheet_sheet4():
    """Initialize and return Google Sheet worksheet for NewsData (formerly Sheet4)"""
    from common.google_sheets import get_worksheet
    # Use the common get_worksheet function which automatically creates the sheet if it doesn't exist
    return get_worksheet("NewsData")


def download_google_sheet_sheet4():
    """Download NewsData sheet (formerly Sheet4) from Google Sheet as a DataFrame"""
    spreadsheet_id = "1oHKGMuBynXOJkkQpDTAtjfsv-jrTXpzI2jj29VCCDaM"
    
    try:
        worksheet = initialize_google_sheet_sheet4()
        sheet_gid = str(worksheet.id)
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_gid}"
        df = pd.read_csv(url)
        
        if df.empty or len(df.columns) < 4:
            return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary', 'News Type'])
        
        if len(df.columns) < 5:
            df['News Type'] = 'top_news'
        
        return df
    except Exception as e:
        print(f"WARNING: Error downloading Sheet4: {e}")
        return pd.DataFrame(columns=['Date', 'Headline', 'Link', 'Summary', 'News Type'])


async def consolidate_and_summarize_from_csv(client, news_type, section_title=None):
    """Consolidate news from CSV file and create a summary
    
    Args:
        client: OpenAI client
        news_type: News type (e.g., "top_news", "financial_news", "tech_news", "regulatory", "hk_ipo")
        section_title: Custom section title (e.g., "Most Important Stories", "Global Financial News", "Tech News").
                      If None, defaults based on news_type.
    """
    print(f"\n{'='*80}")
    print(f"Step: Consolidating and summarizing news from CSV ({news_type})...")
    print('='*80)
    
    print(f"Reading data from {news_type}.csv...")
    from common.csv_storage import read_news_items_from_csv
    from datetime import datetime
    
    df = read_news_items_from_csv(news_type, date=datetime.now())
    
    if df.empty:
        print(f"ERROR: No data found in {news_type}.csv")
        return None
    
    if len(df.columns) == 0:
        print(f"ERROR: {news_type}.csv appears to be empty")
        return None
    
    # CSV already filtered by date, so use df directly
    df_filtered = df.copy()
    
    if len(df_filtered) == 0:
        print(f"ERROR: No news items found for today in {news_type}.csv")
        return None
    
    print(f"Found {len(df_filtered)} news items in {news_type}.csv for today")
    
    consolidated_data = []
    for idx, row in df_filtered.iterrows():
        # CSV columns: Date, Headline, Link, Summary
        headline = str(row['Headline']) if pd.notna(row.get('Headline')) else ""
        link = str(row['Link']) if pd.notna(row.get('Link')) else ""
        summary = str(row['Summary']) if pd.notna(row.get('Summary')) else ""
        
        if headline and headline != "nan" and headline.strip() and headline.lower() not in ['headline', 'title']:
            item = {
                "headline": headline,
                "link": link,
                "summary": summary
            }
            consolidated_data.append(item)
    
    if not consolidated_data:
        print(f"ERROR: No valid news items found in {news_type}.csv")
        return None
    
    # Determine section title
    if section_title is None:
        # Default titles based on news_type
        if news_type == "financial_news":
            section_title = "Global Financial News"
        elif news_type == "tech_news":
            section_title = "Tech News"
        elif news_type == "top_news":
            section_title = "Most Important Stories"
        elif news_type == "hk_news":
            section_title = "Hong Kong News"
        else:
            section_title = "Most Important Stories"
    
    # Create base format instruction
    base_format_instruction = f"""
Format your response as:

## {section_title}

- [Key phrase linked to article] [rest of sentence with details].
- [Key phrase linked to article] [rest of sentence with details].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [Alphabet announced](URL) capital expenditures for 2026 could reach $175-$185 billion..."
   - WRONG: "[Alphabet announced](URL) capital expenditures for 2026 could reach $175-$185 billion..." (missing "- ")

2. **ONE SENTENCE PER ITEM**: Each news item should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.

2. **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL. For example:
   - "Teradyne and MultiLane are [forming a joint venture](URL), MultiLane Test Products (MLTP), to accelerate the development of test solutions for high speed data connections."
   - "Ricursive Intelligence [raised $300M Series A](URL) for AI-driven IC design."
   - "IonQ [plans to acquire SkyWater](URL) for ~$1.8B, creating a 'vertically integrated full-stack quantum platform company.'"

3. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence. This could be:
   - The main action (e.g., "raised $300M", "acquired", "launched", "announced")
   - The key development (e.g., "forming a joint venture", "announced partnership")
   - The significant number/metric (e.g., "$2B investment", "50% performance boost")

4. **SENTENCE STRUCTURE**: 
   - Include the key action/link
   - Add important details (amounts, names, strategic implications, locations)
   - Keep it concise but informative (typically 15-30 words per sentence)

5. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple items describe the same event, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any news stories that are not in the provided data.
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available (e.g., "$300M", "50%", "$1.8B").
   - **DEDUPLICATION CHECK**: Review all sentences and remove any duplicates or near-duplicates.
"""

    # Customize prompt based on news type
    if news_type == "hk_news":
        summary_prompt = f"""
You are a news analyst tasked with creating a concise daily news summary focused on Hong Kong news.

I have collected news items with their summaries from multiple Hong Kong news sources:

{json.dumps(consolidated_data, indent=2)}

Please create a concise and short report of the most important Hong Kong news of the day, focusing on:
- Politics: Government policies, political developments, elections, legislative changes
- Social: Social issues, public events, community news, social movements
- Economy: Economic developments, business news, market updates, financial policies

NOTE: This is a component that will be combined with other summaries to create a final newsletter. Do NOT include any header or title. Start directly with the content section.

{base_format_instruction}

- Focus on the most significant and impactful stories related to politics, social issues, and economy
- **MAXIMUM LENGTH**: Keep the entire summary under 600 words total (aim for 400-500 words). Prioritize covering more unique stories over longer descriptions.
- Use the provided summaries to understand the context, but do not copy them verbatim - be concise
- Prioritize news that has significant impact on Hong Kong's political, social, or economic landscape
- Group related stories together when appropriate (combine into one sentence)

Output only the summary, no additional commentary. 

FINAL CHECKLIST BEFORE OUTPUTTING:
- Every entry MUST start with "- " (dash and space)
- Every sentence must have at least one markdown link to the article URL
- Every entry should be exactly one sentence
- No line breaks within sentences
"""
    else:
        summary_prompt = f"""
You are a news analyst tasked with creating a concise daily news summary for an audience based in Hong Kong.

I have collected news items with their summaries from multiple major news sources:

{json.dumps(consolidated_data, indent=2)}

Please create a concise and short report of the most important news of the day.

NOTE: This is a component that will be combined with other summaries to create a final newsletter. Do NOT include any header or title. Start directly with the content section.

{base_format_instruction}

- Focus on the most significant and impactful stories from the provided data
- **MAXIMUM LENGTH**: Keep the entire summary under 600 words total (aim for 400-500 words). Prioritize covering more unique stories over longer descriptions.
- Use the provided summaries to understand the context, but do not copy them verbatim - be concise
- Prioritize news related to the United States and China, as these are of particular interest to the Hong Kong-based audience
- However, do not exclude important news from other countries - major global developments, conflicts, natural disasters, and significant political events from any country should be included
- Balance the coverage: prioritize US and China news, but ensure important stories from other regions are not overlooked
- Group related stories together when appropriate (combine into one sentence)
- IMPORTANT: When referring to Donald Trump, always refer to him as "President Donald Trump" or "US President Donald Trump". He is the CURRENT President of the United States as of 2025. Do NOT label him as "Former President" or "Ex-President" - this is incorrect

Output only the summary, no additional commentary. 

FINAL CHECKLIST BEFORE OUTPUTTING:
- Every entry MUST start with "- " (dash and space)
- Every sentence must have at least one markdown link to the article URL
- Every entry should be exactly one sentence
- No line breaks within sentences
"""
    
    print("Generating consolidated summary...")
    response = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[
            {"role": "user", "content": summary_prompt}
        ],
        temperature=0.3,
        max_tokens=8000,
    )
    
    summary = response.choices[0].message.content.strip()
    return summary

