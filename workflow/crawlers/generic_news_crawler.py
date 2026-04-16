"""
Generic News Crawler
Unified crawler for top_news, tech_news, and financial_news
Uses configuration from component_config.json
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
from urllib.parse import urljoin, urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import (
    initialize_openai_client,
    chat_completion_with_fallback,
    extract_json_text_from_llm_response,
)
from common.csv_storage import batch_save_news_items_to_csv, get_csv_path
from common import extract_html
from common.link_cache import is_link_seen, save_seen_link


def heuristic_match_headline_to_link(headline: str, links_on_page: str, website: str) -> Optional[str]:
    """
    Match headline to a markdown [text](url) on the page by title overlap / keywords.
    Used when LLM providers reject the prompt (e.g. content policy) or return NO_LINK_FOUND.
    """
    if not headline or not links_on_page:
        return None
    is_futu = "futunn.com" in website or "futu" in website.lower()
    headline_lower = headline.strip().lower()
    headline_words = [w for w in re.findall(r"[a-z0-9]+", headline_lower) if len(w) > 3][:12]

    candidate_links: List[Dict[str, Any]] = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^\)]+)\)", links_on_page):
        link_text = match.group(1)
        link_url = match.group(2)
        link_text_lower = link_text.lower()
        link_url_lower = link_url.lower()

        lt_norm = re.sub(r"\s+", " ", link_text_lower.strip())
        hl_norm = re.sub(r"\s+", " ", headline_lower)
        title_bonus = 0
        if hl_norm == lt_norm:
            title_bonus = 200
        elif len(hl_norm) >= 24 and hl_norm in lt_norm:
            title_bonus = 150
        elif len(lt_norm) >= 24 and lt_norm in hl_norm:
            title_bonus = 150

        matches = sum(1 for word in headline_words if word in link_text_lower or word in link_url_lower)
        if title_bonus == 0 and matches == 0:
            continue

        priority = title_bonus
        if is_futu and ("/en/post/" in link_url or "/post/" in link_url):
            priority += 100
        elif is_futu and ("/en/main" in link_url or "/main/" in link_url):
            priority -= 10

        candidate_links.append(
            {
                "url": link_url,
                "text": link_text,
                "matches": matches + (title_bonus // 50),
                "priority": priority,
            }
        )

    candidate_links.sort(key=lambda x: (x["priority"], x["matches"]), reverse=True)
    if not candidate_links:
        return None

    best_match = candidate_links[0]
    print(
        f"    DEBUG: Heuristic best: {best_match['url'][:80]}... "
        f"(matches≈{best_match['matches']}, priority={best_match['priority']})"
    )

    if is_futu:
        if urlparse(best_match["url"]).path in ["/en/main", "/en/main/", "/main", "/main/"]:
            return None
        if "/en/post/" in best_match["url"] or "/post/" in best_match["url"]:
            return best_match["url"]
        if any(p in best_match["url"] for p in ["/menu/", "/select/", "/watchlist/"]):
            return None
        return best_match["url"]

    if any(p in best_match["url"] for p in ["/main/", "/markets/"]):
        return None
    return best_match["url"]


# Pydantic models
class Headlines(BaseModel):
    """Pydantic model for structured headlines output"""
    headlines: List[str]


class NewsItem(BaseModel):
    """Pydantic model for a single news item with headline, URL, and HTML"""
    headline: str
    url: str
    html: str


class SiteNews(BaseModel):
    """Pydantic model for all news from a single site"""
    site: str
    news_items: List[NewsItem]


# Helper functions
def remove_html_tags(html_content):
    """Remove HTML tags and return clean text"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def extract_dates_from_script_tags(html_content):
    """Extract date information from script tags (e.g., AAStocks ConvertToLocalTime, Nikkei)
    
    Returns:
        List of date strings found in script tags
    """
    dates_found = []
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find all script tags
    for script in soup.find_all("script"):
        script_text = script.string or ""
        
        # Look for AAStocks pattern: ConvertToLocalTime({dt:'YYYY/MM/DD HH:MM'})
        aastocks_pattern = r"ConvertToLocalTime\s*\(\s*\{\s*dt\s*:\s*['\"](\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})['\"]\s*\}\s*\)"
        matches = re.findall(aastocks_pattern, script_text)
        for match in matches:
            dates_found.append(match)
        
        # Look for Nikkei date patterns in script tags (e.g., "datePublished": "2026-02-10T...")
        nikkei_patterns = [
            r'"datePublished"\s*:\s*["\'](\d{4}-\d{2}-\d{2})',  # "datePublished": "2026-02-10"
            r'"dateModified"\s*:\s*["\'](\d{4}-\d{2}-\d{2})',  # "dateModified": "2026-02-10"
            r'publishedTime["\']?\s*:\s*["\'](\d{4}-\d{2}-\d{2})',  # publishedTime: "2026-02-10"
        ]
        for pattern in nikkei_patterns:
            matches = re.findall(pattern, script_text, re.IGNORECASE)
            for match in matches:
                if match not in dates_found:
                    dates_found.append(match)
        
        # Look for other common date patterns in script tags
        # Pattern: YYYY/MM/DD or YYYY-MM-DD
        date_patterns = [
            r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",  # MM/DD/YYYY
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, script_text)
            for match in matches:
                if match not in dates_found:
                    dates_found.append(match)
    
    return dates_found


def extract_links_from_html(html_string, base_url=None):
    """Extract article links from HTML, filtering out section pages"""
    soup = BeautifulSoup(html_string, "html.parser")
    links_on_page = ""
    
    # Check if this is Futu News
    is_futu = base_url and ("futunn.com" in base_url or "futu" in base_url.lower())
    
    # Common section page patterns to exclude
    section_patterns = [
        '/markets-asia-pacific/', '/world-markets/', '/markets/', '/business/', 
        '/investing/', '/tech/', '/technology/', '/politics/', '/video/', 
        '/watchlist/', '/pro/', '/livestream/', '/menu/', '/select/', 
        '/tag/', '/author/', '/category/', '/section/', '/investing-club/',
    ]
    
    # For Futu News, be less restrictive - allow /main/ and /news/ paths as they may contain articles
    if is_futu:
        section_patterns = [p for p in section_patterns if p not in ['/main/', '/news/']]
        # Only exclude obvious non-article pages for Futu
        futu_section_patterns = ['/menu/', '/select/', '/watchlist/', '/pro/', '/livestream/']
        section_patterns = [p for p in section_patterns if p in futu_section_patterns or '/category/' in p or '/tag/' in p or '/author/' in p]
    
    # Determine base domain from base_url if provided
    base_domain = None
    if base_url:
        parsed = urlparse(base_url)
        base_domain = parsed.netloc
    
    link_count = 0
    excluded_count = 0
    
    for link in soup.find_all("a", href=True):
        url = link.get("href", "")
        link_text = link.get_text(strip=True)
        
        if url and link_text and len(link_text.strip()) > 5:  # Filter out very short link text
            # Handle protocol-relative URLs
            if url.startswith("//"):
                if base_url:
                    url = urlparse(base_url).scheme + ":" + url
                else:
                    url = "https:" + url
            elif url.startswith("/") and base_url:
                url = urljoin(base_url, url)
            elif not url.startswith("http") and base_url:
                url = urljoin(base_url, url)
            
            # For Futu News: Prioritize /en/post/ and /post/ URLs (these are article pages)
            if is_futu:
                # Skip JavaScript and empty URLs
                if url.startswith('javascript:') or url == '#' or not url.startswith('http'):
                    excluded_count += 1
                    continue
                
                # Article URLs use /en/post/[ID]/[slug] or /post/[ID]/[slug] pattern
                if '/en/post/' in url or '/post/' in url:
                    # This is definitely an article URL - include it
                    links_on_page += f" [{link_text}]({url})"
                    link_count += 1
                    continue
                
                # Skip base pages (just /en/main, /main/, etc.)
                url_path = urlparse(url).path
                if url_path in ['/en/main', '/en/main/', '/main', '/main/']:
                    excluded_count += 1
                    continue
                
                # Skip obvious non-article pages
                if any(pattern in url for pattern in ['/menu/', '/select/', '/watchlist/', '/pro/', '/livestream/', '/quote/']):
                    excluded_count += 1
                    continue
                
                # For other Futu URLs, include them (they might be articles in different formats)
                links_on_page += f" [{link_text}]({url})"
                link_count += 1
                continue
            
            # Simplified approach: Extract all links like the user's working code
            # Only exclude obvious non-article pages (JavaScript, empty, or obvious section pages)
            url_path = urlparse(url).path
            path_segments = [s for s in url_path.split('/') if s]  # Remove empty segments
            
            # Skip obvious non-article pages
            skip_link = False
            
            # Skip JavaScript and empty URLs
            if url.startswith('javascript:') or url == '#' or not url.startswith('http'):
                skip_link = True
            
            # For sites like Nikkei, only exclude if URL path is very short (1-2 segments) AND matches section pattern exactly
            # Article URLs have 3+ segments (e.g., /business/tech/semiconductors/article-slug)
            if not skip_link and len(path_segments) <= 2:
                # Check if it's exactly a section page (e.g., /business/tech with nothing after)
                for pattern in section_patterns:
                    pattern_clean = pattern.rstrip('/')
                    # Only exclude if URL path exactly matches the section pattern (no additional segments)
                    if url_path.rstrip('/') == pattern_clean:
                        skip_link = True
                        break
            
            # Include all other links (let LLM matching and date filtering handle the rest)
            if not skip_link:
                links_on_page += f" [{link_text}]({url})"
                link_count += 1
            else:
                excluded_count += 1
    
    print(f"    DEBUG: Extracted {link_count} article links, excluded {excluded_count} section/non-article links")
    if is_futu and link_count == 0:
        print(f"    WARNING: No links extracted for Futu News - may need to adjust filtering")
    
    return links_on_page


