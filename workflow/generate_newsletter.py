"""
Generate Newsletter
Generates newsletters based on user configs and saves each in its own subfolder

Usage:
    python workflow/generate_newsletter.py
    cd workflow && python generate_newsletter.py
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_newsletter_pipeline import (
    load_newsletter_config,
    generate_newsletter as generate_newsletter_from_config,
    combine_newsletter
)
from common.summary_storage import get_latest_summary
from common.translation import translate_to_chinese


def save_newsletter_to_subfolder(newsletter_name: str, newsletters: Dict[str, str], date_str: str = None):
    """
    Save newsletter files to a subfolder named after the newsletter
    
    Args:
        newsletter_name: Name of the newsletter (e.g., "global_newsletter")
        newsletters: Dictionary with language keys (e.g., {"EN": "...", "CN": "..."})
        date_str: Optional date string (YYYYMMDD format). If None, uses today's date.
    
    Returns:
        List of file paths saved
    """
    if not newsletters:
        print(f"No newsletter content to save for {newsletter_name}")
        return []
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    # Create newsletter folder structure: newsletter/{newsletter_name}/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    newsletter_subfolder = os.path.join(script_dir, "newsletter", newsletter_name)
    os.makedirs(newsletter_subfolder, exist_ok=True)
    
    saved_files = []
    
    # Save each language version
    for lang, content in newsletters.items():
        if content:
            filename = f"newsletter_{date_str}_{lang.lower()}.md"
            filepath = os.path.join(newsletter_subfolder, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            saved_files.append(filepath)
            print(f"  ✓ Saved {lang} version: {filepath}")
    
    return saved_files


def read_summary_file(filepath: str) -> Optional[str]:
    """Read summary content from a file"""
    if not filepath or not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  WARNING: Failed to read summary file {filepath}: {e}")
        return None


def load_summaries_from_files(components: list, date: Optional[datetime] = None) -> Dict[str, str]:
    """
    Load summaries from files for the specified components
    
    Args:
        components: List of component names (must match folder names in summaries/)
        date: Optional date to look for specific date. If None, gets latest.
    
    Returns:
        Dictionary mapping component names to summary content
    """
    summaries = {}
    
    for component in components:
        print(f"  Loading summary for {component}...")
        
        # Get the latest summary file for this component
        summary_file = get_latest_summary(component)
        
        if not summary_file:
            print(f"    ✗ No summary file found for {component}")
            summaries[component] = f"## {component.replace('_', ' ').title()}\n\nNo summary available.\n"
            continue
        
        # Read the summary content
        summary_content = read_summary_file(summary_file)
        
        if summary_content:
            summaries[component] = summary_content
            print(f"    ✓ Loaded from: {summary_file}")
        else:
            print(f"    ✗ Failed to read summary file")
            summaries[component] = f"## {component.replace('_', ' ').title()}\n\nNo summary available.\n"
    
    return summaries


async def main():
    """Main function to generate all newsletters from config"""
    print("=" * 80)
    print("GENERATE NEWSLETTERS")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load configuration from user configs
    config = load_newsletter_config()
    newsletters_config = config["newsletters"]
    
    print(f"Found {len(newsletters_config)} newsletter(s) to generate")
    print()
    
    date_str = datetime.now().strftime("%Y%m%d")
    all_saved_files = []
    
    # Generate each newsletter from config
    for newsletter_config in newsletters_config:
        newsletter_name = newsletter_config["name"]
        components = newsletter_config["components"]
        language = newsletter_config.get("language", "EN")
        should_translate = newsletter_config.get("translate", False)
        
        print(f"\n{'='*80}")
        print(f"Processing newsletter: {newsletter_name}")
        print(f"Components: {', '.join(components)}")
        print('='*80)
        
        # Step 1: Load summaries from files
        print("\nLoading summaries from files...")
        summaries = load_summaries_from_files(components)
        
        # Check if all required summaries are available
        missing_summaries = [comp for comp in components if not summaries.get(comp) or "No summary available" in summaries.get(comp, "")]
        if missing_summaries:
            print(f"  WARNING: Missing summaries for: {', '.join(missing_summaries)}")
        
        # Step 2: Combine summaries into newsletter
        print("\nCombining summaries into newsletter...")
        newsletter_en = combine_newsletter(components, summaries)
        
        newsletters = {"EN": newsletter_en}
        
        # Step 3: Translate if needed
        if should_translate and language == "EN":
            print("\nTranslating newsletter to Chinese...")
            try:
                newsletter_cn = await translate_to_chinese(newsletter_en)
                newsletters["CN"] = newsletter_cn
                print("  ✓ Translation complete")
            except Exception as e:
                print(f"  ✗ Translation failed: {e}")
                newsletters["CN"] = newsletter_en  # Fallback to English
        
        # Step 4: Save to subfolder
        print(f"\nSaving {newsletter_name} to subfolder...")
        saved_files = save_newsletter_to_subfolder(newsletter_name, newsletters, date_str)
        all_saved_files.extend(saved_files)
    
    print()
    print("=" * 80)
    print("NEWSLETTER GENERATION COMPLETE")
    print("=" * 80)
    print(f"Generated {len(newsletters_config)} newsletter(s)")
    print(f"Saved {len(all_saved_files)} file(s):")
    for filepath in all_saved_files:
        print(f"  - {filepath}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

