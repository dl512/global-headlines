# User Config Structure

## Overview

The system now supports **multiple config files per user**, allowing better organization of newsletters. Each newsletter can be saved in its own file, making it easier to manage and update individual newsletters.

## File Naming Convention

Config files are stored in `workflow/config/user_configs/` with the following naming:

- **Global Newsletter**: `{user_id}_global_newsletter.json`
- **Market Briefing**: `{user_id}_market_briefing.json`
- **Custom Newsletters**: `{user_id}_custom_{newsletter_name}.json`

### Examples:
- `demo_user_global_newsletter.json`
- `demo_user_market_briefing.json`
- `demo_user_custom_tech_financial.json`
- `user123_custom_daily_update.json`

## How It Works

### When `helper.py` runs:

1. **No user_id specified**: Loads **ALL** config files from `user_configs/` folder
   - Reads all `*.json` files (excluding backups)
   - Combines all newsletters from all files
   - Base config (`newsletter_config.json`) is included as a fallback

2. **user_id specified**: Loads only that user's config files
   - Reads all `{user_id}_*.json` files
   - Combines newsletters from those files

### Config File Structure

Each config file contains:
```json
{
  "email_intro": "Optional email intro text",
  "newsletters": [
    {
      "name": "newsletter_name",
      "components": ["component1", "component2"],
      "component_customizations": {...},
      "recipients": {...},
      "email": {...},
      "language": "EN",
      "translate": false
    }
  ]
}
```

## Benefits

1. **Modular**: Each newsletter in its own file
2. **Easy Updates**: Update one newsletter without affecting others
3. **Scalable**: Can have many custom newsletters per user
4. **Backward Compatible**: Old single-file format still works

## Migration

Old format (`{user_id}_newsletter_config.json`) is still supported for backward compatibility. The system will:
- Load old format files if they exist
- New configs are saved in the new format automatically

## Example Structure

```
workflow/config/user_configs/
├── demo_user_global_newsletter.json      # Global newsletter config
├── demo_user_market_briefing.json        # Market briefing config
├── demo_user_custom_tech_news.json       # Custom tech newsletter
├── demo_user_custom_financial.json       # Custom financial newsletter
└── user123_custom_daily_update.json      # Another user's custom newsletter
```

When the pipeline runs, it will:
1. Read all these files
2. Combine all newsletters
3. Generate newsletters for each one
4. Send emails according to each newsletter's recipients