async def extract_top_headlines(client, website, html_string_input, special_handling=None):
    """Extract top headlines from a news site using LLM"""
    special_handling = special_handling or {}
    is_36kr = special_handling.get("is_36kr", False)
    news_type = special_handling.get("news_type", None)  # e.g., "tech_news", "financial_news", "top_news", "hk_news"
    
    if is_36kr:
        # Special prompt for 36Kr focusing on funding events and AI/robotics
        prompt = f"""
You are a web scraper that extracts news headlines from a Chinese tech news website (36Kr PitchHub).

Here is the full HTML of {website}:

```{html_string_input}```

CRITICAL REQUIREMENTS:
1. Focus on funding events (融资, 投资, 轮次, Series A/B/C, etc.)
2. Prioritize AI/robotics news (人工智能, 机器人, AI, robotics, etc.)
3. Include other important tech news as well
4. ALWAYS translate all headlines to English
5. Extract the top 20 most prominent headlines

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1 in English",
    "headline 2 in English",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text. 
All headlines must be in English.
"""
    elif news_type == "tech_news":
        # Investment-focused prompt for tech news (AI, robotics, AI infrastructure)
        prompt = f"""
You are a news analyst extracting headlines for tech/hardware/AI investment professionals from {website}.

Here is the full HTML of {website}:

```{html_string_input}```

CRITICAL REQUIREMENTS - FOCUS ON INVESTMENT-RELEVANT TECH NEWS:

PRIORITY TOPICS (extract these first):
1. **Artificial Intelligence (AI)**:
   - AI model releases, updates, and breakthroughs
   - AI company funding, valuations, and IPOs
   - AI infrastructure investments
   - AI chip developments (GPUs, TPUs, AI accelerators)
   - Large language models (LLMs) and generative AI
   - AI agent platforms and applications
   - AI regulation and policy changes affecting investments

2. **Robotics & Automation**:
   - Robotics company news, funding, and product launches
   - Industrial automation and manufacturing robotics
   - Service robots and humanoid robots
   - Autonomous vehicles and drones
   - Robotics IPOs and M&A activity

3. **AI Infrastructure**:
   - Data center developments and investments
   - Cloud computing infrastructure for AI
   - Chip manufacturing and semiconductor news
   - GPU and AI accelerator supply/demand
   - AI computing infrastructure investments
   - Edge computing for AI applications

4. **Hardware & Semiconductors**:
   - Chip design and manufacturing news
   - Semiconductor equipment and materials
   - Hardware startups and funding
   - Hardware IPOs and acquisitions

5. **Enterprise AI & Tech Platforms**:
   - Enterprise AI software and platforms
   - AI integration in business applications
   - Tech company strategic AI initiatives

FILTER OUT:
- Consumer gadget reviews and unboxings
- Gaming hardware reviews
- General software updates without AI/hardware focus
- Entertainment tech news
- Sports and weather tech mentions

TARGET AUDIENCE: Tech/hardware/AI investment professionals who need actionable intelligence on:
- Investment opportunities in AI, robotics, and infrastructure
- Market trends affecting tech valuations
- Strategic moves by major tech companies
- Regulatory changes impacting tech investments
- Supply chain and manufacturing developments

Extract the top 20 most investment-relevant headlines. Prioritize news that would impact investment decisions.

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1",
    "headline 2",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text.
"""
    elif news_type == "financial_news":
        # Investment-focused prompt for financial news
        prompt = f"""
You are a news analyst extracting headlines for investment professionals from {website}.

Here is the full HTML of {website}:

```{html_string_input}```

CRITICAL REQUIREMENTS - FOCUS ON INVESTMENT-RELEVANT FINANCIAL NEWS:

PRIORITY TOPICS:
1. **Market Movements & Trends**:
   - Major market indices and sector performance
   - Significant stock price movements
   - Market volatility and trading volumes
   - Currency and commodity price movements

2. **Company Financials & Earnings**:
   - Earnings announcements and guidance
   - Revenue and profit reports
   - Financial results that impact valuations
   - Corporate restructuring and strategic changes

3. **M&A & Corporate Actions**:
   - Mergers and acquisitions
   - IPOs and public offerings
   - Spin-offs and divestitures
   - Share buybacks and dividends

4. **Economic Indicators & Policy**:
   - Central bank decisions and interest rate changes
   - Economic data releases (GDP, inflation, employment)
   - Fiscal policy changes
   - Trade policy and tariffs

5. **Sector-Specific Financial News**:
   - Banking and financial services
   - Real estate and property markets
   - Energy and commodities
   - Technology sector financial performance

FILTER OUT:
- Personal finance advice
- Consumer banking product launches
- Lifestyle financial content
- Non-financial general news

TARGET AUDIENCE: Investment professionals who need actionable intelligence on:
- Market opportunities and risks
- Company valuations and financial health
- Economic trends affecting investments
- Policy changes impacting markets

Extract the top 20 most investment-relevant headlines.

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1",
    "headline 2",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text.
"""
    elif news_type == "hk_news":
        # Investment-focused prompt for Hong Kong news
        prompt = f"""
You are a news analyst extracting headlines for investment professionals focused on Hong Kong from {website}.

Here is the full HTML of {website}:

```{html_string_input}```

CRITICAL REQUIREMENTS - FOCUS ON INVESTMENT-RELEVANT HONG KONG NEWS:

PRIORITY TOPICS:
1. **Politics & Policy**:
   - Government policy changes affecting business and investments
   - Regulatory changes impacting markets
   - Political developments affecting economic stability
   - Cross-border policy (Mainland China-HK relations)

2. **Economy & Markets**:
   - Hong Kong stock market performance
   - Economic indicators and GDP data
   - Property market developments
   - Trade and commerce news

3. **Social Issues**:
   - Social developments affecting business environment
   - Labor market and employment trends
   - Demographic changes
   - Social stability affecting investments

4. **Business & Corporate News**:
   - Major corporate announcements
   - Business environment changes
   - Industry developments in Hong Kong

FILTER OUT:
- Pure entertainment news
- Sports news
- Celebrity gossip
- Non-business social events

TARGET AUDIENCE: Investment professionals who need actionable intelligence on:
- Hong Kong's business and investment environment
- Policy changes affecting investments
- Economic trends in Hong Kong
- Market opportunities and risks

Extract the top 20 most investment-relevant headlines.

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1",
    "headline 2",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text.
"""
    elif news_type == "ar_ai_glasses_news":
        prompt = f"""
You are a news analyst extracting headlines about augmented reality (AR) and AI glasses / smart glasses only from {website}.

Here is the full HTML of {website}:

```{html_string_input}```

CRITICAL SCOPE — AR / AI GLASSES ONLY:
- INCLUDE: AR glasses, smart glasses, optical see-through wearables, waveguides, microLED / micro-OLED near-eye displays,
  on-device AI for glasses, spatial computing when clearly tied to glasses (e.g. Vision, Ray-Ban Meta, Android XR on headsets/glasses).
- EXCLUDE: PC VR, console VR, VR game reviews, VR esports, general TV/streaming, non-wearable gaming, generic smartphone news
  unless the story is clearly about AR glasses or smart glasses.

Extract up to 20 headlines that best match AR / smart glasses / AI glasses hardware, platforms, or ecosystem. If fewer than 20 qualify, return only the qualifying ones.

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1",
    "headline 2",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text.
"""
    else:
        # Standard prompt for other sites (top_news, etc.)
        prompt = f"""
You are a web scraper that extracts news headlines from a news site's homepage HTML.

Here is the full HTML of {website}:

```{html_string_input}```

Extract the top 20 most prominent headlines of the day. 

Focus on the main stories shown at the top of the page (usually the hero story and the next 19 featured stories). 

Ignore navigation links, video titles, weather, sport sub-sections, and advertisements.

Return ONLY a JSON object that matches this exact schema:

{{
  "headlines": [
    "headline 1",
    "headline 2",
    ...
  ]
}}

Do not include any explanations, markdown, or extra text. 

If there are fewer than 20 prominent headlines, return all of them.
"""
    
    response = await chat_completion_with_fallback(
        client,
        "light",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2500,
    )
    
    raw_content = response.choices[0].message.content.strip()
    json_text = extract_json_text_from_llm_response(raw_content)

    try:
        data = json.loads(json_text)
        top_headlines = Headlines(**data)
        
        print(f"Extracted {len(top_headlines.headlines)} headlines from {website}")
        return top_headlines.headlines
        
    except json.JSONDecodeError as e:
        print(f"ERROR: LLM did not return valid JSON for {website}: {e}")
        print(f"Raw output (after fence strip): {json_text[:200]}...")
        return []
    except ValidationError as e:
        print(f"ERROR: Validation error for {website}: {e}")
        print(f"Raw output: {json_text[:200]}...")
        return []


