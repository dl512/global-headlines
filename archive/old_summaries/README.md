# Old Summaries Archive

This folder contains the old summary folder structure that has been replaced by the new `workflow/summaries/` structure.

## Contents

- **global_news/** - Old global news summaries (now in `workflow/summaries/global_news/`)
- **daily_summaries/** - Old daily/top news summaries (now in `workflow/summaries/top_news/`)

## Migration Date

Archived on: December 26, 2025

## New Structure

All new summaries are saved in `workflow/summaries/` with the following structure:
- `workflow/summaries/global_news/global_news_summary_YYYYMMDD.md`
- `workflow/summaries/top_news/top_news_summary_YYYYMMDD.md`
- `workflow/summaries/financial_news/financial_news_summary_YYYYMMDD.md`
- `workflow/summaries/market_snapshot/market_snapshot_summary_YYYYMMDD.md`
- `workflow/summaries/tech_news/tech_news_summary_YYYYMMDD.md`
- `workflow/summaries/regulatory/regulatory_summary_YYYYMMDD.md`
- `workflow/summaries/hk_ipo/hk_ipo_summary_YYYYMMDD.md`

## Backward Compatibility

The `workflow/generate_newsletter.py` script has been updated to:
1. First look in the new `workflow/summaries/` structure
2. Fallback to these archived folders if files are not found in the new location

This ensures backward compatibility while transitioning to the new structure.

