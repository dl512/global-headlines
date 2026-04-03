"""
HK IPO News Summarizer
Reads from HKIPO sheet and generates markdown summary using LLM
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
from common.csv_storage import read_news_items_from_csv


async def generate_ipo_summary_markdown(items: List[Dict[str, Any]]) -> str:
    """Generate IPO summary markdown from items using LLM"""
    client = initialize_openai_client()

    prompt = f"""
You are an expert financial news summarizer specializing in Hong Kong IPO and stock market updates.

Your task is to read the following list of raw news items (each with title, date, content, link) and produce a concise daily bulletin in English.

Format your response as:

## HK IPO News Summary

- [Company/Stock name] [key action phrase linked to article] [rest of sentence with key details].
- [Company/Stock name] [key action phrase linked to article] [rest of sentence with key details].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [Company ABC raised](URL) $500M in IPO, pricing shares at $20 each."
   - WRONG: "[Company ABC raised](URL) $500M in IPO, pricing shares at $20 each." (missing "- ")

2. **ONE SENTENCE PER ITEM**: Each news item should be exactly ONE sentence. Use bullet points (-) for each entry, but keep each entry to one sentence with no line breaks within the sentence.

2. **INLINE LINKS ON KEY PHRASES**: The key action phrase or most important part of each sentence must be a markdown link to the article URL. For example:
   - "Company ABC [raised $500M in IPO](URL), pricing shares at $20 each."
   - "XYZ Holdings [announced IPO plans](URL) targeting a $1B valuation."

3. **LINK PLACEMENT**: Place the link on the most important action or key phrase in the sentence.

4. **SENTENCE STRUCTURE**: 
   - Start with company/stock name/code
   - Include the key action/link
   - Add important details (IPO size, pricing, dates, performance metrics)
   - Keep it concise but informative (typically 15-30 words per sentence)

5. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple items describe the same event or company, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any news stories that are not in the provided data.
   - **ALWAYS GROUP**: If multiple items are about the SAME company/stock, combine them into ONE sentence.
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available (e.g., IPO size, pricing, valuation).
   - **INCLUDE DATES**: For price-related news, include the date (e.g., "on December 17" or "Dec 17") for temporal context.
   - **MAXIMUM LENGTH**: Keep the entire summary under 400 words total. Prioritize covering more unique companies/stocks over longer descriptions.
   - **SORT BY RECENCY**: List newest items/companies first.
   - **DEDUPLICATION CHECK**: Review all sentences and remove any duplicates or near-duplicates.

Raw news data (JSON):

{json.dumps(items, ensure_ascii=False, indent=2)}

Output only the markdown summary above. No extra commentary. 

FINAL CHECKLIST BEFORE OUTPUTTING:
- Every entry MUST start with "- " (dash and space)
- Every sentence must have at least one markdown link to the article URL
- Every entry should be exactly one sentence
- No line breaks within sentences
""".strip()

    resp = await chat_completion_with_fallback(
        client,
        "main",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1400,
    )
    return (resp.choices[0].message.content or "").strip()


def get_trading_dates() -> List[str]:
    """Get today's date in DD/MM/YYYY format"""
    today = datetime.now()
    formatted_today = today.strftime('%d/%m/%Y')
    return [formatted_today]


async def summarize_hk_ipo_news(date: Optional[datetime] = None) -> str:
    """Summarize HK IPO news from HKIPO sheet using LLM
    
    Args:
        date: Optional date to filter news (defaults to today only)
    
    Returns:
        Markdown formatted summary
    """
    # Read data from CSV (filtered by today's date)
    if date is None:
        date = datetime.now()
    
    df = read_news_items_from_csv("hk_ipo", date=date)
    
    if df.empty:
        return "## HK IPO News\n\nNo IPO news available.\n"
    
    print(f"Found {len(df)} IPO news items for today")
    
    # Convert to format expected by generate_ipo_summary_markdown
    items = []
    for _, row in df.iterrows():
        items.append({
            'headline': row.get('Headline', ''),
            'url': row.get('Link', ''),
            'summary': row.get('Summary', ''),
            'date': row.get('Date', '')
        })
    
    # Use existing IPO summary logic
    summary = await generate_ipo_summary_markdown(items)
    
    if not summary:
        return "## HK IPO News\n\nNo IPO news available.\n"
    
    return summary


if __name__ == "__main__":
    summary = asyncio.run(summarize_hk_ipo_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("hk_ipo", summary)
    print(f"\n✓ Summary saved to: {filepath}")