async def match_headline_to_link(client, headline, links_on_page, website):
    """Match a headline to the most relevant link on the page"""
    if not links_on_page:
        print(f"    DEBUG: links_on_page is empty or None")
        return None
    if not headline:
        print(f"    DEBUG: headline is empty or None")
        return None
    
    # Debug: Show how many links we have
    links_count = links_on_page.count("[")  # Rough count of markdown links
    print(f"    DEBUG: Found {links_count} links on page to search through")
    
    # Special handling for Futu News URLs
    is_futu = "futunn.com" in website or "futu" in website.lower()
    
    # For Futu News, prioritize article links (those with /en/post/ pattern) at the beginning
    if is_futu and len(links_on_page) > 8000:
        # Split links into article links and other links
        article_links = []
        other_links = []
        
        # Parse links
        for match in re.finditer(r'\[([^\]]+)\]\(([^\)]+)\)', links_on_page):
            link_text = match.group(1)
            link_url = match.group(2)
            full_link = match.group(0)
            
            # Prioritize /en/post/ URLs (these are article pages)
            if '/en/post/' in link_url or '/post/' in link_url:
                article_links.append(full_link)
            else:
                other_links.append(full_link)
        
        # Reconstruct with article links first
        prioritized_links = ' '.join(article_links + other_links)
        print(f"    DEBUG: Reordered links - {len(article_links)} article links prioritized")
        links_on_page = prioritized_links
    
    # Increase limit for link matching (up to 12000 chars to give more context)
    links_snippet = links_on_page[:12000]
    if len(links_on_page) > 12000:
        print(f"    DEBUG: Links truncated from {len(links_on_page)} to 12000 chars for LLM")
        # Try to find partial headline matches in the remaining links
        headline_keywords = headline.lower().split()[:5]  # First 5 words
        # Check if any links contain these keywords
        remaining_links = links_on_page[12000:]
        for keyword in headline_keywords:
            if keyword in remaining_links.lower() and len(keyword) > 3:  # Only check meaningful keywords
                print(f"    DEBUG: Found potential match for keyword '{keyword}' in remaining links")
    
    futu_instructions = ""
    if is_futu:
        futu_instructions = """
- For Futu News: Article URLs typically use the pattern /en/post/[ID]/[slug] or /post/[ID]/[slug]
- Look for URLs like: https://news.futunn.com/en/post/67167448/article-slug
- These are the actual article pages, not section pages
- DO NOT select URLs that are just /en/main, /main/, or other section pages
- Priority: Look for /en/post/ or /post/ URLs first
"""
    
    prompt = f"""
Given this headline: "{headline}"

And these links from the news website {website}:
{links_snippet}

Find the URL that most likely corresponds to this headline. 

IMPORTANT REQUIREMENTS:
- You MUST return a specific article URL (not a section/category page)
- DO NOT return section page URLs like /business/tech, /technology/, /markets/, /main/, etc.
- The URL must be a direct link to the article page, not a category or section page
- Article URLs are typically longer paths that point to specific articles
- Look for URLs that contain keywords from the headline
{futu_instructions}

Return ONLY the URL, nothing else.
If no matching article URL is found, return "NO_LINK_FOUND".
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        
        url = response.choices[0].message.content.strip()
        print(f"    DEBUG: LLM returned: {url[:100]}...")
        
        # Clean up the URL (remove markdown formatting if present)
        url = url.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        # Remove quotes if present
        url = url.strip('"').strip("'")
        
        # Handle protocol-relative URLs for 36Kr
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and "36kr.com" in website:
            url = "https://pitchhub.36kr.com" + url
        # Handle relative URLs for Futu News
        elif url.startswith("/") and is_futu:
            # Determine base URL
            if "news.futunn.com" in website:
                url = "https://news.futunn.com" + url
            elif "futunn.com" in website:
                url = "https://www.futunn.com" + url
        
        # If the model did NOT explicitly say NO_LINK_FOUND, try to snap the URL
        # back to one of the actual links we extracted from the page. This prevents
        # small path variations (e.g. missing a section like '/semiconductors/')
        # from giving us a non-canonical URL.
        if url != "NO_LINK_FOUND":
            candidate_urls = []
            for match in re.finditer(r'\[([^\]]+)\]\(([^\)]+)\)', links_on_page):
                candidate_urls.append(match.group(2))

            if candidate_urls:
                url_lower = url.lower()
                # 1) Exact match (case-insensitive) against any candidate URL
                exact_match = None
                for cu in candidate_urls:
                    if cu.lower() == url_lower:
                        exact_match = cu
                        break

                if exact_match:
                    url = exact_match
                else:
                    # 2) Match by slug (last path segment), ignoring case
                    from urllib.parse import urlparse

                    parsed = urlparse(url)
                    slug = parsed.path.rstrip("/").split("/")[-1].lower() if parsed.path else ""

                    best_slug_match = None
                    for cu in candidate_urls:
                        c_parsed = urlparse(cu)
                        c_slug = c_parsed.path.rstrip("/").split("/")[-1].lower() if c_parsed.path else ""
                        if slug and c_slug == slug:
                            best_slug_match = cu
                            break

                    if best_slug_match:
                        print(f"    DEBUG: Adjusted URL to canonical link from page: {best_slug_match}")
                        url = best_slug_match

        if url == "NO_LINK_FOUND":
            print(f"    DEBUG: LLM explicitly returned NO_LINK_FOUND; trying heuristic link match")
            return heuristic_match_headline_to_link(headline, links_on_page, website)

        if not url.startswith("http"):
            print(f"    DEBUG: URL doesn't start with http: {url}")
            return None
        
        return url
    except Exception as e:
        print(f"    WARNING: Error matching link (LLM): {e}")
        fb = heuristic_match_headline_to_link(headline, links_on_page, website)
        if fb:
            print(f"    DEBUG: Using heuristic link match after LLM failure")
            return fb
        import traceback
        traceback.print_exc()
        return None


async def fetch_article_html(url):
    """Fetch the HTML content of an article page"""
    try:
        html_dict = extract_html.get_raw_html(url)
        if html_dict and html_dict.get("html"):
            html_content = html_dict["html"]
            return html_content
        return None
    except Exception as e:
        print(f"      [ERROR] Error fetching article HTML: {e}")
        return None


async def is_article_from_today(client, html_content, url, date_filter_mode="today", special_handling=None):
    """Use LLM to determine if an article is from today (or today/yesterday) by reading the HTML content
    
    Args:
        client: OpenAI client
        html_content: HTML content of the article
        url: URL of the article
        date_filter_mode: "none", "today", or "today_or_yesterday"
        special_handling: Dict with special handling flags (e.g., {"is_futu_news": True})
    
    Returns:
        True if article matches date filter, False otherwise
    """
    if date_filter_mode == "none":
        return True  # No date filtering
    
    if not html_content:
        return False
    
    special_handling = special_handling or {}
    is_futu_news = special_handling.get("is_futu_news", False)
    
    # Pre-check: Extract date from URL for sites that include dates in URLs (TechCrunch, CNN, CNBC)
    url_date_check = None
    today = datetime.now()
    
    # Check for date pattern in URL: /YYYY/MM/DD/ or /YYYY-MM-DD/
    url_date_pattern = r'/(\d{4})[/-](\d{1,2})[/-](\d{1,2})/'
    url_match = re.search(url_date_pattern, url)
    
    if url_match:
        try:
            url_year = int(url_match.group(1))
            url_month = int(url_match.group(2))
            url_day = int(url_match.group(3))
            url_date = datetime(url_year, url_month, url_day)
            
            if date_filter_mode == "today":
                url_date_check = url_date.date() == today.date()
            elif date_filter_mode == "today_or_yesterday":
                yesterday = today - timedelta(days=1)
                url_date_check = url_date.date() == today.date() or url_date.date() == yesterday.date()
            
            if url_date_check:
                print(f"    >> URL date check: {url_date.date()} matches filter ({date_filter_mode})")
                # If URL date matches, we can trust it and skip LLM check for efficiency
                # But for now, let's still do LLM check as backup and use URL as fallback
            else:
                # URL has a date but it doesn't match - reject immediately for sites with dates in URLs
                # This is reliable for CNN, TechCrunch, CNBC, etc.
                print(f"    >> URL date check: {url_date.date()} does NOT match filter ({date_filter_mode}) - rejecting article")
                return False
        except (ValueError, IndexError):
            pass  # Invalid date in URL, continue with LLM check
    
    # Extract dates from script tags before removing HTML (for sites like AAStocks)
    script_dates = extract_dates_from_script_tags(html_content)
    script_date_check = None
    script_date_info = ""
    meta_date_check = None  # For Nikkei meta tag date extraction
    
    if script_dates:
        # Try to parse various date formats from script tags
        parsed_dates = []
        for date_str in script_dates:
            try:
                script_date = None
                
                # Try AAStocks format: "2026/01/15 11:33" or "2026/01/15"
                if "/" in date_str:
                    if ":" in date_str:
                        # Has time component: "2026/01/15 11:33"
                        date_part = date_str.split()[0]  # Get "2026/01/15"
                        year, month, day = map(int, date_part.split("/"))
                        script_date = datetime(year, month, day)
                    else:
                        # No time component: "2026/01/15"
                        parts = date_str.split("/")
                        if len(parts) == 3:
                            year, month, day = map(int, parts)
                            script_date = datetime(year, month, day)
                
                # Try ISO format: "2026-01-15" or "2026-01-15 11:33"
                elif "-" in date_str:
                    if ":" in date_str:
                        # Has time component: "2026-01-15 11:33"
                        date_part = date_str.split()[0]  # Get "2026-01-15"
                        year, month, day = map(int, date_part.split("-"))
                        script_date = datetime(year, month, day)
                    else:
                        # No time component: "2026-01-15"
                        parts = date_str.split("-")
                        if len(parts) == 3:
                            year, month, day = map(int, parts)
                            script_date = datetime(year, month, day)
                
                if script_date:
                    parsed_dates.append(script_date)
            except (ValueError, IndexError) as e:
                continue
        
        # Check all parsed dates against the filter
        if parsed_dates:
            for script_date in parsed_dates:
                # Check if date matches filter
                if date_filter_mode == "today":
                    date_matches = script_date.date() == today.date()
                elif date_filter_mode == "today_or_yesterday":
                    yesterday = today - timedelta(days=1)
                    date_matches = script_date.date() == today.date() or script_date.date() == yesterday.date()
                else:
                    date_matches = None
                
                if date_matches is True:
                    print(f"    >> Script date check: {script_date.date()} matches filter ({date_filter_mode})")
                    script_date_check = True
                    break
                elif date_matches is False:
                    # Date found but doesn't match - mark as False and keep checking other dates
                    if script_date_check is None:
                        script_date_check = False
                    print(f"    >> Script date check: {script_date.date()} does NOT match filter ({date_filter_mode})")
            
            # If we checked all dates and none matched, return False immediately
            if script_date_check is False:
                # All parsed dates were checked and none matched - article is too old
                print(f"    >> All script dates checked - none match filter ({date_filter_mode}) - article is too old")
                return False
        
        if script_dates:
            script_date_info = f"\nIMPORTANT: Date information found in script tags: {', '.join(script_dates)}\nThese dates are reliable indicators of publication time. Use these dates to determine if the article is from today.\n"
            print(f"    >> Found dates in script tags: {', '.join(script_dates)}")
    
    # Extract text from HTML (limit length for LLM)
    clean_text = remove_html_tags(html_content)
    # Remove newlines to reduce unnecessary spacing
    clean_text = clean_text.replace("\n", "")
    
    # Special handling for Nikkei: If text extraction failed (very short text from large HTML),
    # try to extract date from meta tags
    is_nikkei = "asia.nikkei.com" in url or "nikkei.com" in url
    meta_date_check = None
    if is_nikkei and len(clean_text) < 1000 and len(html_content) > 100000:
        print(f"    >> WARNING: Text extraction seems to have failed for Nikkei article (only {len(clean_text)} chars from {len(html_content)} chars HTML)")
        print(f"    >> Attempting to extract date from meta tags...")
        
        # Try to extract from meta tags
        soup = BeautifulSoup(html_content, "html.parser")
        meta_date = None
        
        # Check meta tags for date
        for meta in soup.find_all("meta"):
            property_attr = meta.get("property", "")
            name_attr = meta.get("name", "")
            content = meta.get("content", "")
            
            if any(prop in property_attr.lower() for prop in ["published", "modified", "date"]) or \
               any(name in name_attr.lower() for name in ["published", "modified", "date"]):
                if content:
                    # Extract date from content (e.g., "2026-02-10T12:34:56Z" -> "2026-02-10")
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
                    if date_match:
                        meta_date = date_match.group(1)
                        print(f"    >> Found date in meta tag: {meta_date}")
                        break
        
        # Check if meta date matches filter
        if meta_date:
            try:
                year, month, day = map(int, meta_date.split("-"))
                meta_date_obj = datetime(year, month, day)
                if date_filter_mode == "today":
                    meta_date_check = meta_date_obj.date() == today.date()
                elif date_filter_mode == "today_or_yesterday":
                    yesterday = today - timedelta(days=1)
                    meta_date_check = meta_date_obj.date() == today.date() or meta_date_obj.date() == yesterday.date()
                
                if meta_date_check is True:
                    print(f"    >> Meta tag date check: {meta_date_obj.date()} matches filter ({date_filter_mode})")
                elif meta_date_check is False:
                    print(f"    >> Meta tag date check: {meta_date_obj.date()} does NOT match filter ({date_filter_mode})")
            except (ValueError, IndexError):
                pass
    
    # Check for relative time indicators (e.g., "3 hours ago", "2 minutes ago", "1 hour ago")
    # These indicate the article is from today
    relative_time_patterns = [
        r'\b(\d+)\s*(?:hour|hours|hr|hrs|h)\s+ago\b',
        r'\b(\d+)\s*(?:minute|minutes|min|mins|m)\s+ago\b',
        r'\b(?:just|recently)\s+(?:published|posted|updated)\b',
        r'\b(?:today|this\s+(?:morning|afternoon|evening))\b'
    ]
    
    has_relative_time = False
    for pattern in relative_time_patterns:
        if re.search(pattern, clean_text, re.IGNORECASE):
            has_relative_time = True
            print(f"    >> Found relative time indicator (e.g., 'X hours ago') - treating as today's news")
            break
    
    if len(clean_text) > 200000:
        clean_text = clean_text[:200000] + "..."
    
    # Prepend script date info to clean text so LLM can see it
    if script_date_info:
        clean_text = script_date_info + "\n" + clean_text
    
    today = datetime.now()
    today_str = today.strftime("%B %d, %Y")  # e.g., "December 29, 2025"
    today_str_alt = today.strftime("%d %B %Y")  # e.g., "29 December 2025"
    today_str_short = today.strftime("%m/%d/%Y")  # e.g., "12/29/2025"
    
    if date_filter_mode == "today_or_yesterday":
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime("%B %d, %Y")  # e.g., "December 29, 2025"
        yesterday_str_alt = yesterday.strftime("%d %B %Y")  # e.g., "29 December 2025"
        yesterday_str_short = yesterday.strftime("%m/%d/%Y")  # e.g., "12/29/2025"
        
        date_instruction = f"""
