import html as html_lib
import os
import re
import sys
from typing import Any, Dict, List
from urllib.parse import urljoin

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.playwright_utils import PLAYWRIGHT_INSTALL_HINT, is_probably_missing_playwright_browser


AASTOCKS_IPO_NEWS_URL = "https://www.aastocks.com/en/stocks/market/ipo/iponews.aspx"
AASTOCKS_ROOT = "https://www.aastocks.com"
AASTOCKS_FOOTER = "~AAStocks Financial NewsWeb Site: www.aastocks.com"


def _normalize_date_to_ddmmyyyy(text: str) -> str:
    """
    Extract yyyy/mm/dd from text and convert to dd/mm/yyyy.
    If not found, returns "[Unknown]".
    """
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", text or "")
    if not m:
        return "[Unknown]"
    y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
    return f"{d:02d}/{mo:02d}/{y}"


async def scrape_aastocks_ipo_news(*, headless: bool = True, timeout_ms: int = 60_000) -> List[Dict[str, Any]]:
    """
    Scrape AAStocks IPO news list.

    Output items:
      {title, date, content, link, image_url}
    """
    """
    Scrape AAStocks IPO news list.

    Output items:
      {title, date, content, link, image_url}
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()
            await page.goto(AASTOCKS_IPO_NEWS_URL, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for blocks
            await page.wait_for_selector("div[ref^='NOW.']", timeout=timeout_ms)
            await page.wait_for_timeout(800)

            items: List[Dict[str, Any]] = []
            blocks = await page.query_selector_all("div[ref^='NOW.']")

            for block in blocks:
                item: Dict[str, Any] = {"title": "", "date": "", "content": "", "link": "", "image_url": None}

                # Title + link
                title_link = None
                try:
                    title_link = await block.query_selector('a[id*="lnkNews_"]:not([id*="lnkNewsImage"])')
                except Exception:
                    title_link = None

                if title_link:
                    raw_title = (await title_link.get_attribute("title")) or (await title_link.inner_text()) or ""
                    clean_title = html_lib.unescape(raw_title).replace("<IPO>", "").strip()
                    item["title"] = clean_title or "[No title]"

                    href = await title_link.get_attribute("href")
                    if href:
                        item["link"] = href if href.startswith("http") else urljoin(AASTOCKS_ROOT, href)
                else:
                    item["title"] = "[No title]"

                # Date
                try:
                    time_el = await block.query_selector(".newstime4 .inline_block")
                    time_text = (await time_el.inner_text()) if time_el else ""
                    item["date"] = _normalize_date_to_ddmmyyyy(time_text)
                except Exception:
                    item["date"] = "[Unknown]"

                # Content
                try:
                    content_el = await block.query_selector(".newscontent4")
                    text = (await content_el.inner_text()).strip() if content_el else ""
                    if text.endswith(AASTOCKS_FOOTER):
                        text = text[: -len(AASTOCKS_FOOTER)].strip()
                    item["content"] = text or "[No content]"
                except Exception:
                    item["content"] = "[No content]"

                # Image (optional)
                try:
                    img = await block.query_selector(".newsImage4a img")
                    if img:
                        item["image_url"] = await img.get_attribute("src")
                except Exception:
                    pass

                if item["title"] and item["title"] not in {"[No title]", "[Title error]"}:
                    items.append(item)

            await context.close()
            await browser.close()
            return items

    except PlaywrightTimeoutError:
        raise RuntimeError(f"Timed out loading AAStocks page: {AASTOCKS_IPO_NEWS_URL}")
    except Exception as e:
        if is_probably_missing_playwright_browser(e):
            raise RuntimeError(PLAYWRIGHT_INSTALL_HINT) from e
        raise


async def fetch_aastocks_ipo_news(dates: List[str] = None, *, headless: bool = True, timeout_ms: int = 60_000) -> List[Dict[str, Any]]:
    """
    Fetch AAStocks IPO news and filter by dates.
    
    Args:
        dates: List of dates in DD/MM/YYYY format to filter news (optional)
        headless: Run browser in headless mode
        timeout_ms: Timeout in milliseconds
    
    Returns:
        List of IPO news items with keys: headline, url, summary, date
    """
    items = await scrape_aastocks_ipo_news(headless=headless, timeout_ms=timeout_ms)
    
    # Convert to expected format
    result = []
    for item in items:
        result.append({
            'headline': item.get('title', ''),
            'url': item.get('link', ''),
            'summary': item.get('content', ''),
            'date': item.get('date', ''),
            'image_url': item.get('image_url')
        })
    
    # Filter by dates if provided
    if dates:
        date_set = set(dates)
        result = [item for item in result if item.get('date') in date_set]
    
    return result

