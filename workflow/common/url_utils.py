"""
URL utilities for newsletter output.
Shortens fragile URLs (e.g. with percent-encoded Chinese slugs) to ID-only form
so they don't break when opened on mobile or after re-encoding.
"""

import re
from urllib.parse import urlparse, urlunparse


# Domains where we shorten URLs to scheme + netloc + /section/numeric_id
# (drop the slug so percent-encoded paths can't get corrupted)
SHORTEN_URL_DOMAINS = [
    "stheadline.com",
    "www.stheadline.com",
]


def normalize_display_url(url: str) -> str:
    """Return a mobile-safe display URL for known fragile domains.

    For stheadline.com (and similar), the path is like /politics/3546872/ENCODED_SLUG.
    We keep only /politics/3546872 so the link cannot be corrupted by encoding.

    Args:
        url: Full URL (may be already corrupted or correct).

    Returns:
        Short URL for known domains, or original URL unchanged.
    """
    if not url or not url.strip():
        return url
    url = url.strip()
    try:
        parsed = urlparse(url)
        netloc_lower = (parsed.netloc or "").lower()
        path = parsed.path or ""
        for domain in SHORTEN_URL_DOMAINS:
            if domain in netloc_lower or netloc_lower.endswith("." + domain):
                # Match path like /politics/3546872 or /politics/3546872/anything
                match = re.match(r"^/([^/]+)/(\d+)(?:/.*)?$", path)
                if match:
                    section, article_id = match.group(1), match.group(2)
                    new_path = f"/{section}/{article_id}"
                    return urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        new_path,
                        "",  # params
                        parsed.query,
                        parsed.fragment,
                    ))
                break
    except Exception:
        pass
    return url


def normalize_markdown_links(markdown_text: str) -> str:
    """Replace every markdown link URL ](URL) with normalize_display_url(URL).

    Prevents encoding-corrupted links (e.g. stheadline.com with Chinese slugs)
    from breaking on mobile.

    Args:
        markdown_text: Markdown string that may contain [text](url) links.

    Returns:
        Markdown with link URLs normalized.
    """
    if not markdown_text:
        return markdown_text

    # Match ]( ... ) - the URL part of [text](url)
    pattern = re.compile(r"\]\s*\(\s*([^)\s]+)\s*\)")

    def replace_url(match: re.Match) -> str:
        url = match.group(1).strip()
        normalized = normalize_display_url(url)
        return f"]({normalized})"

    return pattern.sub(replace_url, markdown_text)
