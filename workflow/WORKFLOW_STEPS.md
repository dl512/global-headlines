# Newsletter Generation Workflow Steps

## Overview
This document describes the workflow for generating personalized newsletters based on user prompts. The system supports both base (default) newsletters and user-specific custom newsletters.

## Directory Structure

```
workflow/
├── config/
│   ├── newsletter_config.json          # Base/default newsletters
│   ├── component_config.json           # Component definitions (crawlers, summarizers)
│   ├── news_crawler_config.json       # Generic news crawler configurations
│   └── user_configs/                   # User-specific newsletter configs
│       ├── user_123_newsletter_config.json
│       ├── user_456_newsletter_config.json
│       └── ...
├── data/
│   ├── news_csv/                      # CSV files for news data
│   │   ├── top_news.csv
│   │   ├── tech_news.csv
│   │   ├── financial_news.csv
│   │   ├── regulatory.csv
│   │   ├── hk_ipo.csv
│   │   └── conversation_ai_news.csv
│   └── market_snapshot/               # Market data JSON
│       └── market_data.json
├── summaries/                         # Generated summaries
│   ├── top_news/
│   ├── tech_news/
│   └── ...
└── newsletter/                        # Generated newsletters
    ├── global_newsletter/
    ├── market_briefing/
    ├── conversation_ai_newsletter/
    └── ...
```

## Workflow Steps (Current Implementation)

### Step 1: Load User Config and Get Required Components
**Process**: Load newsletter configuration and extract all unique components needed

**Steps**:
1. Load user-specific config (or base config if no user_id)
2. Extract all newsletters from config
3. Collect all unique components across all newsletters
4. Display required components

**Example**:
- User config has 2 newsletters:
  - `global_newsletter`: ["top_news", "global_news"]
  - `market_briefing`: ["market_snapshot", "financial_news", "tech_news", "regulatory", "hk_ipo"]
- Required components: {"top_news", "global_news", "market_snapshot", "financial_news", "tech_news", "regulatory", "hk_ipo"}

**Location**: `workflow/run_newsletter_pipeline.py` → `main()` → `get_required_components()`

---

### Step 2: Crawl and Summarize Required Components
**Process**: Based on component config, crawl and summarize only the required components

**Steps**:
1. Run crawlers for required components only
2. Generate summaries for required components only
3. Save summaries to files

**Optimization**: Only processes components that are actually needed, not all components

**Location**: 
- `workflow/run_newsletter_pipeline.py` → `run_crawlers(required_components)`
- `workflow/run_newsletter_pipeline.py` → `generate_summaries(required_components)`

---

### Step 3: Generate Newsletters
**Process**: Back to user json, generate the corresponding newsletter for each

**Steps**:
1. For each newsletter in user config:
   - Get its components
   - Combine summaries for those components
   - Translate if needed (based on config)
   - Store generated newsletter

**Location**: `workflow/run_newsletter_pipeline.py` → `generate_newsletter()`

---

### Step 4: Send Emails
**Process**: Send newsletters to recipients

**Steps**:
1. For each generated newsletter:
   - Get recipients from config (en and cn lists)
   - Send English version to en recipients
   - Send Chinese version to cn recipients (if available)
   - Use BCC for all recipients except primary

**Location**: `workflow/run_newsletter_pipeline.py` → `send_newsletter()`

---

## Complete Workflow Diagram (Current)

```
[Step 1] Load User Config
    ├─ Load newsletter_config.json or user_configs/{user_id}_newsletter_config.json
    ├─ Extract all newsletters
    └─ Get unique required components: {"top_news", "market_snapshot", ...}
    ↓
[Step 2] Crawl & Summarize (Only Required Components)
    ├─ Run crawlers: crawl_top_news(), crawl_market_snapshot(), ...
    ├─ Generate summaries: summarize_top_news(), summarize_market_snapshot(), ...
    └─ Save summaries to files
    ↓
[Step 3] Generate Newsletters
    ├─ For each newsletter in config:
    │   ├─ Get components: ["top_news", "global_news"]
    │   ├─ Combine summaries
    │   └─ Translate if needed
    └─ Store generated newsletters
    ↓
[Step 4] Send Emails
    ├─ For each newsletter:
    │   ├─ Get recipients (en, cn)
    │   ├─ Send EN version to en recipients
    │   └─ Send CN version to cn recipients
    └─ Use BCC for all recipients
```

---

## Future Workflow Steps (With Prompt Analysis)

### Step 1: User Prompt Input
**Input**: User provides a natural language prompt describing their newsletter needs

