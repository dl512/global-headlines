# Google Sheets Naming Convention

This document describes the sheet naming convention used in the newsletter pipeline.

## Sheet Names

| Old Name | New Name | Purpose |
|----------|----------|---------|
| Sheet1 | **Countries** | List of websites for crawling global news (Country, Newspaper, Website) |
| Sheet2 | **GlobalNews** | Global news headlines from countries list |
| Sheet3 | **TopNews** | Top news (currently unused, data goes to NewsData) |
| Sheet4 | **NewsData** | Shared sheet for multiple news types (top_news, financial_news, tech_news) with "News Type" column |
| Sheet5 | **Market** | Market snapshot data (stock prices, indices) |
| Sheet6 | *(unused)* | Tech news now goes to NewsData |
| Sheet7 | **Regulatory** | HKEX regulatory announcements |
| Sheet8 | **HKIPO** | HK IPO news |

## Notes

- **Countries**: Contains the source configuration (renamed from Sheet1 by user)
- **NewsData**: Shared sheet for top_news, financial_news, and tech_news. Uses column E ("News Type") to distinguish between types.
- All other sheets use short, descriptive names instead of generic "SheetX" format.

## Migration

When creating new sheets in Google Sheets, use the names from the "New Name" column above. The code will automatically create sheets with these names if they don't exist.

