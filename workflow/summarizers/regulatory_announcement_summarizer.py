"""
Regulatory Announcement Summarizer
Reads from Regulatory sheet and uses LLM to generate consolidated news-style summary
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

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


async def summarize_regulatory_announcements(date: Optional[datetime] = None) -> str:
    """Summarize regulatory announcements from Regulatory sheet using LLM
    
    Args:
        date: Optional date to filter announcements (defaults to today)
    
    Returns:
        Markdown formatted summary
    """
    if date is None:
        date = datetime.now()
    
    date_formats = get_today_dates(date)
    
    # Read data from CSV (no date filter, we'll filter manually)
    df = read_news_items_from_csv("regulatory", date=None)
    
    if df.empty:
        return "## Regulatory Announcements\n\nNo regulatory announcements for today.\n"
    
    # Filter by date - only include today
    # Convert Date column to string and strip quotes/spaces for comparison
    df['Date'] = df['Date'].astype(str).str.strip().str.strip('"').str.strip("'")
    
    # Check for dates in both DD/MM/YYYY and English formats
    # Also check for dates with or without quotes
    date_matches = (
        (df['Date'] == date_formats['today_ddmm']) |
        (df['Date'] == date_formats['today_english'])
    )
    
    df_filtered = df[date_matches].copy()
    
    print(f"Filtering regulatory announcements for today's date:")
    print(f"  Today: {date_formats['today_ddmm']} or {date_formats['today_english']}")
    print(f"Found {len(df_filtered)} announcements matching today's date (out of {len(df)} total)")
    
    # Debug: Show unique date formats found in CSV
    if len(df_filtered) == 0:
        unique_dates = df['Date'].unique()[:10]
        print(f"DEBUG: Sample dates found in CSV: {unique_dates}")
    
    if df_filtered.empty:
        return "## Regulatory Announcements\n\nNo regulatory announcements for today.\n"
    
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
You are a financial news journalist tasked with creating a concise news-style summary of regulatory announcements from listed companies.

I have collected the following regulatory announcements:

{json.dumps(announcements_data, indent=2)}

Please create a concise news-style summary.

Format your response as:

## Regulatory Announcements

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
   - "SMIC [filed a regulatory disclosure](URL) regarding its expansion plans."

3. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence. This could be:
   - The main action (e.g., "reported earnings", "announced partnership", "filed disclosure")
   - The key development (e.g., "completed acquisition", "launched new product")
   - The significant metric (e.g., "$2B investment", "50% revenue growth")

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
   - **MAXIMUM LENGTH**: Keep the entire summary under 300 words total (aim for 200-250 words). Prioritize covering more unique announcements over longer descriptions.
   - **PRIORITIZE SIGNIFICANT NEWS**: Focus on major corporate actions, financial results, regulatory changes, etc.
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
        markdown = "## Regulatory Announcements\n\n"
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
    summary = asyncio.run(summarize_regulatory_announcements())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("regulatory", summary)
    print(f"\n✓ Summary saved to: {filepath}")
