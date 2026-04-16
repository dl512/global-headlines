"""
AR / AI glasses newsletter crawler.
Runs industry homepage crawl + targeted Google News into ar_ai_glasses_news.csv (single component).
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.corporate_news_crawler import crawl_corporate_news
from crawlers.generic_news_crawler import crawl_news_from_config


def _config_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


def _load_default_company_queries() -> List[Dict[str, Any]]:
    path = os.path.join(_config_dir(), "ar_ai_glasses_company_queries.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_component_websites_and_queries(
    websites: Optional[List[str]],
    company_configs: Optional[List[Dict[str, Any]]],
) -> tuple:
    config_path = os.path.join(_config_dir(), "component_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    inputs = data.get("components", {}).get("ar_ai_glasses_news", {}).get("crawler", {}).get("inputs", {})

    if websites is None:
        w = inputs.get("websites", {})
        websites = w.get("value", w.get("default", []))

    if company_configs is None:
        cq = inputs.get("company_configs", {})
        company_configs = cq.get("value", cq.get("default", []))

    if not company_configs:
        company_configs = _load_default_company_queries()

    return websites, company_configs


async def crawl_ar_ai_glasses_news(
    websites: Optional[List[str]] = None,
    company_configs: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Refresh ar_ai_glasses_news.csv: generic crawl for configured sites, then Google News rows.
    """
    websites, company_configs = _load_component_websites_and_queries(websites, company_configs)

    await crawl_news_from_config("ar_ai_glasses_news", websites_override=websites)
    if company_configs:
        await crawl_corporate_news(
            company_configs,
            google_news_simple_csv="ar_ai_glasses_news",
        )
    return []


if __name__ == "__main__":
    asyncio.run(crawl_ar_ai_glasses_news())
