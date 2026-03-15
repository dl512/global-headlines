import os
import sys
from typing import Any, Dict, List
from urllib.parse import urljoin

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.playwright_utils import PLAYWRIGHT_INSTALL_HINT, is_probably_missing_playwright_browser


HKEX_LCI_URL = "https://www1.hkexnews.hk/listedco/listconews/index/lci.html?lang=en"


def _process_row_data(date_str: str, time_str: str, code: str, company: str, headline_text: str, link: str) -> Dict[str, Any]:
    row_data: Dict[str, Any] = {
        "date": (date_str or "").strip(),
        "time": (time_str or "").strip(),
        "code": (code or "").strip(),
        "company": (company or "").strip(),
        "category": "",
        "title": "",
        "link": (link or "").strip(),
    }

    headline_text = (headline_text or "").strip()
    if "\n" in headline_text:
        parts = headline_text.split("\n", 1)
        if len(parts) == 2:
            category, title = parts
            row_data["category"] = category.strip()
            title = title.split("...More")[0].strip()
            row_data["title"] = title
        else:
            row_data["title"] = headline_text.split("...More")[0].strip()
    else:
        row_data["title"] = headline_text.split("...More")[0].strip()

    return row_data


async def _try_accept_cookies(page) -> None:
    # A best-effort list of common accept selectors.
    candidates = [
        "#onetrust-accept-btn-handler",
        "button#onetrust-accept-btn-handler",
        "button:has-text(\"Accept All\")",
        "button:has-text(\"Accept\")",
        "button:has-text(\"I Accept\")",
        "button:has-text(\"Agree\")",
        "text=Accept All",
        "text=Accept",
    ]
    for selector in candidates:
        try:
            el = await page.query_selector(selector)
            if el:
                await el.click(timeout=1500)
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue


async def scrape_hkex_listedco_announcements(
    url: str = HKEX_LCI_URL,
    *,
    headless: bool = True,
    timeout_ms: int = 60_000,
) -> List[Dict[str, Any]]:
    """
    Scrape HKEX Listed Company announcements table.

    Notes:
    - This page is dynamic; we use Playwright to click the "7 DAYS" filter if possible.
    - Output is a list of dicts: {date,time,code,company,category,title,link}
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            await _try_accept_cookies(page)

            # Best-effort click "7 DAYS" (matches the notebook logic)
            try:
                await page.click('label[for="Daterange2"]', timeout=5_000)
                await page.wait_for_timeout(1500)
            except Exception:
                pass

            await page.wait_for_selector("table tr td", timeout=timeout_ms)
            await page.wait_for_timeout(1000)

            extracted: List[Dict[str, Any]] = []
            rows = await page.query_selector_all("table tr")

            for row in rows:
                cells = await row.query_selector_all("td")
                if not cells or len(cells) < 4:
                    continue

                date_time_text = (await cells[0].inner_text()).strip()
                code_text = (await cells[1].inner_text()).strip()
                company_text = (await cells[2].inner_text()).strip()
                headline_text = (await cells[3].inner_text()).strip()

                # Find PDF link within headline cell
                link = ""
                try:
                    anchors = await cells[3].query_selector_all("a")
                    for a in anchors:
                        href = await a.get_attribute("href")
                        if href and ".pdf" in href.lower():
                            link = urljoin(url, href)
                            break
                except Exception:
                    pass

                # Parse date/time
                date_str = date_time_text
                time_str = ""
                if " " in date_time_text:
                    date_str, time_str = date_time_text.split(" ", 1)

                # Handle multi-company rows (code/company may contain newline-separated entries)
                if "\n" in code_text and "\n" in company_text:
                    codes = [c.strip() for c in code_text.split("\n") if c.strip()]
                    companies = [c.strip() for c in company_text.split("\n") if c.strip()]
                    for code, company in zip(codes, companies):
                        extracted.append(_process_row_data(date_str, time_str, code, company, headline_text, link))
                else:
                    extracted.append(_process_row_data(date_str, time_str, code_text, company_text, headline_text, link))

            await context.close()
            await browser.close()

            # Very light sanity filter: remove rows without a title
            return [r for r in extracted if (r.get("title") or "").strip()]

    except PlaywrightTimeoutError:
        raise RuntimeError(f"Timed out loading HKEX page: {url}")
    except Exception as e:
        if is_probably_missing_playwright_browser(e):
            raise RuntimeError(PLAYWRIGHT_INSTALL_HINT) from e
        raise


async def fetch_hkex_announcements(dates: List[str] = None, *, headless: bool = True, timeout_ms: int = 60_000) -> List[Dict[str, Any]]:
    """
    Fetch HKEX listed company announcements and filter by dates.
    
    Args:
        dates: List of dates in DD/MM/YYYY format to filter announcements (optional)
        headless: Run browser in headless mode
        timeout_ms: Timeout in milliseconds
    
    Returns:
        List of announcement items with keys: date, time, code, company, category, title, link
    """
    items = await scrape_hkex_listedco_announcements(headless=headless, timeout_ms=timeout_ms)
    
    # Filter by dates if provided
    if dates:
        date_set = set(dates)
        items = [item for item in items if item.get('date') in date_set]
    
    return items

