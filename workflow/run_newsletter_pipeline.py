"""
Main Newsletter Pipeline
Orchestrates crawling, summarization, translation, and email sending
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional
import markdown

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.google_sheets import SHEET_MAPPING
from common.email import send_email
from common.translation import translate_to_chinese
from common.summary_storage import save_all_summaries
from common.url_utils import normalize_markdown_links

# Import all crawlers
from crawlers.global_news_crawler import crawl_global_news
from crawlers.generic_news_crawler import crawl_top_news, crawl_tech_news, crawl_global_financial_news, crawl_hk_news
from crawlers.market_snapshot_crawler import crawl_market_snapshot
from crawlers.regulatory_announcement_crawler import crawl_regulatory_announcements
from crawlers.corporate_news_crawler import crawl_corporate_news_from_config
from crawlers.futu_stock_news_crawler import crawl_futu_stock_news_from_config
from crawlers.hk_ipo_news_crawler import crawl_hk_ipo_news

# Import all summarizers
from summarizers.global_news_summarizer import summarize_global_news
from summarizers.top_news_summarizer import summarize_top_news
from summarizers.hk_news_summarizer import summarize_hk_news
from summarizers.global_financial_news_summarizer import summarize_global_financial_news
from summarizers.market_snapshot_summarizer import summarize_market_snapshot
from summarizers.tech_news_summarizer import summarize_tech_news
from summarizers.regulatory_announcement_summarizer import summarize_regulatory_announcements
from summarizers.tech_stock_regulatory_summarizer import summarize_tech_stock_regulatory_announcements
from summarizers.corporate_news_summarizer import summarize_corporate_news
from summarizers.semi_ai_corporate_news_summarizer import summarize_semi_ai_corporate_news
from summarizers.futu_stock_news_summarizer import summarize_futu_stock_news
from summarizers.hk_ipo_news_summarizer import summarize_hk_ipo_news


# Mapping of component names to summarizer functions
SUMMARIZERS = {
    "global_news": summarize_global_news,
    "top_news": summarize_top_news,
    "hk_news": summarize_hk_news,
    "financial_news": summarize_global_financial_news,
    "market_snapshot": summarize_market_snapshot,
    "tech_news": summarize_tech_news,
    "regulatory": summarize_regulatory_announcements,
    "tech_stock_regulatory": summarize_tech_stock_regulatory_announcements,
    "corporate_news": summarize_corporate_news,
    "semi_ai_corporate_news": summarize_semi_ai_corporate_news,
    "futu_stock_news": summarize_futu_stock_news,
    "hk_ipo": summarize_hk_ipo_news,
}


def _count_markdown_bullets(markdown_text: str) -> int:
    if not markdown_text:
        return 0
    return sum(1 for line in markdown_text.splitlines() if line.strip().startswith("- "))


def _hk_summary_needs_retry(summary: str) -> bool:
    """Return True if hk_news summary looks malformed.

    This is a lightweight guardrail to catch obvious LLM failures (empty output,
    missing bullets/links, JSON/code blocks). It is not meant to judge content
    quality.
    """
    if not summary or not summary.strip():
        return True

    s = summary.strip()

    # Common "LLM went off the rails" signals
    if s.startswith("{") or s.startswith("[") or "```" in s:
        return True
    if "Error generating summary" in s:
        return True

    # If we have HK items today, require minimally well-formed bullets with links.
    try:
        from common.csv_storage import read_news_items_from_csv
        df_today = read_news_items_from_csv("hk_news", date=datetime.now())
        items_today = len(df_today)
    except Exception:
        items_today = 0

    if items_today <= 0:
        return False

    bullets = _count_markdown_bullets(s)
    min_bullets = max(1, min(3, items_today))
    if bullets < min_bullets:
        return True

    for line in s.splitlines():
        line_stripped = line.strip()
        if not line_stripped.startswith("- "):
            continue
        if not re.search(r"\[[^\]]+\]\((https?://[^)]+)\)", line_stripped):
            return True

    return False


def load_newsletter_config(config_path: str = None, user_id: str = None) -> Dict:
    """Load newsletter configuration from JSON file
    
    Args:
        config_path: Optional path to config file (for backward compatibility)
        user_id: Optional user ID to load user-specific config
    
    Returns:
        Newsletter config dictionary
    """
    if config_path:
        # Load specific config file (backward compatibility)
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Load all user configs (new approach: reads all config files from user_configs folder)
        # If user_id is provided, only loads that user's configs; otherwise loads all
        from common.user_config_manager import load_all_user_configs
        return load_all_user_configs(user_id=user_id)


def get_required_components(newsletters_config: List[Dict]) -> set:
    """Extract all unique components needed from newsletters config
    
    Args:
        newsletters_config: List of newsletter configurations
    
    Returns:
        Set of component names required
    """
    required_components = set()
    
    for newsletter in newsletters_config:
        components = newsletter.get("components", [])
        required_components.update(components)
    
    return required_components


def extract_component_customizations(newsletters_config: List[Dict]) -> Dict[str, Dict]:
    """Extract component customizations from all newsletters
    
    Args:
        newsletters_config: List of newsletter configurations
    
    Returns:
        Dictionary mapping component name to its customization (from first newsletter that customizes it)
        Format: {"market_snapshot": {"assets": [...], "output_file_suffix": "user_b"}, ...}
    """
    customizations = {}
    
    for newsletter in newsletters_config:
        component_customizations = newsletter.get("component_customizations", {})
        for component, customization in component_customizations.items():
            # Use first customization found (or could merge if needed)
            if component not in customizations:
                customizations[component] = customization
    
    return customizations


# Mapping of component names to crawler functions
CRAWLERS = {
    "global_news": crawl_global_news,
    "top_news": crawl_top_news,
    "hk_news": crawl_hk_news,
    "financial_news": crawl_global_financial_news,
    "market_snapshot": crawl_market_snapshot,
    "tech_news": crawl_tech_news,
    "regulatory": crawl_regulatory_announcements,
    "corporate_news": crawl_corporate_news_from_config,
    "futu_stock_news": crawl_futu_stock_news_from_config,
    "hk_ipo": crawl_hk_ipo_news,
}


async def run_crawlers(required_components: set, component_customizations: Dict[str, Dict] = None) -> Dict[str, List]:
    """Run crawlers for required components only
    
    Args:
        required_components: Set of component names to crawl
        component_customizations: Optional dictionary of component customizations
    
    Returns:
        Dictionary of crawler results
    """
    print("=" * 80)
    print("RUNNING CRAWLERS")
    print("=" * 80)
    print(f"Required components: {', '.join(sorted(required_components))}")
    if component_customizations:
        print(f"Customizations: {', '.join(component_customizations.keys())}")
    print()
    
    results = {}
    component_customizations = component_customizations or {}
    
    # Run only required crawlers
    component_order = ["global_news", "top_news", "hk_news", "financial_news", "market_snapshot", 
                       "tech_news", "regulatory", "corporate_news", "futu_stock_news", "hk_ipo"]
    
    for i, component in enumerate(component_order, 1):
        if component in required_components:
            crawler_func = CRAWLERS.get(component)
            if crawler_func:
                print(f"{i}. Crawling {component}...")
                try:
                    # Get customizations for this component
                    customization = component_customizations.get(component, {})
                    
                    # Apply customizations based on component type
                    if component == "market_snapshot":
                        custom_assets = customization.get("assets")
                        output_suffix = customization.get("output_file_suffix")
                        if asyncio.iscoroutinefunction(crawler_func):
                            results[component] = await crawler_func(assets=custom_assets, output_file_suffix=output_suffix)
                        else:
                            results[component] = crawler_func(assets=custom_assets, output_file_suffix=output_suffix)
                    elif component == "regulatory":
                        custom_stock_codes = customization.get("stock_codes")
                        # TODO: Update regulatory crawler to accept custom stock codes
                        if asyncio.iscoroutinefunction(crawler_func):
                            results[component] = await crawler_func()
                        else:
                            results[component] = crawler_func()
                    else:
                        # Other components don't support customizations yet
                        if asyncio.iscoroutinefunction(crawler_func):
                            try:
                                result = await crawler_func()
                                results[component] = result if result is not None else []
                            except Exception as inner_e:
                                # For global_news, provide more detailed error info
                                if component == "global_news":
                                    print(f"\n   ⚠ CRITICAL: Global news crawler failed with error: {inner_e}")
                                    print(f"   ⚠ This may indicate:")
                                    print(f"      - Google Sheets API authentication issue")
                                    print(f"      - OpenAI API issue")
                                    print(f"      - Network connectivity issue")
                                    print(f"   ⚠ You can try running the crawler directly:")
                                    print(f"      python workflow/crawlers/global_news_crawler.py\n")
                                raise  # Re-raise to be caught by outer exception handler
                        else:
                            result = crawler_func()
                            results[component] = result if result is not None else []
                    
                    print(f"   ✓ {component} crawl complete")
                except Exception as e:
                    print(f"   ✗ Error crawling {component}: {e}")
                    import traceback
                    traceback.print_exc()
                    results[component] = []
            else:
                print(f"   ⚠ No crawler found for {component}")
    
    print("\n" + "=" * 80)
    print("CRAWLERS COMPLETE")
    print("=" * 80)
    
    return results


async def generate_summaries(required_components: set, component_customizations: Dict[str, Dict] = None) -> Dict[str, str]:
    """Generate summaries for required components only
    
    Args:
        required_components: Set of component names to summarize
        component_customizations: Optional dictionary of component customizations
    
    Returns:
        Dictionary of summaries
    """
    print("\n" + "=" * 80)
    print("GENERATING SUMMARIES")
    print("=" * 80)
    print(f"Required components: {', '.join(sorted(required_components))}")
    if component_customizations:
        print(f"Customizations: {', '.join(component_customizations.keys())}")
    print()
    
    summaries = {}
    component_customizations = component_customizations or {}
    
    # Generate summaries only for required components
    for component in sorted(required_components):
        customization = component_customizations.get(component, {})
        summarizer_func = SUMMARIZERS.get(component)
        
        if summarizer_func:
            print(f"Summarizing {component}...")
            try:
                # Apply customizations based on component type
                if component == "market_snapshot":
                    file_suffix = customization.get("output_file_suffix")
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(file_suffix=file_suffix)
                    else:
                        summary = summarizer_func(file_suffix=file_suffix)
                elif component == "tech_stock_regulatory":
                    # Load stock_codes and company_names from component config or customization
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "config",
                        "component_config.json"
                    )
                    with open(config_path, 'r', encoding='utf-8') as f:
                        component_config_data = json.load(f)
                    
                    component_config = component_config_data.get("components", {}).get(component, {})
                    summarizer_config = component_config.get("summarizer", {})
                    inputs = summarizer_config.get("inputs", {})
                    
                    # Get stock_codes (from customization or config default)
                    stock_codes_config = inputs.get("stock_codes", {})
                    stock_codes = customization.get("stock_codes") or stock_codes_config.get("default", None)
                    
                    # Get company_names (from customization or config default)
                    company_names_config = inputs.get("company_names", {})
                    company_names = customization.get("company_names") or company_names_config.get("default", None)
                    
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(stock_codes=stock_codes, company_names=company_names)
                    else:
                        summary = summarizer_func(stock_codes=stock_codes, company_names=company_names)
                elif component == "corporate_news":
                    # Load company_names and section_title from component config or customization
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "config",
                        "component_config.json"
                    )
                    with open(config_path, 'r', encoding='utf-8') as f:
                        component_config_data = json.load(f)
                    
                    component_config = component_config_data.get("components", {}).get(component, {})
                    summarizer_config = component_config.get("summarizer", {})
                    inputs = summarizer_config.get("inputs", {})
                    
                    # Get company_names (from customization or config default)
                    company_names_config = inputs.get("company_names", {})
                    company_names = customization.get("company_names") or company_names_config.get("default", None)
                    
                    # Get section_title (from customization or config default)
                    section_title_config = inputs.get("section_title", {})
                    section_title = customization.get("section_title") or section_title_config.get("default", None)
                    
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(company_names=company_names, section_title=section_title)
                    else:
                        summary = summarizer_func(company_names=company_names, section_title=section_title)
                elif component == "semi_ai_corporate_news":
                    # Load section_title from component config or customization
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "config",
                        "component_config.json"
                    )
                    with open(config_path, 'r', encoding='utf-8') as f:
                        component_config_data = json.load(f)
                    
                    component_config = component_config_data.get("components", {}).get(component, {})
                    summarizer_config = component_config.get("summarizer", {})
                    inputs = summarizer_config.get("inputs", {})
                    
                    # Get section_title (from customization or config default)
                    section_title_config = inputs.get("section_title", {})
                    section_title = customization.get("section_title") or section_title_config.get("default", None)
                    
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(section_title=section_title)
                    else:
                        summary = summarizer_func(section_title=section_title)
                elif component == "futu_stock_news":
                    # Load stock_codes, company_names, and section_title from component config or customization
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "config",
                        "component_config.json"
                    )
                    with open(config_path, 'r', encoding='utf-8') as f:
                        component_config_data = json.load(f)
                    
                    component_config = component_config_data.get("components", {}).get(component, {})
                    summarizer_config = component_config.get("summarizer", {})
                    inputs = summarizer_config.get("inputs", {})
                    
                    # Get stock_codes (from customization or config default)
                    stock_codes_config = inputs.get("stock_codes", {})
                    stock_codes = customization.get("stock_codes") or stock_codes_config.get("default", None)
                    
                    # Get company_names (from customization or config default)
                    company_names_config = inputs.get("company_names", {})
                    company_names = customization.get("company_names") or company_names_config.get("default", None)
                    
                    # Get section_title (from customization or config default)
                    section_title_config = inputs.get("section_title", {})
                    section_title = customization.get("section_title") or section_title_config.get("default", None)
                    
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(stock_codes=stock_codes, company_names=company_names, section_title=section_title)
                    else:
                        summary = summarizer_func(stock_codes=stock_codes, company_names=company_names, section_title=section_title)
                elif component == "tech_news":
                    # Load section_title from component config or customization
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "config",
                        "component_config.json"
                    )
                    with open(config_path, 'r', encoding='utf-8') as f:
                        component_config_data = json.load(f)
                    
                    component_config = component_config_data.get("components", {}).get(component, {})
                    summarizer_config = component_config.get("summarizer", {})
                    inputs = summarizer_config.get("inputs", {})
                    
                    # Get section_title (from customization or config default)
                    section_title_config = inputs.get("section_title", {})
                    section_title = customization.get("section_title") or section_title_config.get("default", None)
                    
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func(section_title=section_title)
                    else:
                        summary = summarizer_func(section_title=section_title)
                else:
                    # Other components don't support customizations yet
                    if asyncio.iscoroutinefunction(summarizer_func):
                        summary = await summarizer_func()
                    else:
                        summary = summarizer_func()

                # Reliability guardrail: retry hk_news once if output is malformed
                if component == "hk_news" and _hk_summary_needs_retry(summary):
                    print("  ⚠ hk_news summary failed validation; retrying once...")
                    try:
                        if asyncio.iscoroutinefunction(summarizer_func):
                            summary_retry = await summarizer_func()
                        else:
                            summary_retry = summarizer_func()

                        if not _hk_summary_needs_retry(summary_retry):
                            summary = summary_retry
                            print("  ✓ hk_news summary regenerated successfully")
                        else:
                            print("  ⚠ hk_news retry also failed validation; keeping original output")
                    except Exception as retry_err:
                        print(f"  ⚠ hk_news retry failed; keeping original output: {retry_err}")
                
                summaries[component] = summary
                print(f"  ✓ {component} summary generated ({len(summary)} chars)")
            except Exception as e:
                print(f"  ✗ Error summarizing {component}: {e}")
                import traceback
                traceback.print_exc()
                summaries[component] = f"## {component.replace('_', ' ').title()}\n\nError generating summary.\n"
        else:
            print(f"  ⚠ No summarizer found for {component}")
            summaries[component] = f"## {component.replace('_', ' ').title()}\n\nSummarizer not available.\n"
    
    # Save all summaries to files
    print("\nSaving summaries to files...")
    save_all_summaries(summaries)
    
    print("\n" + "=" * 80)
    print("SUMMARIES COMPLETE")
    print("=" * 80)
    
    return summaries


def combine_newsletter(components: List[str], summaries: Dict[str, str]) -> str:
    """Combine summaries into a single newsletter"""
    newsletter_parts = []
    
    for component in components:
        if component in summaries:
            newsletter_parts.append(summaries[component])
        else:
            newsletter_parts.append(f"## {component.replace('_', ' ').title()}\n\nComponent not available.\n")
    
    return "\n\n".join(newsletter_parts)


async def generate_newsletter(newsletter_config: Dict, summaries: Dict[str, str]) -> Dict[str, str]:
    """Generate newsletter in specified language(s)"""
    components = newsletter_config["components"]
    language = newsletter_config.get("language", "EN")
    should_translate = newsletter_config.get("translate", False)
    
    # Generate base newsletter
    newsletter_en = combine_newsletter(components, summaries)
    # Normalize links (e.g. stheadline.com -> ID-only URLs) so they don't break on mobile
    newsletter_en = normalize_markdown_links(newsletter_en)

    result = {"EN": newsletter_en}

    # Translate if needed
    if should_translate and language == "EN":
        print(f"\nTranslating newsletter to Chinese...")
        try:
            newsletter_cn = await translate_to_chinese(newsletter_en)
            newsletter_cn = normalize_markdown_links(newsletter_cn)
            result["CN"] = newsletter_cn
            print("  ✓ Translation complete")
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            result["CN"] = newsletter_en  # Fallback to English
    
    return result


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML"""
    return markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])