Today's date is: {today_str} (also known as {today_str_alt} or {today_str_short})
Yesterday's date is: {yesterday_str} (also known as {yesterday_str_alt} or {yesterday_str_short})

Determine if this article was published TODAY ({today_str}) or YESTERDAY ({yesterday_str}).

Return ONLY "YES" if the article is from today or yesterday, or "NO" if it's from a different date.
"""
    else:  # date_filter_mode == "today"
        date_instruction = f"""
Today's date is: {today_str} (also known as {today_str_alt} or {today_str_short})

Determine if this article was published TODAY ({today_str}).

Return ONLY "YES" if the article is from today, or "NO" if it's from a different date.
"""
    
    futu_instruction = ""
    futu_fallback_check = False
    if is_futu_news:
        # Pre-check: Look for time-only patterns in the HTML text (HH:MM format)
        # If we find time-only patterns without dates, treat as today
        time_only_pattern = r'\b\d{1,2}:\d{2}\b'  # Matches patterns like "14:56", "9:30"
        date_time_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}'  # Matches "Dec 31, 2025 21:49"
        
        # Check if we have time-only patterns but no date-time patterns
        has_time_only = bool(re.search(time_only_pattern, clean_text))
        has_date_time = bool(re.search(date_time_pattern, clean_text, re.IGNORECASE))
        
        if has_time_only and not has_date_time:
            # Likely time-only format - treat as today (but still verify with LLM)
            futu_fallback_check = True
            print(f"    >> Detected time-only format (no date) - likely today's news")
        
        futu_instruction = """
