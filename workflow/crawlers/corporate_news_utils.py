"""
Corporate News Utilities
Shared utility functions for corporate news crawling, including company relevance checking
"""

import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback


async def is_news_about_company(client, headline: str, url: str, html_content: str, company: str, stock_code: Optional[str] = None) -> bool:
    """Use LLM to check if a news article is actually about the specified company
    
    Args:
        client: OpenAI client
        headline: News headline
        url: News article URL
        html_content: HTML content of the article (or summary)
        company: Company name to check against (e.g., "Alibaba", "TSMC", "NVIDIA")
        stock_code: Optional stock code for additional context (e.g., "09988")
    
    Returns:
        True if the article is about the specified company, False otherwise
    """
    # Quick check: Filter out obvious stock price-related news
    headline_lower = headline.lower()
    company_lower = company.lower()
    
    # Stock price-related keywords that indicate the article is about stock prices, not business news
    stock_price_keywords = [
        "stock price", "share price", "stock rises", "stock falls", "stock jumps", "stock drops",
        "stock gains", "stock losses", "stock surges", "stock plunges", "stock soars", "stock tumbles",
        "trading at", "trades at", "shares rise", "shares fall", "shares jump", "shares drop",
        "market cap", "market capitalization", "price target", "analyst rating", "upgrade", "downgrade",
        "stock split", "dividend yield", "pe ratio", "valuation", "stock market", "equity market",
        "intraday", "pre-market", "after-hours", "closing price", "opening price", "52-week high", "52-week low",
        "stock rally", "stock selloff", "stock crash", "stock bubble", "bullish", "bearish",
        "buy rating", "sell rating", "hold rating", "overweight", "underweight", "neutral rating"
    ]
    
    # Check if headline contains stock price-related keywords
    is_stock_price_news = any(keyword in headline_lower for keyword in stock_price_keywords)
    
    # If it's clearly stock price news, reject immediately (unless it's about significant business news that affects stock)
    # But be careful - some business news might mention stock prices but still be about the business
    # So we'll still pass it to LLM but with a note in the prompt
    
    # Check if company name appears in headline (with some variations)
    company_in_headline = (
        company_lower in headline_lower or
        f"{company_lower}'s" in headline_lower or
        f"{company_lower} " in headline_lower or
        f" {company_lower}" in headline_lower
    )
    
    # If company is clearly the subject of the headline (e.g., "Alibaba launches...", "TSMC announces...")
    # it's very likely relevant
    action_verbs = ["launches", "announces", "reports", "reveals", "unveils", "introduces", "plans", 
                    "earns", "wins", "signs", "partners", "acquires", "invests", "expands", "opens"]
    is_company_subject = False
    if company_in_headline:
        # Check if company appears before common action verbs (indicating it's the subject)
        for verb in action_verbs:
            if company_lower in headline_lower and verb in headline_lower:
                company_pos = headline_lower.find(company_lower)
                verb_pos = headline_lower.find(verb)
                # If company appears before the verb, it's likely the subject
                if company_pos < verb_pos and verb_pos - company_pos < 50:  # Within reasonable distance
                    is_company_subject = True
                    break
    
    # Prepare company context
    company_context = f"Company: {company}"
    if stock_code:
        company_context += f" (Stock Code: {stock_code})"
    
    # Extract a sample of the article content (first 2000 chars to avoid token limits)
    content_sample = html_content[:2000] if html_content else ""
    
    # Adjust prompt based on whether company is clearly the subject in headline and if it's stock price news
    stock_price_warning = ""
    if is_stock_price_news:
        stock_price_warning = """
CRITICAL: The headline contains stock price-related keywords (e.g., "stock price", "shares rise", "trading at", etc.).
This article is likely about STOCK PRICES or MARKET MOVEMENTS, not substantive business news.
REJECT this article unless it contains significant business news (e.g., major earnings, product launches, strategic announcements) 
that happens to mention stock prices. Pure stock price movements, trading activity, or market performance should be REJECTED.
"""
    
    if is_company_subject:
        strictness_note = f"""
IMPORTANT: The company name appears as the SUBJECT in the headline (e.g., "{company} launches...", "{company} announces...").
This strongly indicates the article is about {company}. Be lenient and accept unless the article is clearly about stock prices/market movements or about a different company.
{stock_price_warning}
"""
    elif company_in_headline:
        strictness_note = f"""
IMPORTANT: The company name appears in the headline. This suggests the article may be about {company}. 
Be reasonably lenient - accept if the article is about {company}'s activities, products, or announcements.
{stock_price_warning}
"""
    else:
        strictness_note = f"""
IMPORTANT: The company name does NOT appear prominently in the headline. Be more careful - only accept if the article content clearly shows it's about {company}.
{stock_price_warning}
"""
    
    prompt = f"""
You are a news analyst tasked with determining if a news article is actually about a SPECIFIC COMPANY.

{strictness_note}

GUIDELINES:
1. The article should be PRIMARILY about the specified company, not just mention it in passing
2. The article should be about the CORRECT company (not a different company with a similar name)
3. The company should be the MAIN SUBJECT or a PRIMARY FOCUS of the article

ACCEPT articles that:
   - Are about the company's own announcements, product launches, financial results (earnings, revenue), or strategic decisions
   - Feature the company as the main subject (especially if company is the subject in the headline)
   - Are about the company's direct actions, partnerships, acquisitions, or developments
   - Are about the company's products, services, or business activities
   - Are about major business news, operational updates, or corporate developments
   - Mention the company prominently in the headline as the subject (e.g., "{company} launches...", "{company} announces...")
   
NOTE: Financial results (earnings, revenue, profit) are ACCEPTABLE as they are substantive business news. 
Stock price movements, trading activity, and market performance are NOT acceptable.

REJECT articles that:
   - Are primarily about STOCK PRICES, stock market movements, trading activity, or share price changes
   - Are about stock market performance, price targets, analyst ratings, or investment recommendations
   - Are about daily/weekly stock price movements, market cap changes, or trading volume
   - Are about stock splits, dividends (unless significant strategic announcement), or routine financial market updates
   - Only mention the company briefly in a list of many companies
   - Are about a different company with a similar name (e.g., "Alibaba Cloud" vs "Alibaba Group" - verify it's the right entity)
   - Are primarily about competitors or industry trends without focusing on the company itself
   - Are about unrelated topics that only mention the company name in passing
   - Are about other companies' actions that only indirectly affect the company

Company to check: {company_context}

Article headline: {headline}
Article URL: {url}
Article content sample: {content_sample}

Based on the headline, URL, and content, determine if this article is PRIMARILY about the specified company ({company}).

CRITICAL: If the article is primarily about STOCK PRICES, stock market movements, trading activity, share price changes, or market performance, REJECT it (return "NO") even if it mentions {company}.

If the company name appears as the subject in the headline (e.g., "{company} launches..."), the article is LIKELY about {company} - accept it unless it's clearly about stock prices/market movements or about a different company.

Return ONLY "YES" if the article is primarily about {company}'s business activities (not stock prices), or "NO" if it's about stock prices, not primarily about {company}, or is about a different company.
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result == "YES"
    except Exception as e:
        print(f"      WARNING: Error checking company relevance: {e}")
        # Default to True if check fails (to avoid losing potentially relevant news)
        # But log the error so we know something went wrong
        return True


async def is_article_matching_search_theme(
    client,
    headline: str,
    url: str,
    html_content: str,
    search_query: str,
) -> bool:
    """Use LLM to decide if an article matches a Google News *topic* query (not a single company)."""
    content_sample = html_content[:2000] if html_content else ""
    prompt = f"""
You are screening news for a professional digest on conversational AI, AI customer support, and CX automation.

Google News search theme (boolean-style query the user ran):
{search_query}

Article headline: {headline}
URL: {url}
Article sample: {content_sample}

Return YES only if the article is SUBSTANTIVELY about this theme — e.g. conversational AI, AI agents for support,
contact center automation, CX / messaging automation, chatbots for business, voice/virtual agents for service,
or closely related B2B product/funding/partnership news.

Return NO if it is primarily: stock price or trading noise, unrelated consumer tech, generic big-tech earnings with no CX/AI angle,
sports/entertainment, or only a passing mention of AI with no support/CX focus.

Return ONLY the word YES or NO.
"""
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result = response.choices[0].message.content.strip().upper()
        return result.startswith("YES")
    except Exception as e:
        print(f"      WARNING: Error checking topic relevance: {e}")
        return True

