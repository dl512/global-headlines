"""
Common Playwright utilities
"""

PLAYWRIGHT_INSTALL_HINT = (
    "Playwright browser runtime not found.\n"
    "Run this ONCE to install the Chromium runtime:\n"
    "  python -m playwright install chromium\n"
)


def is_probably_missing_playwright_browser(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "playwright" in msg and ("executable doesn't exist" in msg or "browser_type.launch" in msg)