CRITICAL: This is a Futu News article. Futu News uses a unique date format:
- If ONLY a TIME is shown (e.g., "01:23", "14:56", "09:30", "9:30") WITHOUT any date, this means the article is from TODAY.
- Common time-only patterns: "HH:MM" or "H:MM" (just time, no date)
- If a DATE followed by TIME is shown (e.g., "Dec 31, 2025 21:49", "January 1, 2025 15:20", "Jan 8 2025 14:30"), this means the article is from YESTERDAY or earlier.
- Look for timestamp patterns like "HH:MM" or "H:MM" (just time) vs "Month DD, YYYY HH:MM" or "Month DD YYYY HH:MM" (date + time).
- IMPORTANT: If you see only a time (like "01:23", "14:56", "9:30") WITHOUT any month/day/year date information, return "YES" immediately as this indicates today's news.
- Be very careful: "01:23" alone = today, but "Dec 31, 2025 01:23" = yesterday or earlier.

"""
    
    # Check if URL contains date (TechCrunch, CNN, CNBC format: /YYYY/MM/DD/)
    url_date_info = ""
    if url_match:
        try:
            url_year = int(url_match.group(1))
            url_month = int(url_match.group(2))
            url_day = int(url_match.group(3))
            month_names = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            url_date_formatted = f"{month_names[url_month - 1]} {url_day}, {url_year}"
            url_date_info = f"\nIMPORTANT: The article URL contains a date: {url_date_formatted} (from URL path /{url_year}/{url_month}/{url_day}/)\nThis is a reliable indicator of the publication date. If this date matches today or yesterday (depending on filter mode), return 'YES'.\n"
        except (ValueError, IndexError):
            pass
    
    prompt = f"""
You are analyzing a news article to determine if it was published recently.

{date_instruction}
{futu_instruction}
{url_date_info}
Here is the article content (extracted from HTML):
{clean_text}

Article URL: {url}

Look for publication date information in the article. This could be:
- A "Published" or "Updated" date
- A timestamp
- A date in the article metadata
- Any date information visible on the page
- The date in the URL path (for sites like TechCrunch, CNN, CNBC that include dates in URLs)
- Relative time indicators like "3 hours ago", "2 minutes ago", "1 hour ago", "just published", "recently updated" - these indicate the article is from TODAY
{f"- For Futu News: Look for time-only format (HH:MM or H:MM) which indicates today, vs date+time format (Month DD, YYYY HH:MM) which indicates yesterday or earlier" if is_futu_news else ""}

{f"REMINDER FOR FUTU NEWS: If you see ONLY time (HH:MM) without any date (month/day/year), it means TODAY. Return YES." if is_futu_news else ""}

{"If the URL contains a date (e.g., /2026/01/12/), use that as the primary indicator. If the URL date matches today or yesterday (depending on filter mode), return 'YES'." if url_date_info else ""}