async def send_newsletter(newsletter_config: Dict, newsletters: Dict[str, str], recipient: str = None, language: str = None):
    """Send newsletter via email
    
    Args:
        newsletter_config: Newsletter configuration dictionary
        newsletters: Dictionary with language keys (e.g., {"EN": "...", "CN": "..."})
        recipient: Optional recipient email (if not provided, uses config recipients)
        language: Optional language code (if not provided, uses config language)
    """
    email_config = newsletter_config["email"]
    
    # Use provided language or default from config
    if language is None:
        language = newsletter_config.get("language", "EN")
    
    # Select newsletter based on language
    newsletter_text = newsletters.get(language, newsletters.get("EN", ""))
    
    if not newsletter_text:
        print(f"ERROR: No newsletter content available for language {language}")
        return False
    
    # Convert to HTML
    html_content = markdown_to_html(newsletter_text)
    
    # Add email intro from newsletter config (if available)
    email_intro = newsletter_config.get('email_intro', '')
    if email_intro:
        html_content = email_intro + "\n\n" + html_content
    
    # Get recipient
    if recipient is None:
        # Try to get from config (backward compatibility)
        recipient = newsletter_config.get("recipient")
        if not recipient:
            recipients = newsletter_config.get("recipients", {})
            lang_recipients = recipients.get(language.lower(), recipients.get("en", []))
            if lang_recipients:
                recipient = lang_recipients[0]  # Use first recipient as primary
    
    if not recipient:
        print(f"ERROR: No recipient specified")
        return False
    
    # Get BCC recipients (all other recipients)
    recipients = newsletter_config.get("recipients", {})
    all_recipients = []
    for lang, emails in recipients.items():
        all_recipients.extend(emails)
    
    # Remove primary recipient from BCC list
    bcc_recipients = [r for r in all_recipients if r != recipient]
    
    # Send email
    success = send_email(
        to_email=recipient,
        subject=email_config["subject"],
        html_content=html_content,
        from_email=email_config.get("from_email"),
        from_name=email_config.get("from_name"),
        bcc_emails=bcc_recipients if bcc_recipients else None
    )
    
    return success


