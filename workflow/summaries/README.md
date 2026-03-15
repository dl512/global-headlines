# Summaries Directory

This directory contains all generated summaries organized by component type.

## Structure

```
summaries/
├── global_news/
│   └── global_news_summary_YYYYMMDD.md
├── top_news/
│   └── top_news_summary_YYYYMMDD.md
├── financial_news/
│   └── financial_news_summary_YYYYMMDD.md
├── market_snapshot/
│   └── market_snapshot_summary_YYYYMMDD.md
├── tech_news/
│   └── tech_news_summary_YYYYMMDD.md
├── regulatory/
│   └── regulatory_summary_YYYYMMDD.md
└── hk_ipo/
    └── hk_ipo_summary_YYYYMMDD.md
```

## File Naming Convention

Files are named using the pattern: `{component}_summary_{YYYYMMDD}.md`

Example: `global_news_summary_20251226.md`

## Usage

Summaries are automatically saved when running `workflow/run_newsletter_pipeline.py`.

You can also use the `summary_storage` module to save summaries programmatically:

```python
from common.summary_storage import save_summary, get_latest_summary

# Save a summary
filepath = save_summary("global_news", summary_content)

# Get the latest summary for a component
latest_file = get_latest_summary("global_news")
```

## Migration Note

The old folders `workflow/global_news/` and `workflow/daily_summaries/` have been moved to `archive/old_summaries/` for historical reference. All new summaries are saved in this structured format.