{"CRITICAL: If you cannot clearly determine the date, return 'NO'. Only return 'YES' if you are confident the article is from today or yesterday. When in doubt, return 'NO'." if not is_futu_news else "For Futu News: If you see only time without date, return 'YES'. If you see date+time, check if it matches today or yesterday. Only return 'NO' if you clearly see a date that is not today or yesterday."}
"""
    
    # If script_date_check is True, we can return early (already verified)
    if script_date_check is True:
        return True
    
    # If meta_date_check is True (from Nikkei meta tag extraction), return early
    if meta_date_check is True:
        return True
    
    # If script_date_check is False, we already returned False above (should not reach here)
    # But add a safety check just in case
    if script_date_check is False:
        print(f"    >> ERROR: script_date_check is False but function continued - returning False")
        return False
    
    # If meta_date_check is False and we have it, return False
    if meta_date_check is False:
        print(f"    >> Meta tag date check failed - article is too old")
        return False
    
    # If script_date_check is None, continue with LLM check
    
    # Check for listing page relative time first (before LLM check)
    # This is especially important for sites like Nikkei where relative time is only on listing page
    listing_page_relative_time = special_handling.get("listing_page_relative_time", "") if special_handling else ""
    if listing_page_relative_time:
        print(f"    >> Listing page shows relative time - treating as today's news (bypassing LLM date check)")
        return True
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip().upper()
        is_today = result == "YES"
        
        # Fallback checks if LLM says NO
        if not is_today:
            # Check 1: Script date check (for AAStocks with dates in script tags)
            if script_date_check is not None:
                if script_date_check:
                    print(f"    >> LLM returned NO, but script date check passed - using script date")
                    return True
                else:
                    print(f"    >> LLM returned NO, and script date check also failed")
            
            # Check 2: URL date check (for TechCrunch, CNN, CNBC with dates in URL)
            if url_date_check is not None:
                if url_date_check:
                    print(f"    >> LLM returned NO, but URL date check passed - using URL date")
                    return True
                else:
                    print(f"    >> LLM returned NO, and URL date check also failed")
            
            # Check 3: Futu news with time-only fallback
            if is_futu_news and futu_fallback_check:
                print(f"    >> LLM returned NO, but time-only pattern detected - treating as today's news")
                return True
        
        return is_today
    except Exception as e:
        print(f"    WARNING: Error checking article date: {e}")
        
        # Fallback 1: Relative time indicators
        if has_relative_time:
            print(f"    >> Date check failed, but relative time indicator found - treating as today's news")
            return True
        
        # Fallback 2: Use meta date check if available (for Nikkei)
        if meta_date_check is not None:
            print(f"    >> Date check failed, but meta tag date check available - using meta date")
            return meta_date_check
        
        # Fallback 3: Use script date check if available (for AAStocks)
        if script_date_check is not None:
            print(f"    >> Date check failed, but script date check available - using script date")
            return script_date_check
        
        # Fallback 4: Use URL date check if available
        if url_date_check is not None:
            print(f"    >> Date check failed, but URL date check available - using URL date")
            return url_date_check
        
        # Fallback 4: For Futu news with time-only fallback, default to True if check fails
        if is_futu_news and futu_fallback_check:
            print(f"    >> Date check failed, but time-only pattern detected - treating as today's news")
            return True
        return False  # Default to False if check fails


async def extract_publication_date(client, html_content, url):
    """Extract the actual publication date from article HTML
    
    Args:
        client: OpenAI client
        html_content: HTML content of the article
        url: URL of the article
    
    Returns:
        datetime object if date found, None otherwise
    """
    if not html_content:
        return None
    
    from datetime import datetime
    import re
    
    # First, try to extract date from URL (most reliable for some sites)
    url_date_pattern = r'/(\d{4})[/-](\d{1,2})[/-](\d{1,2})/'
    url_match = re.search(url_date_pattern, url)
    if url_match:
        try:
            url_year = int(url_match.group(1))
            url_month = int(url_match.group(2))
            url_day = int(url_match.group(3))
            return datetime(url_year, url_month, url_day)
        except (ValueError, IndexError):
            pass
    
    # Extract text from HTML
    clean_text = remove_html_tags(html_content)
    if len(clean_text) > 50000:
        clean_text = clean_text[:50000] + "..."
    
    today = datetime.now()
    today_str = today.strftime("%B %d, %Y")
    
    prompt = f"""
Extract the publication date from this article.

Today's date is: {today_str}

Article URL: {url}

Article content:
{clean_text}

Find the publication date, release date, or "Published" date in the article. This could be:
- A date like "January 20, 2026" or "Jan. 20, 2026"
- A timestamp
- A date in metadata or article header
- Any date that indicates when this article was published

Return ONLY the date in this exact format: YYYY-MM-DD (e.g., "2026-01-20")
If you cannot find a date, return "NOT_FOUND".
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        
        if result == "NOT_FOUND" or not result:
            return None
        
        # Parse the date
        try:
            return datetime.strptime(result, "%Y-%m-%d")
        except ValueError:
            # Try other formats
            date_formats = [
                "%B %d, %Y",  # January 20, 2026
                "%b %d, %Y",  # Jan 20, 2026
                "%d %B %Y",   # 20 January 2026
                "%Y/%m/%d",   # 2026/01/20
                "%m/%d/%Y",   # 01/20/2026
            ]
            for fmt in date_formats:
                try:
                    return datetime.strptime(result, fmt)
                except ValueError:
                    continue
            return None
    except Exception as e:
        print(f"      WARNING: Error extracting publication date: {e}")
        return None


async def generate_article_summary(client, headline, url, html_content, news_type=None):
    """Generate a summary of an article from its HTML content
    
    Args:
        client: OpenAI client
        headline: Article headline
        url: Article URL
        html_content: HTML content of the article
        news_type: Optional news type (e.g., "tech_news", "financial_news") for topic-specific prompts
    """
    clean_text = remove_html_tags(html_content)
    
    # Limit text length for LLM
    if len(clean_text) > 10000:
        clean_text = clean_text[:10000] + "..."
    
    # Topic-specific summary instructions
    topic_instructions = ""
    if news_type == "tech_news":
        topic_instructions = """
INVESTMENT-FOCUSED SUMMARY REQUIREMENTS FOR TECH NEWS:
- Emphasize investment-relevant details: funding amounts, valuations, IPO information, market size
- Highlight technical breakthroughs that could impact market positions
- Include company names, product names, and key metrics (performance numbers, market share, etc.)
- Focus on implications for tech/hardware/AI investment decisions
- Mention competitive positioning and market dynamics
- Include regulatory or policy implications affecting investments
"""
    elif news_type == "financial_news":
        topic_instructions = """
INVESTMENT-FOCUSED SUMMARY REQUIREMENTS FOR FINANCIAL NEWS:
- Include specific numbers: stock prices, market values, revenue, profit, growth rates
- Highlight market movements and their magnitude (percentage changes, dollar amounts)
- Emphasize implications for investment decisions
- Include company valuations, market cap changes, and financial metrics
- Mention economic indicators and their significance
- Focus on actionable intelligence for investment professionals
"""
    elif news_type == "hk_news":
        topic_instructions = """
INVESTMENT-FOCUSED SUMMARY REQUIREMENTS FOR HONG KONG NEWS:
- Emphasize policy and regulatory changes affecting investments
- Include economic data and market implications
- Highlight business environment changes
- Focus on cross-border implications (Mainland China-HK)
- Mention social and political developments affecting investment climate
"""
    elif news_type == "ar_ai_glasses_news":
        topic_instructions = """
SUMMARY REQUIREMENTS — AR / AI GLASSES ONLY:
- Focus on product, platform, optics, supply chain, partnerships, and regulation affecting AR glasses or smart glasses.
- If the article is primarily about VR games, PC VR, or unrelated entertainment, state that briefly and note it is out of scope (still summarize the AR-relevant angle if any).
"""

    prompt = f"""
Given this news article:

Headline: {headline}
URL: {url}

Article content:
{clean_text}

Generate a concise 2-3 sentence summary of this article. Focus on the key facts and implications.
{topic_instructions}

IMPORTANT REQUIREMENTS FOR IPO-RELATED NEWS:
- If this article is about an IPO (Initial Public Offering), you MUST include the IPO size/proceeds in the summary
- Look for IPO size information in the article, which may be referred to as:
  * "IPO size"
  * "proceeds"
  * "gross proceeds"
  * "net proceeds"
  * "offering size"
  * "fundraising amount"
- If the IPO size is not directly stated but the article mentions:
  * Number of shares issued AND IPO price → Calculate: IPO size = number of shares × IPO price
  * Example: If 10 million shares at $20 per share → IPO size = $200 million
- CRITICAL: Do NOT invent or make up IPO size numbers if they are not available in the article. Only include IPO size if it is explicitly stated or can be calculated from the provided information (shares × price).
- If IPO size information is not available and cannot be calculated, simply omit it from the summary rather than guessing.

CRITICAL: Do NOT invent any numbers, facts, or details that are not explicitly stated in the article. Only use information that is clearly provided in the article content.
"""
    
    try:
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"      [ERROR] Error generating summary: {e}")
        return ""


