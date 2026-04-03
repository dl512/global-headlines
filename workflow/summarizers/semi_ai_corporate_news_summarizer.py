"""
Semi/AI Corporate News Summarizer
Reads from CSV and generates markdown summary using LLM
Specifically for Semiconductor / AI newsletter - filters by specific company list
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
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


async def summarize_semi_ai_corporate_news(
    date: Optional[datetime] = None,
    section_title: Optional[str] = None
) -> str:
    """Summarize corporate news from CSV for Semi/AI newsletter
    Filters by specific company list: TSMC, UMC, Intel, Nvidia, Samsung, SK Hynix, Micron, AMD, OpenAI, Globalfoundries, Marvell, Broadcom, ASML, SMIC, Hua Hong, Mediatek, Cambricon, Moore Threads, Biren, Anthropic, Huayan Robotics
    
    Args:
        date: Optional date to filter news (defaults to today)
        section_title: Optional custom section title (defaults to "Semiconductor / AI Corporate News")
    
    Returns:
        Markdown formatted summary
    """
    if date is None:
        date = datetime.now()
    
    if section_title is None:
        section_title = "Semiconductor / AI Corporate News"
    
    # Fixed company list for Semi/AI newsletter
    company_names = [
        "TSMC",
        "UMC",
        "Intel",
        "NVIDIA",
        "Nvidia",
        "Samsung",
        "SK Hynix",
        "Micron",
        "AMD",
        "OpenAI",
        "GlobalFoundries",
        "Globalfoundries",
        "Marvell",
        "Broadcom",
        "ASML",
        "SMIC",
        "Hua Hong",
        "MediaTek",
        "Mediatek",
        "Cambricon",
        "Moore Threads",
        "Biren",
        "Anthropic",
        "Huayan Robotics",
        "Huayan",
    ]
    
    date_formats = get_today_dates(date)
    
    # Read data from CSV (no date filter, we'll filter manually)
    df = read_news_items_from_csv("corporate_news", date=None)
    
    if df.empty:
        return f"## {section_title}\n\nNo corporate news available.\n"
    
    # Filter by date - only include today
    df['Date'] = df['Date'].astype(str).str.strip().str.strip('"').str.strip("'")
    
    # Debug: Show sample dates from CSV
    if len(df) > 0:
        sample_dates = df['Date'].unique()[:5]
        print(f"DEBUG: Sample dates found in CSV: {list(sample_dates)}")
    
    date_matches = (
        (df['Date'] == date_formats['today_ddmm']) |
        (df['Date'] == date_formats['today_english'])
    )
    
    df_filtered = df[date_matches].copy()
    
    print(f"Filtering corporate news for today's date:")
    print(f"  Today: {date_formats['today_ddmm']} or {date_formats['today_english']}")
    print(f"Found {len(df_filtered)} news items matching today's date (out of {len(df)} total)")
    
    # Filter by company names (always filter for Semi/AI newsletter)
    if 'Company' in df_filtered.columns:
        print(f"Filtering by Semi/AI company names: {company_names}")
        df_filtered = df_filtered[df_filtered['Company'].isin(company_names)].copy()
        print(f"Found {len(df_filtered)} news items matching Semi/AI company names")
    else:
        print(f"WARNING: Company column not found in CSV")
    
    if df_filtered.empty:
        return f"## {section_title}\n\nNo corporate news available for the selected companies and dates.\n"
    
    # Prepare data for LLM
    news_data = []
    for _, row in df_filtered.iterrows():
        company = row.get('Company', '')
        headline = row.get('Headline', '')
        link = row.get('Link', '')
        summary = row.get('Summary', '')
        date_str = row.get('Date', '')
        
        news_data.append({
            'company': company,
            'headline': headline,
            'link': link,
            'summary': summary,
            'date': date_str
        })
    
    # Use LLM to create consolidated summary
    client = initialize_openai_client()
    
    prompt = f"""
You are a financial news journalist tasked with creating a concise news-style summary of corporate press releases and announcements for semiconductor and AI companies.

I have collected the following corporate news items:

{json.dumps(news_data, indent=2)}

Please create a concise news-style summary in the following format:

## {section_title}

- [Company name] [key action phrase linked to article] [rest of sentence with key details].
- [Company name] [key action phrase linked to article] [rest of sentence with key details].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [TSMC announced](URL) plans to expand production capacity..."
   - WRONG: "[TSMC announced](URL) plans to expand production capacity..." (missing "- ")

2. **ONE SENTENCE PER ITEM**: Each news item should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.

3. **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL. For example:
   - "Teradyne and MultiLane are [forming a joint venture](URL), MultiLane Test Products (MLTP), to accelerate the development of test solutions for high speed data connections."
   - "Ricursive Intelligence [raised $300M Series A](URL) for AI-driven IC design."
   - "IonQ [plans to acquire SkyWater](URL) for ~$1.8B, creating a 'vertically integrated full-stack quantum platform company.'"

4. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence. This could be:
   - The main action (e.g., "raised $300M", "acquired", "launched")
   - The key development (e.g., "forming a joint venture", "announced partnership")
   - The significant number/metric (e.g., "$2B investment", "50% performance boost")

5. **SENTENCE STRUCTURE**: 
   - Start with company name(s)
   - Include the key action/link
   - Add important details (amounts, names, strategic implications)
   - Keep it concise but informative

6. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple items describe the same event, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct, typically 15-30 words.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any news stories that are not in the provided data.
   - **PRIORITIZE SIGNIFICANT NEWS**: Focus on product launches, financial results, strategic partnerships, major investments, M&A, funding rounds, etc.
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available (e.g., "$300M", "50%", "$1.8B").
   - **DEDUPLICATION CHECK**: Review all sentences and remove any duplicates or near-duplicates.

Output only the summary, no additional commentary. 

FINAL CHECKLIST BEFORE OUTPUTTING:
- Every entry MUST start with "- " (dash and space)
- Every sentence must have at least one markdown link to the article URL
- Every entry should be exactly one sentence
- No line breaks within sentences
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=12000,
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"WARNING: Error generating LLM summary: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to simple formatting
        markdown = f"## {section_title}\n\n"
        for item in news_data:
            company = item.get('company', '')
            headline = item.get('headline', '')
            link = item.get('link', '')
            summary_text = item.get('summary', '')
            
            if link:
                markdown += f"- **[{headline}]({link})**: {summary_text}\n\n"
            else:
                markdown += f"- **{headline}**: {summary_text}\n\n"
        return markdown


if __name__ == "__main__":
    summary = asyncio.run(summarize_semi_ai_corporate_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("semi_ai_corporate_news", summary)
    print(f"\n✓ Summary saved to: {filepath}")

