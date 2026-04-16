"""
Summarizer for AR / AI glasses combined CSV (industry sites + Google News rows).
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback
from common.csv_storage import read_news_items_from_csv


async def summarize_ar_ai_glasses_news(
    date: Optional[datetime] = None,
    section_title: Optional[str] = None,
) -> str:
    if date is None:
        date = datetime.now()
    if section_title is None:
        section_title = "AR / AI Glasses"

    df = read_news_items_from_csv("ar_ai_glasses_news", date=date)
    if df.empty:
        return f"## {section_title}\n\nNo AR / AI glasses news available.\n"

    news_data = []
    for _, row in df.iterrows():
        news_data.append(
            {
                "headline": row.get("Headline", ""),
                "link": row.get("Link", ""),
                "summary": row.get("Summary", ""),
            }
        )

    client = initialize_openai_client()
    prompt = f"""
You are a concise industry editor covering augmented reality (AR) and AI glasses only.

News items (headlines may include a [Company] prefix from Google News):
{json.dumps(news_data, indent=2)}

Write a tight digest for professionals building or investing in AR glasses / smart glasses.
- Prefer product launches, optics/display stack, chips for glasses, ecosystem deals, regulation affecting wearables.
- Omit or de-emphasize pure VR game/headset entertainment unless the item clearly ties to AR glasses or passthrough smart glasses.
- Deduplicate overlapping stories.

Format:

## {section_title}

- One sentence per bullet; start each line with "- ".
- Put the markdown link on the key phrase; each bullet must link to the item's URL.

CRITICAL: Only use facts from the provided items. Do not invent products or dates.

Output only the markdown section.
"""

    try:
        response = await chat_completion_with_fallback(
            client,
            "main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=8000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"WARNING: Error generating AR glasses summary: {e}")
        md = f"## {section_title}\n\n"
        for item in news_data:
            h, link, s = item.get("headline", ""), item.get("link", ""), item.get("summary", "")
            if link:
                md += f"- **[{h}]({link})**: {s}\n\n"
            else:
                md += f"- **{h}**: {s}\n\n"
        return md


if __name__ == "__main__":
    print(asyncio.run(summarize_ar_ai_glasses_news()))