async def process_news_site(client, website, date_filter_mode, special_handling=None, enable_early_stop=False, skip_caching=False):
    """Process a single news site: extract headlines, match links, fetch article HTML
    
    Args:
        skip_caching: If True, don't cache links (for use by company-specific crawlers that handle caching after relevance checks)
    """
    print(f"\n{'='*80}")
    print(f"Processing: {website}")
    print('='*80)
    
    special_handling = special_handling or {}
    is_36kr = special_handling.get("is_36kr", False)
    is_futu = "futunn.com" in website or "futu" in website.lower()
    
    # Step 1: Extract HTML
    print("Step 1: Extracting HTML...")
    html_dict = extract_html.get_raw_html(website)
    
    if not html_dict or not html_dict.get("html"):
        print(f"ERROR: Failed to retrieve HTML from {website}")
        return None
    
    html_string = html_dict["html"]
    clean_text = remove_html_tags(html_string)
    
    # For 36Kr, use clean text if HTML is large
    if len(html_string) > 200000:
        html_string_input = clean_text[:200000] if is_36kr else clean_text
    else:
        html_string_input = html_string
    
    # Step 2: Extract top headlines
    print("Step 2: Extracting top headlines...")
    headlines = await extract_top_headlines(client, website, html_string_input, special_handling)
    
    if not headlines:
        print(f"ERROR: No headlines extracted from {website}")
        return None
    
    # Step 3: Get links from HTML
    print("Step 3: Extracting links from HTML...")
    links_on_page = extract_links_from_html(html_string, website)
    
    if not links_on_page or len(links_on_page.strip()) == 0:
        print(f"ERROR: No links extracted from {website}")
        return None
    
    links_total_chars = len(links_on_page)
    print(f"Extracted {links_total_chars:,} characters of links data")
    
    # Extract relative time indicators from listing page (e.g., "3 hours ago")
    # These are often only on the listing page, not the article page
    listing_page_text = clean_text
    relative_time_patterns = [
        r'\b(\d+)\s*(?:hour|hours|hr|hrs|h)\s+ago\b',
        r'\b(\d+)\s*(?:minute|minutes|min|mins|m)\s+ago\b',
        r'\b(?:just|recently)\s+(?:published|posted|updated)\b',
        r'\b(?:today|this\s+(?:morning|afternoon|evening))\b'
    ]
    
    # Find relative time indicators for each headline
    headline_relative_times = {}
    for headline in headlines:
        # Search for the headline in the listing page text, then look for relative time nearby
        headline_lower = headline.lower()
        # Try exact match first
        idx = listing_page_text.lower().find(headline_lower)
        if idx < 0:
            # Try partial match - use first 30 characters of headline
            headline_partial = headline_lower[:30]
            idx = listing_page_text.lower().find(headline_partial)
        
        if idx >= 0:
            # Look in a 500-character window around the headline for relative time
            search_start = max(0, idx - 250)
            search_end = min(len(listing_page_text), idx + len(headline) + 500)
            context = listing_page_text[search_start:search_end]
            
            for pattern in relative_time_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    headline_relative_times[headline] = match.group(0)
                    print(f"    DEBUG: Found relative time '{match.group(0)}' for headline: {headline[:50]}...")
                    break
    
    # Step 4: Match headlines to links and fetch article HTML
    print("Step 4: Matching headlines to links and fetching article HTML...")
    news_items = []
    
    # Track statistics
    stats = {
        'total_headlines': len(headlines),
        'no_link_found': 0,
        'section_page_filtered': 0,
        'html_fetch_failed': 0,
        'date_filtered': 0,
        'success': 0
    }
    
    for i, headline in enumerate(headlines, 1):
        # Safely print headline (handle Unicode)
        headline_display = headline[:60] if len(headline) > 60 else headline
        try:
            print(f"  [{i}/{len(headlines)}] Processing headline: {headline_display}...")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            headline_ascii = headline_display.encode('ascii', 'ignore').decode('ascii')
            print(f"  [{i}/{len(headlines)}] Processing headline: {headline_ascii}...")
        
        # Step 5: Match headline to link
        print(f"    >> Matching headline to article link...")
        url = await match_headline_to_link(client, headline, links_on_page, website)
        
        if not url:
            stats['no_link_found'] += 1
            print(f"    [FAIL] No link found for headline: {headline[:60]}...")
            # Try to find partial matches in the links for debugging
            headline_words = [w.lower() for w in headline.split() if len(w) > 4][:3]
            print(f"    DEBUG: Searching for keywords {headline_words} in extracted links...")
            found_keywords = []
            for word in headline_words:
                if word in links_on_page.lower():
                    found_keywords.append(word)
                    # Try to extract a sample link containing this keyword
                    idx = links_on_page.lower().find(word)
                    if idx >= 0:
                        snippet_start = max(0, idx - 100)
                        snippet_end = min(len(links_on_page), idx + 200)
                        snippet = links_on_page[snippet_start:snippet_end]
                        print(f"    DEBUG: Found keyword '{word}' in links snippet: ...{snippet}...")
            if not found_keywords:
                print(f"    DEBUG: None of the headline keywords were found in extracted links")
            # Note: Can't save to cache if no URL found
            continue
        
        # Minimal validation: only reject obvious non-article pages (navigation, menus, etc.)
        # If we extracted a headline and matched it to a link, it should be an article.
        # The date check is the real filter - if it passes date check, it's valid.
        url_path = urlparse(url).path
        path_segments = [s for s in url_path.split('/') if s]  # Remove empty segments
        
        # Only reject obvious navigation/menu pages, not article URLs
        # These patterns indicate non-article pages regardless of site structure
        obvious_non_article_patterns = [
            '/menu/', '/select/', '/watchlist/', '/pro/', '/livestream/',
            '/tag/', '/author/', '/category/', '/section/', '/search/',
            '/login/', '/signup/', '/register/', '/account/', '/profile/'
        ]
        
        is_section_page = any(pattern in url_path for pattern in obvious_non_article_patterns)
        
        # Also reject if URL path is extremely short (1 segment) and matches common section patterns
        # But only if it's NOT part of a longer path (e.g., /business/tech/article is fine)
        if len(path_segments) == 1:
            single_segment = '/' + path_segments[0]
            if single_segment in ['/business', '/tech', '/technology', '/markets', '/politics', '/video']:
                is_section_page = True
        
        if is_section_page:
            stats['section_page_filtered'] += 1
            print(f"    [SKIP] Matched URL appears to be a navigation/menu page, skipping: {url}")
            # Save to cache (not a valid article page)
            save_seen_link(website, url, headline, was_relevant=False)
            continue
        
        print(f"    [OK] Found article link: {url}")
        
        # Check if this link has been seen before (cache check) - only if not skipping cache
        if not skip_caching and is_link_seen(website, url):
            print(f"    [CACHE] Link already processed before - skipping HTML fetch and date check")
            # Still save to cache to update last_seen timestamp
            save_seen_link(website, url, headline, was_relevant=None)
            continue
        
        # Step 6: Fetch article HTML
        print(f"    >> Fetching article HTML from {url}...")
        article_html = await fetch_article_html(url)
        
        if not article_html:
            stats['html_fetch_failed'] += 1
            print(f"    [FAIL] Failed to fetch article HTML")
            # Save to cache even if HTML fetch failed (so we don't retry) - only if not skipping cache
            if not skip_caching:
                save_seen_link(website, url, headline, was_relevant=False)
            continue
        
        html_size = len(article_html)
        html_size_kb = html_size / 1024
        print(f"    [OK] Fetched article HTML ({html_size:,} chars, {html_size_kb:.1f} KB)")
        
        # Step 7: Extract text from HTML for processing
        clean_text = remove_html_tags(article_html)
        text_size = len(clean_text)
        text_size_kb = text_size / 1024
        print(f"    >> Extracted text from HTML ({text_size:,} chars, {text_size_kb:.1f} KB)")
        
        # Step 8: Check date if needed
        if date_filter_mode != "none":
            date_check_msg = "today" if date_filter_mode == "today" else "today or yesterday"
            print(f"    >> Checking if article is from {date_check_msg}...")
            
            # Check if we found relative time for this headline on the listing page
            relative_time_info = ""
            if headline in headline_relative_times:
                relative_time = headline_relative_times[headline]
                relative_time_info = f"\nIMPORTANT: On the listing page, this article shows '{relative_time}' which indicates it was published TODAY. Use this as the primary indicator.\n"
                print(f"    >> Found relative time '{relative_time}' on listing page - treating as today's news")
            
            # Add relative time info to special_handling
            article_special_handling = special_handling.copy() if special_handling else {}
            if relative_time_info:
                article_special_handling["listing_page_relative_time"] = relative_time_info
            
            is_recent = await is_article_from_today(client, article_html, url, date_filter_mode, article_special_handling)
            
            if not is_recent:
                stats['date_filtered'] += 1
                print(f"    [SKIP] Article is not from {date_check_msg}, skipping")
                print(f"    DEBUG: Article was filtered out by date check (is_futu={is_futu})")
                # Save to cache (not relevant for today/yesterday) - only if not skipping cache
                if not skip_caching:
                    save_seen_link(website, url, headline, was_relevant=False)
                # Early stop only for press release, Futu, and regulatory crawlers where we're sure articles are ordered newest to oldest
                if enable_early_stop:
                    print(f"    [STOP] Stopping processing - articles are ordered newest to oldest, so remaining articles will also be too old")
                    break
                else:
                    print(f"    [CONTINUE] Continuing to check remaining articles (early stop disabled for this crawler)")
                continue  # CRITICAL: Skip adding this article to results
            
            print(f"    [OK] Article is from {date_check_msg}")
        
        news_items.append(NewsItem(
            headline=headline,
            url=url,
            html=article_html
        ))
        stats['success'] += 1
        # Save to cache (relevant article) - only if not skipping cache
        if not skip_caching:
            save_seen_link(website, url, headline, was_relevant=True)
        print(f"    [OK] Article HTML processed and added to results ({stats['success']} total)")
    
    print(f"\n{'='*80}")
    print(f"Processed {website}: {len(news_items)} articles with full content")
    print(f"\nStatistics:")
    print(f"  - Total headlines processed: {stats['total_headlines']}")
    print(f"  - No link found: {stats['no_link_found']}")
    print(f"  - Filtered as section page: {stats['section_page_filtered']}")
    print(f"  - HTML fetch failed: {stats['html_fetch_failed']}")
    print(f"  - Filtered by date: {stats['date_filtered']}")
    print(f"  - Successfully processed: {stats['success']}")
    
    if len(news_items) == 0:
        print(f"\n[WARNING] No articles extracted!")
        print(f"  - Headlines extracted: {len(headlines)}")
        print(f"  - Links extracted: {len(links_on_page) if links_on_page else 0} characters")
        if headlines:
            print(f"  - Sample headlines: {headlines[:3]}")
        print(f"\n  Possible issues:")
        if stats['no_link_found'] > 0:
            print(f"    • {stats['no_link_found']} headlines had no matching links - check link extraction")
        if stats['section_page_filtered'] > 0:
            print(f"    • {stats['section_page_filtered']} URLs filtered as section pages - may need URL pattern adjustment")
        if stats['html_fetch_failed'] > 0:
            print(f"    • {stats['html_fetch_failed']} articles failed HTML fetch - check URLs")
        if stats['date_filtered'] > 0:
            print(f"    • {stats['date_filtered']} articles filtered by date check - check date detection logic")
    print('='*80)
    
    return SiteNews(
        site=website,
        news_items=news_items
    )