async def main(user_id: str = None):
    """Main pipeline execution
    
    Args:
        user_id: Optional user ID to generate newsletters for specific user
                 If None, generates for all base newsletters
    """
    print("=" * 80)
    print("NEWSLETTER PIPELINE")
    print("=" * 80)
    if user_id:
        print(f"User ID: {user_id}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Load user config and get all required components
    print("Step 1: Loading newsletter configuration...")
    config = load_newsletter_config(user_id=user_id)
    newsletters_config = config["newsletters"]
    
    # Extract all unique components needed across all newsletters
    required_components = get_required_components(newsletters_config)
    
    # Extract component customizations from all newsletters
    component_customizations = extract_component_customizations(newsletters_config)
    
    print(f"  Found {len(newsletters_config)} newsletter(s)")
    print(f"  Required components: {', '.join(sorted(required_components))}")
    if component_customizations:
        print(f"  Component customizations: {', '.join(component_customizations.keys())}")
    print()
    
    # Step 2: Based on component config, crawl and summarize all required components
    print("Step 2: Crawling and summarizing required components...")
    await run_crawlers(required_components, component_customizations)
    summaries = await generate_summaries(required_components, component_customizations)
    
    # Step 3: Back to user json, generate newsletters for each
    print("\n" + "=" * 80)
    print("GENERATING NEWSLETTERS")
    print("=" * 80)
    
    generated_newsletters = {}
    for newsletter_config in newsletters_config:
        newsletter_name = newsletter_config["name"]
        print(f"\nGenerating newsletter: {newsletter_name}")
        print(f"  Components: {', '.join(newsletter_config.get('components', []))}")
        
        # Generate newsletter
        newsletters = await generate_newsletter(newsletter_config, summaries)
        generated_newsletters[newsletter_name] = {
            "config": newsletter_config,
            "content": newsletters
        }
        print(f"  ✓ {newsletter_name} generated")
    
    # Step 4: Send emails
    print("\n" + "=" * 80)
    print("SENDING EMAILS")
    print("=" * 80)
    
    for newsletter_name, newsletter_data in generated_newsletters.items():
        newsletter_config = newsletter_data["config"]
        newsletters = newsletter_data["content"]
        
        print(f"\nSending {newsletter_name}...")
        
        # Get recipients
        recipients = newsletter_config.get("recipients", {})
        en_recipients = recipients.get("en", [])
        cn_recipients = recipients.get("cn", [])
        email_config = newsletter_config.get("email", {})

        # Primary 'To' address: use from_email so everything else is BCC
        primary_recipient = email_config.get("from_email") or (en_recipients[0] if en_recipients else None)

        # Send English version: To = primary, BCC = all EN recipients
        if "EN" in newsletters and en_recipients and primary_recipient:
            print(f"  Sending EN to {primary_recipient} with BCC: {', '.join(en_recipients)}")
            cfg_en = dict(newsletter_config)
            cfg_en["recipients"] = {"en": en_recipients}
            success = await send_newsletter(cfg_en, {"EN": newsletters["EN"]}, recipient=primary_recipient, language="EN")
            if success:
                print(f"    ✓ EN sent (primary: {primary_recipient})")
            else:
                print(f"    ✗ Failed to send EN (primary: {primary_recipient})")

        # Send Chinese version: To = primary, BCC = all CN recipients
        if "CN" in newsletters and cn_recipients and primary_recipient:
            print(f"  Sending CN to {primary_recipient} with BCC: {', '.join(cn_recipients)}")
            cfg_cn = dict(newsletter_config)
            cfg_cn["recipients"] = {"cn": cn_recipients}
            success = await send_newsletter(cfg_cn, {"CN": newsletters["CN"]}, recipient=primary_recipient, language="CN")
            if success:
                print(f"    ✓ CN sent (primary: {primary_recipient})")
            else:
                print(f"    ✗ Failed to send CN (primary: {primary_recipient})")
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