**Example prompts:**
- "I need daily tech news and stock prices for Tencent and Alibaba"
- "Send me global news and financial updates"
- "I want AI-focused tech news and IPO updates"

**Location**: User interface or API endpoint

---

### Step 2: Prompt Analysis (LLM)
**Process**: Analyze user prompt to extract requirements

**LLM Task**: 
1. Identify required components from available components
2. Extract customization needs (stocks, topics, websites)
3. Determine email configuration preferences
4. Check if new customized components are needed

**Input to LLM**:
- User prompt
- Available components from `component_config.json`
- Existing user newsletters (if any)

**LLM Output**:
```json
{
  "action": "create_new" | "modify_existing" | "delete",
  "newsletter_name": "custom_tech_stocks",
  "required_components": ["tech_news", "market_snapshot"],
  "component_customizations": {
    "market_snapshot": {
      "stocks": ["0700.HK", "9988.HK"],
      "indices": []
    },
    "tech_news": {
      "section_title": "Tech News for Stock Investors"
    }
  },
  "email_config": {
    "subject": "Daily Tech & Stocks - {date}",
    "recipients": {
      "en": ["user@example.com"]
    }
  },
  "new_components_needed": [],
  "validation": {
    "all_components_exist": true,
    "warnings": []
  }
}
```

**Location**: `workflow/common/prompt_analyzer.py` (to be created)

---

### Step 3: Config File Updates

#### 3a. Update Component Config (if needed)
**Condition**: If user needs a customized version of an existing component

**Example**: User wants "AI-focused tech news"
- Create: `tech_news_ai` component (derived from `tech_news`)
- Update: `component_config.json`

**Process**:
1. Check if base component exists
2. Create derived component entry in `component_config.json`
3. Set customizations (websites, section_title, topic_filter)

**File**: `workflow/config/component_config.json`

#### 3b. Update User Newsletter Config
**Process**:
1. Load user's existing config (or create new)
2. Add/update newsletter entry
3. Validate configuration
4. Save to user-specific config file

**File**: `workflow/config/user_configs/{user_id}_newsletter_config.json`

**Function**: `user_config_manager.add_newsletter_to_user_config()`

**Config Structure**:
```json
{
  "email_intro": "Hi,\n\nYour personalized newsletter.\n\n",
  "newsletters": [
    {
      "name": "custom_tech_stocks",
      "user_id": "user_123",
      "prompt": "I need tech news and Tencent stock",
      "components": ["tech_news", "market_snapshot"],
      "component_customizations": {
        "market_snapshot": {
          "stocks": ["0700.HK"],
          "indices": []
        }
      },
      "recipients": {
        "en": ["user@example.com"]
      },
      "email": {
        "from_email": "david@xplorehk.com",
        "from_name": "Custom Newsletter",
        "subject": "Daily Tech & Stocks - {date}"
      },
      "language": "EN",
      "translate": false
    }
  ]
}
```

---

### Step 4: Dynamic Crawler Execution
**Process**: Run only the crawlers needed for the user's newsletter

**Steps**:
1. Load user's newsletter config
2. Extract required components from all newsletters
3. Determine which crawlers to run
4. Apply customizations (e.g., custom stock list for market_snapshot)
5. Execute crawlers

**Crawler Selection Logic**:
- `top_news` → `crawl_top_news()`
- `tech_news` → `crawl_tech_news()`
- `financial_news` → `crawl_global_financial_news()`
- `market_snapshot` → `crawl_market_snapshot(custom_stocks=...)`
- `regulatory` → `crawl_regulatory_announcements(custom_stock_codes=...)`
- `hk_ipo` → `crawl_hk_ipo_news()`
- `global_news` → `crawl_global_news()`

**Customization Application**:
- For `market_snapshot`: Replace or merge stock list
- For `regulatory`: Filter by custom stock codes
- For generic news: Use custom websites if specified

**Location**: `workflow/run_newsletter_pipeline.py` → `run_crawlers()`

**Output**: 
- CSV files in `workflow/data/news_csv/`
- JSON file in `workflow/data/market_snapshot/`
- Google Sheets (for global_news)

---

### Step 5: Summarization
**Process**: Generate summaries for each component

**Steps**:
1. Load summaries for required components only
2. Apply customizations (section titles, topic filters)
3. Pass user context to summarizers (if applicable)
4. Generate markdown summaries

**Summarizer Functions**:
- `summarize_top_news()`
- `summarize_tech_news()`
- `summarize_global_financial_news()`
- `summarize_market_snapshot()`
- `summarize_regulatory_announcements()`
- `summarize_hk_ipo_news()`
- `summarize_global_news()`

