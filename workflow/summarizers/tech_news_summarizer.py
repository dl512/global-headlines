"""
Tech News Summarizer
Filters tech_news.csv for AI, robotics, and semiconductor topics
Designed for tech/hardware/AI investment professionals
"""

import asyncio
import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client
from common.csv_storage import read_news_items_from_csv


def filter_by_topics(df: pd.DataFrame, topics: List[str]) -> pd.DataFrame:
    """Filter DataFrame by topics (AI, robotics, semiconductor, etc.)
    
    Uses keyword matching for fast filtering.
    """
    if df.empty:
        return df
    
    # Keywords to look for in headlines and summaries
    topic_keywords = {
        "AI": ["AI", "artificial intelligence", "machine learning", "ML", "LLM", "large language model", 
               "generative AI", "GPT", "ChatGPT", "neural network", "deep learning", "AI model", 
               "AI chip", "AI accelerator", "AI infrastructure", "AI platform", "AI agent", "openai",
               "anthropic", "claude", "gemini", "qwen", "minimax", "zhipu", "moonshot"],
        "robotics": ["robot", "robotics", "robotic", "automation", "autonomous", "drone", "humanoid",
                     "industrial robot", "service robot", "AGV", "autonomous vehicle", "unitree",
                     "ubtech", "geekplus", "dobot", "pony", "weride"],
        "semiconductor": ["semiconductor", "chip", "GPU", "CPU", "TPU", "ASIC", "FPGA", "wafer",
                         "foundry", "fab", "semiconductor equipment", "EUV", "lithography",
                         "TSMC", "SMIC", "Intel", "NVIDIA", "Nvidia", "AMD", "Qualcomm", "Broadcom",
                         "ASML", "Micron", "Samsung", "SK Hynix", "Hua Hong", "UMC", "GlobalFoundries",
                         "MediaTek", "Marvell", "Cambricon", "Moore Threads", "Biren"]
    }
    
    # Combine all keywords for the topics we're interested in
    all_keywords = []
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower == "ai":
            all_keywords.extend(topic_keywords["AI"])
        elif topic_lower == "robotics" or topic_lower == "robotic":
            all_keywords.extend(topic_keywords["robotics"])
        elif topic_lower == "semiconductor" or topic_lower == "semi":
            all_keywords.extend(topic_keywords["semiconductor"])
    
    # Remove duplicates and convert to lowercase for case-insensitive matching
    all_keywords = list(set([kw.lower() for kw in all_keywords]))
    
    # Filter by keywords
    filtered_rows = []
    for idx, row in df.iterrows():
        headline = str(row.get('Headline', '')).lower()
        summary = str(row.get('Summary', '')).lower()
        combined_text = headline + " " + summary
        
        # Check if any keyword matches
        if any(keyword in combined_text for keyword in all_keywords):
            filtered_rows.append(row)
    
    if not filtered_rows:
        return pd.DataFrame(columns=df.columns)
    
    return pd.DataFrame(filtered_rows)


async def summarize_tech_news(
    date: Optional[datetime] = None,
    section_title: Optional[str] = None
) -> str:
    """Summarize AI/robotics/semiconductor news from tech_news.csv
    
    Args:
        date: Optional date to filter news (defaults to today)
        section_title: Optional custom section title (defaults to "Tech News")
    
    Returns:
        Markdown formatted summary
    """
    if date is None:
        date = datetime.now()
    
    if section_title is None:
        section_title = "Tech News"
    
    # Read tech_news CSV
    df = read_news_items_from_csv("tech_news", date=date)
    
    if df.empty:
        return f"## {section_title}\n\nNo tech news available.\n"
    
    print(f"Found {len(df)} tech news items, filtering for AI/robotics/semiconductor topics...")
    
    # Filter by topics
    topics = ["AI", "robotics", "semiconductor"]
    df_filtered = filter_by_topics(df, topics)
    
    if df_filtered.empty:
        return f"## {section_title}\n\nNo AI/robotics/semiconductor news found in today's tech news.\n"
    
    print(f"Filtered to {len(df_filtered)} AI/robotics/semiconductor news items")
    
    # Prepare data for LLM
    news_data = []
    for _, row in df_filtered.iterrows():
        headline = row.get('Headline', '')
        link = row.get('Link', '')
        summary = row.get('Summary', '')
        
        news_data.append({
            'headline': headline,
            'link': link,
            'summary': summary
        })
    
    # Use LLM to create consolidated summary
    client = initialize_openai_client()
    
    prompt = f"""
You are a financial news journalist creating a summary for tech/hardware/AI investment professionals.

I have collected the following AI, robotics, and semiconductor news items:

{json.dumps(news_data, indent=2)}

Please create a concise news-style summary that:
1. Highlights the most significant developments in AI, robotics, and semiconductors
2. Emphasizes investment-relevant information (funding, valuations, IPOs, market trends)
3. Groups related news when appropriate
4. Focuses on actionable intelligence for investment decisions

Format your response as:

## {section_title}

- [Key phrase linked to article] [rest of sentence with key details and investment implications].
- [Key phrase linked to article] [rest of sentence with key details and investment implications].
...

CRITICAL FORMATTING REQUIREMENTS:

1. **BULLET POINTS ARE REQUIRED**: EVERY entry MUST start with a dash and space ("- "). This is mandatory. Do NOT omit the bullet points. Example:
   - CORRECT: "- [Alphabet announced](URL) capital expenditures for 2026 could reach $175-$185 billion..."
   - WRONG: "[Alphabet announced](URL) capital expenditures for 2026 could reach $175-$185 billion..." (missing "- ")

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
   - Include the key action/link
   - Add important details (amounts, names, strategic implications)
   - Keep it concise but informative (typically 15-30 words per sentence)

6. **CONTENT REQUIREMENTS**:
   - **CRITICAL - PREVENT DUPLICATION**: If multiple items describe the same event, include only ONE sentence and combine the information.
   - **CONCISENESS**: Each sentence should be clear and direct.
   - **ONLY USE PROVIDED DATA**: Do NOT invent, make up, or add any news stories that are not in the provided data.
   - **INVESTMENT FOCUS**: Emphasize funding amounts, valuations, IPOs, market size, competitive positioning, and strategic implications
   - **INCLUDE KEY METRICS**: Always include specific numbers, amounts, percentages when available (e.g., "$300M", "50%", "$1.8B").
   - **MAXIMUM LENGTH**: Keep the entire summary under 500 words total. Prioritize covering more unique stories over longer descriptions.
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
            max_tokens=8000,
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
            headline = item.get('headline', '')
            link = item.get('link', '')
            summary_text = item.get('summary', '')
            
            if link:
                markdown += f"- **[{headline}]({link})**: {summary_text}\n\n"
            else:
                markdown += f"- **{headline}**: {summary_text}\n\n"
        return markdown


if __name__ == "__main__":
    summary = asyncio.run(summarize_tech_news())
    print(summary)
    
    # Save the summary to file
    from common.summary_storage import save_summary
    filepath = save_summary("tech_news", summary)
    print(f"\n✓ Summary saved to: {filepath}")