async def crawl_news_from_config(
    config_key: str,
    websites_override: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Crawl news based on configuration key
    
    Args:
        config_key: Component key in component_config.json (e.g., "top_news", "tech_news", "financial_news")
        websites_override: If set, replaces configured websites list (used by ar_ai_glasses_news, etc.)
    
    Returns:
        List of news items
    """
    # Load component config
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "component_config.json"
    )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        component_config = json.load(f)
    
    if config_key not in component_config.get("components", {}):
        raise ValueError(f"Component '{config_key}' not found in component_config.json")
    
    component = component_config["components"][config_key]
    crawler_config = component.get("crawler", {})
    inputs = crawler_config.get("inputs", {})
    
    # Extract values (support both "value" and "default" keys)
    websites = inputs.get("websites", {}).get("value", inputs.get("websites", {}).get("default", []))
    if websites_override is not None:
        websites = websites_override
    date_filter_mode = inputs.get("date_filter_mode", {}).get("value", inputs.get("date_filter_mode", {}).get("default", "none"))
    global_special_handling = inputs.get("special_handling", {}).get("value", inputs.get("special_handling", {}).get("default", {}))
    news_type = config_key

    # Dedicated AR newsletter CSV: start fresh each run so Google + site rows do not duplicate across days in one file
    if config_key == "ar_ai_glasses_news":
        ar_csv = get_csv_path("ar_ai_glasses_news")
        if ar_csv.exists():
            ar_csv.unlink()
    
    print(f"Starting {news_type} crawl...")
    print(f"Websites: {websites}")
    print(f"Date filter mode: {date_filter_mode}")
    
    client = initialize_openai_client()
    
    news_items = []
    batch_items = []  # Collect items for batch save
    
    # Process each website
    for website in websites:
        # Get special handling for this specific website
        website_special_handling = {}
        for domain, handling in global_special_handling.items():
            if domain in website:
                website_special_handling.update(handling)
        
        # Add news_type to special_handling so extract_top_headlines can use topic-specific prompts
        website_special_handling["news_type"] = news_type
        
        # IMPORTANT: enable_early_stop=False for generic news crawlers (same as test script)
        # Early stop should only be used for press release, Futu, and regulatory crawlers
        site_news = await process_news_site(
            client, 
            website, 
            date_filter_mode, 
            special_handling=website_special_handling, 
            enable_early_stop=False
        )
        
        if site_news and site_news.news_items:
            print(f"\n  >> Processing {len(site_news.news_items)} articles from {website}...")
            print(f"  >> Generating summaries and saving to CSV...")
            
            today_obj = datetime.now()
            # Use unambiguous English date format: "January 8, 2025"
            month_names = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"]
            date_str = f"{month_names[today_obj.month - 1]} {today_obj.day}, {today_obj.year}"
            
            for i, news_item in enumerate(site_news.news_items, 1):
                # Safely print headline (handle Unicode)
                headline_display = news_item.headline[:60] if len(news_item.headline) > 60 else news_item.headline
                try:
                    print(f"    [{i}/{len(site_news.news_items)}] Processing article: {headline_display}...")
                except UnicodeEncodeError:
                    # Fallback for Windows console encoding issues
                    headline_ascii = headline_display.encode('ascii', 'ignore').decode('ascii')
                    print(f"    [{i}/{len(site_news.news_items)}] Processing article: {headline_ascii}...")
                print(f"      >> Generating summary from HTML...")
                
                summary = await generate_article_summary(
                    client, 
                    news_item.headline, 
                    news_item.url, 
                    news_item.html,
                    news_type=news_type
                )
                
                if summary:
                    summary_size = len(summary)
                    print(f"      [OK] Generated summary ({summary_size:,} chars)")
                    
                    # Add to batch
                    batch_items.append([date_str, news_item.headline, news_item.url, summary])
                    
                    news_items.append({
                        "date": today_obj.strftime("%Y-%m-%d"),
                        "headline": news_item.headline,
                        "link": news_item.url,
                        "summary": summary
                    })
                    print(f"      >> Added to CSV batch ({len(batch_items)} items so far)")
                else:
                    print(f"      [FAIL] Failed to generate summary, skipping article")
        else:
            print(f"WARNING: No news items extracted from {website}")
    
    # Batch save to CSV
    if batch_items:
        print(f"\n>> Saving {len(batch_items)} {news_type} items to CSV...")
        try:
            batch_save_news_items_to_csv(news_type, batch_items)
            print(f"[OK] Saved {len(batch_items)} {news_type} items to {news_type}.csv")
        except Exception as e:
            print(f"❌ Error saving batch to CSV: {e}")
    
    print(f"\n{news_type} crawl complete. Found {len(news_items)} items")
    return news_items


# Convenience functions for backward compatibility
async def crawl_top_news() -> List[Dict[str, Any]]:
    """Crawl top news - convenience wrapper"""
    return await crawl_news_from_config("top_news")


async def crawl_tech_news() -> List[Dict[str, Any]]:
    """Crawl tech news - convenience wrapper"""
    return await crawl_news_from_config("tech_news")


async def crawl_global_financial_news() -> List[Dict[str, Any]]:
    """Crawl global financial news - convenience wrapper"""
    return await crawl_news_from_config("financial_news")


async def crawl_hk_news() -> List[Dict[str, Any]]:
    """Crawl Hong Kong news - convenience wrapper"""
    return await crawl_news_from_config("hk_news")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        config_key = sys.argv[1]
        asyncio.run(crawl_news_from_config(config_key))
    else:
        print("Usage: python generic_news_crawler.py <config_key>")
        print("Available config keys: top_news, tech_news, financial_news")