**Customization**:
- Custom section titles
- Topic filtering (if supported)
- User context in summary prompts

**Location**: `workflow/run_newsletter_pipeline.py` → `generate_summaries()`

**Output**: Markdown files in `workflow/summaries/{component_name}/`

---

### Step 6: Newsletter Generation
**Process**: Combine summaries into newsletters

**Steps**:
1. Load user's newsletter config
2. For each newsletter:
   - Load summaries for its components
   - Combine summaries in order
   - Apply custom formatting
   - Generate markdown newsletter
3. Translate if needed (based on config)

**Function**: `generate_newsletter(newsletter_config, summaries)`

**Location**: `workflow/run_newsletter_pipeline.py` → `generate_newsletter()`

**Output**: Markdown files in `workflow/newsletter/{newsletter_name}/`

---

### Step 7: Email Sending
**Process**: Send newsletters via email

**Steps**:
1. For each newsletter in user config:
   - Load generated newsletter content
   - Convert markdown to HTML
   - Get recipients from config
   - Send email via Mailjet API

**Function**: `send_newsletter(newsletter_config, newsletters)`

**Location**: `workflow/run_newsletter_pipeline.py` → `send_newsletter()`

**Email Details**:
- From: `email.from_email` and `email.from_name`
- Subject: `email.subject` (with {date} replaced)
- Recipients: `recipients.en` and `recipients.cn`
- BCC: All recipients except primary

---

## Complete Workflow Diagram

```
User Prompt
    ↓
[Step 2] LLM Prompt Analysis
    ├─ Identify components needed
    ├─ Extract customizations
    └─ Generate config structure
    ↓
[Step 3] Update Config Files
    ├─ component_config.json (if new customized component)
    └─ user_configs/{user_id}_newsletter_config.json
    ↓
[Step 4] Run Crawlers (Dynamic)
    ├─ Only run required crawlers
    ├─ Apply customizations
    └─ Save to CSV/JSON/Sheets
    ↓
[Step 5] Generate Summaries
    ├─ Load data from CSV/JSON/Sheets
    ├─ Apply customizations
    └─ Generate markdown summaries
    ↓
[Step 6] Generate Newsletters
    ├─ Combine summaries
    ├─ Apply formatting
    └─ Translate if needed
    ↓
[Step 7] Send Emails
    ├─ Convert to HTML
    ├─ Send to recipients
    └─ Log results
```

## User-Specific Config Management

### Creating a New Newsletter
```python
from common.user_config_manager import add_newsletter_to_user_config

newsletter_config = {
    "name": "my_custom_newsletter",
    "components": ["tech_news", "market_snapshot"],
    "component_customizations": {
        "market_snapshot": {"stocks": ["0700.HK"]}
    },
    "recipients": {"en": ["user@example.com"]},
    "email": {
        "from_email": "david@xplorehk.com",
        "from_name": "My Newsletter",
        "subject": "My Newsletter - {date}"
    },
    "language": "EN",
    "translate": False
}

add_newsletter_to_user_config("user_123", newsletter_config)
```

### Loading User Config
```python
from common.user_config_manager import load_user_newsletter_config

config = load_user_newsletter_config("user_123")
# Returns merged config (base + user-specific)
```

### Listing User Newsletters
```python
from common.user_config_manager import list_user_newsletters

newsletters = list_user_newsletters("user_123")
# Returns: ["global_newsletter", "market_briefing", "my_custom_newsletter"]
```

## Key Features

1. **User Isolation**: Each user has their own config file
2. **Base Config Preservation**: Base configs remain unchanged
3. **Config Merging**: User configs merge with base configs at runtime
4. **Backup System**: Automatic backups before config changes
5. **Validation**: Config validation before saving
6. **Dynamic Execution**: Only run required crawlers
7. **Customization**: Support for component customizations

## Error Handling

- **Invalid Config**: Validation errors prevent saving
- **Missing Components**: Warn user, suggest alternatives
- **Crawler Failures**: Continue with other crawlers, log errors
- **Summary Failures**: Use fallback or skip component
- **Email Failures**: Log error, continue with other newsletters

## Future Enhancements

1. **Component Templates**: Pre-defined component combinations
2. **Scheduled Newsletters**: Cron-based automatic generation
3. **Newsletter Preview**: Preview before sending
4. **A/B Testing**: Test different component combinations
5. **Analytics**: Track newsletter performance

