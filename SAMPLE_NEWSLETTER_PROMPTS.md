# Sample Newsletter Prompts

This document provides example prompts that users can provide to generate tailored newsletters. Each example corresponds to one of the existing newsletter configurations.

---

## Example 1: Global Headlines Newsletter

**User Prompt:**

```
I want a daily newsletter that covers the most important global news stories. 
I'm interested in:

1. Top breaking news from major international news sources (BBC, CNN, CNBC Politics)
2. Regional news stories directly from local news sources around the world, organized by geographic regions

The newsletter should:
- Focus on significant global events, politics, conflicts, natural disasters, and major developments
- Be comprehensive but concise
- Include links to original sources
- Be available in both English and Chinese (translate the content)

Send it to my email list with separate English and Chinese recipient lists.
```

**Resulting Newsletter Configuration:**
- **Name:** `global_newsletter`
- **Components:** 
  - `top_news` (Most Important Stories from major news sites)
  - `global_news` (Regional Stories from local news sources worldwide)
- **Language:** English with Chinese translation
- **Target Audience:** General audience interested in global affairs

---

## Example 2: Market Briefing Newsletter

**User Prompt:**

```
I need a daily market-focused newsletter for my investment research. It should include:

1. Market snapshot with current prices, percentage changes, and market caps for major indices and stocks I track
2. Global financial news from financial markets and economic developments
3. Technology news, especially funding events and AI/robotics developments
4. Regulatory announcements from Hong Kong-listed companies I'm monitoring
5. Hong Kong IPO news and updates

The newsletter should:
- Focus on market-moving information and investment-relevant news
- Include detailed market data (prices, changes, market caps)
- Cover tech sector with emphasis on funding and AI/robotics
- Track specific Hong Kong stocks for regulatory filings
- Be in English only (no translation needed)

Send it daily to my email.
```

**Resulting Newsletter Configuration:**
- **Name:** `market_briefing`
- **Components:**
  - `market_snapshot` (Stock/index prices and market data)
  - `financial_news` (Global financial markets news)
  - `tech_news` (Technology news with funding/AI focus)
  - `regulatory` (HKEX regulatory announcements)
  - `hk_ipo` (Hong Kong IPO news)
- **Language:** English only
- **Target Audience:** Investors and market professionals

---

## How to Use These Prompts

When a user provides a prompt like the examples above, you would:

1. **Parse the requirements** to identify:
   - Desired news components/sections
   - Language preferences (translation needed?)
   - Target audience
   - Delivery preferences

2. **Map to available components:**
   - `top_news` - Major news from BBC, CNN, CNBC Politics
   - `global_news` - Regional news from local sources worldwide
   - `market_snapshot` - Stock/index market data
   - `financial_news` - Global financial markets news
   - `tech_news` - Technology news (funding, AI, robotics)
   - `regulatory` - HKEX regulatory announcements
   - `hk_ipo` - Hong Kong IPO news

3. **Create newsletter configuration** in `newsletter_config.json` format

4. **Generate and deliver** the newsletter according to the user's specifications

---

## Notes

- Users can mix and match components based on their interests
- Translation can be enabled/disabled per newsletter
- Recipient lists can be customized per newsletter
- Email subject lines and sender names can be customized
- Each newsletter can have different delivery schedules (though currently all are daily)

