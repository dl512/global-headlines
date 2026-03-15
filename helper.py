"""
Workflow Helper - Interactive Menu
Provides a user interface to run different workflow scripts

Usage:
    python helper.py
"""

import os
import sys
import subprocess
from datetime import datetime


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the header"""
    print("=" * 80)
    print("NEWSLETTER WORKFLOW HELPER")
    print("=" * 80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()


def print_menu():
    """Print the main menu"""
    print("Select an action:")
    print()
    print("  1. Run Crawlers (Collect data for required components)")
    print("     1a. Run Specific Component Crawler (Choose which component to crawl)")
    print("  2. Generate Summaries (Create summaries for required components)")
    print("     2a. Generate Specific Component Summary (Choose which component to summarize)")
    print("  3. Generate Newsletter (Combine summaries into final newsletter)")
    print("  4. Send Newsletter Email (Send newsletter via email)")
    print()
    print("  5. Run Full Pipeline (Load config → Crawl → Summarize → Generate → Send)")
    print()
    print("  0. Exit")
    print()


def run_script(script_name, description):
    """Run a workflow script"""
    print()
    print("=" * 80)
    print(f"Running: {description}")
    print("=" * 80)
    print()
    
    # Get the workflow directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_dir = os.path.join(script_dir, 'workflow')
    script_path = os.path.join(workflow_dir, script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        return False
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=workflow_dir,
            check=False
        )
        
        print()
        if result.returncode == 0:
            print("✅ Script completed successfully!")
            return True
        else:
            print(f"❌ Script exited with code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Error running script: {e}")
        return False


def run_send_newsletter_email():
    """Run send newsletter email"""
    import asyncio
    import sys
    import json
    import markdown
    from datetime import datetime
    
    # Import using importlib to avoid conflict with standard library email module
    import importlib.util
    script_dir = os.path.dirname(os.path.abspath(__file__))
    email_module_path = os.path.join(script_dir, 'workflow', 'common', 'email.py')
    spec = importlib.util.spec_from_file_location("workflow_email", email_module_path)
    workflow_email = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow_email)
    send_email = workflow_email.send_email
    
    print()
    print("=" * 80)
    print("Send Newsletter Email")
    print("=" * 80)
    print()
    
    # Get the workflow directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_dir = os.path.join(script_dir, 'workflow')
    newsletter_dir = os.path.join(workflow_dir, 'newsletter')
    
    # Load config from user_configs folder
    sys.path.insert(0, workflow_dir)
    try:
        from common.user_config_manager import load_all_user_configs
        config = load_all_user_configs()  # Load all newsletters from all user configs
        email_intro = config.get('email_intro', '')
        newsletters_config = config.get('newsletters', [])
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if not newsletters_config:
        print("[ERROR] No newsletters configured")
        print("  Make sure you have newsletter config files in workflow/config/user_configs/")
        return False
    
    print(f"Loaded {len(newsletters_config)} newsletter(s) from user configs")
    
    today_str = datetime.now().strftime("%Y%m%d")
    overall_success = True
    
    # Process each newsletter in config
    for newsletter_config in newsletters_config:
        newsletter_name = newsletter_config.get('name', 'unknown')
        recipients = newsletter_config.get('recipients', {})
        email_config = newsletter_config.get('email', {})
        
        print(f"\nProcessing newsletter: {newsletter_name}")
        
        # Find newsletter files in subfolder
        newsletter_subfolder = os.path.join(newsletter_dir, newsletter_name)
        en_file = os.path.join(newsletter_subfolder, f"newsletter_{today_str}_en.md")
        cn_file = os.path.join(newsletter_subfolder, f"newsletter_{today_str}_cn.md")
        
        en_exists = os.path.exists(en_file)
        cn_exists = os.path.exists(cn_file)
        
        if not en_exists and not cn_exists:
            print(f"  [WARNING] No newsletter files found for {newsletter_name} (today: {today_str})")
            print(f"    Expected files:")
            print(f"      - {en_file}")
            print(f"      - {cn_file}")
            continue
        
        en_recipients = recipients.get('en', [])
        cn_recipients = recipients.get('cn', [])
        from_email = email_config.get('from_email')
        from_name = email_config.get('from_name', 'Newsletter')
        
        # Primary recipient (always david@xplorehk.com)
        primary_recipient = 'david@xplorehk.com'
        
        # Send English newsletter
        if en_exists and en_recipients:
            try:
                with open(en_file, 'r', encoding='utf-8') as f:
                    newsletter_text = f.read()
                html_content = markdown.markdown(email_intro + "\n\n" + newsletter_text, extensions=['tables'])
                subject = email_config.get('subject', 'Newsletter - {date}').format(date=datetime.now().strftime('%B %d, %Y'))
                
                # Send one email to primary recipient with all EN recipients as BCC
                if send_email(primary_recipient, subject, html_content, from_email=from_email, from_name=from_name, bcc_emails=en_recipients):
                    print(f"  [OK] English newsletter sent to {primary_recipient} with {len(en_recipients)} BCC recipient(s)")
                else:
                    print(f"  [ERROR] Failed to send English newsletter")
                    overall_success = False
            except Exception as e:
                print(f"  [ERROR] Error sending English newsletter: {e}")
                import traceback
                traceback.print_exc()
                overall_success = False
        
        # Send Chinese newsletter
        if cn_exists and cn_recipients:
            try:
                with open(cn_file, 'r', encoding='utf-8') as f:
                    newsletter_text = f.read()
                html_content = markdown.markdown(email_intro + "\n\n" + newsletter_text, extensions=['tables'])
                subject = email_config.get('subject', 'Newsletter (繁體中文版) - {date}').format(date=datetime.now().strftime('%B %d, %Y'))
                
                # Send one email to primary recipient with all CN recipients as BCC
                if send_email(primary_recipient, subject, html_content, from_email=from_email, from_name=from_name, bcc_emails=cn_recipients):
                    print(f"  [OK] Chinese newsletter sent to {primary_recipient} with {len(cn_recipients)} BCC recipient(s)")
                else:
                    print(f"  [ERROR] Failed to send Chinese newsletter")
                    overall_success = False
            except Exception as e:
                print(f"  [ERROR] Error sending Chinese newsletter: {e}")
                import traceback
                traceback.print_exc()
                overall_success = False
    
    return overall_success


def get_available_components():
    """Get list of available components from component_config.json"""
    import json
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'workflow',
        'config',
        'component_config.json'
    )
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            component_config = json.load(f)
        components = component_config.get('components', {})
        return components
    except Exception as e:
        print(f"❌ Error loading component config: {e}")
        return {}


def print_component_menu():
    """Print component selection menu"""
    components = get_available_components()
    if not components:
        print("❌ No components available")
        return None
    
    print()
    print("Available components:")
    print()
    component_list = []
    for idx, (key, comp) in enumerate(sorted(components.items()), 1):
        name = comp.get('name', key)
        description = comp.get('description', '')
        print(f"  {idx}. {name} ({key})")
        if description:
            print(f"     {description}")
        component_list.append(key)
    print(f"  0. Back to main menu")
    print()
    return component_list


def run_specific_component_summarizer(component_key):
    """Run summarizer for a specific component"""
    import asyncio
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow'))
    
    print()
    print("=" * 80)
    print(f"RUNNING SUMMARIZER: {component_key.upper()}")
    print("=" * 80)
    print()
    
    try:
        components = get_available_components()
        if component_key not in components:
            print(f"[ERROR] Component '{component_key}' not found")
            return False
        
        component = components[component_key]
        summarizer_config = component.get('summarizer', {})
        
        # Import summarizers from run_newsletter_pipeline
        from run_newsletter_pipeline import SUMMARIZERS, save_all_summaries
        
        summarizer_func = SUMMARIZERS.get(component_key)
        
        if not summarizer_func:
            print(f"[ERROR] No summarizer found for component '{component_key}'")
            print(f"Available summarizers: {', '.join(SUMMARIZERS.keys())}")
            return False
        
        print(f"Summarizing {component_key}...")
        
        # Call the summarizer function
        if asyncio.iscoroutinefunction(summarizer_func):
            summary = asyncio.run(summarizer_func())
        else:
            summary = summarizer_func()
        
        if summary:
            # Save the summary
            summaries = {component_key: summary}
            save_all_summaries(summaries)
            print(f"[OK] {component_key} summary generated ({len(summary)} chars)")
            print(f"[OK] Summary saved to file")
            return True
        else:
            print(f"[ERROR] Failed to generate summary for {component_key}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error running {component_key} summarizer: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_specific_component_crawler(component_key):
    """Run crawler for a specific component"""
    import asyncio
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow'))
    
    print()
    print("=" * 80)
    print(f"RUNNING CRAWLER: {component_key.upper()}")
    print("=" * 80)
    print()
    
    try:
        components = get_available_components()
        if component_key not in components:
            print(f"[ERROR] Component '{component_key}' not found")
            return False
        
        component = components[component_key]
        crawler_config = component.get('crawler', {})
        crawler_type = crawler_config.get('type')
        
        if crawler_type == 'generic_news':
            # Use generic news crawler
            from crawlers.generic_news_crawler import crawl_news_from_config
            print(f"Crawling {component_key} using generic_news_crawler...")
            asyncio.run(crawl_news_from_config(component_key))
        elif crawler_type == 'market_snapshot':
            # Use market snapshot crawler (not async)
            from crawlers.market_snapshot_crawler import crawl_market_snapshot
            print(f"Crawling {component_key} using market_snapshot_crawler...")
            crawl_market_snapshot()  # Not async, no asyncio.run needed
        elif crawler_type == 'regulatory':
            # Use regulatory crawler
            from crawlers.regulatory_announcement_crawler import crawl_regulatory_announcements
            print(f"Crawling {component_key} using regulatory_announcement_crawler...")
            asyncio.run(crawl_regulatory_announcements())
        elif crawler_type == 'hk_ipo':
            # Use HK IPO crawler
            from crawlers.hk_ipo_news_crawler import crawl_hk_ipo_news
            print(f"Crawling {component_key} using hk_ipo_news_crawler...")
            asyncio.run(crawl_hk_ipo_news())
        elif crawler_type == 'global_news':
            # Use global news crawler
            from crawlers.global_news_crawler import crawl_global_news
            print(f"Crawling {component_key} using global_news_crawler...")
            asyncio.run(crawl_global_news())
        elif crawler_type == 'corporate_news':
            # Use master corporate news crawler
            from crawlers.corporate_news_crawler import crawl_corporate_news_from_config
            print(f"Crawling {component_key} using corporate_news_crawler...")
            asyncio.run(crawl_corporate_news_from_config())
        elif crawler_type == 'futu_stock_news':
            # Use Futu stock news crawler (legacy - now part of corporate_news)
            from crawlers.futu_stock_news_crawler import crawl_futu_stock_news_from_config
            print(f"Crawling {component_key} using futu_stock_news_crawler...")
            print("⚠ NOTE: futu_stock_news is now part of corporate_news. Consider using corporate_news instead.")
            asyncio.run(crawl_futu_stock_news_from_config())
        else:
            print(f"❌ Unknown crawler type: {crawler_type}")
            return False
        
        print()
        print(f"✅ {component_key} crawler completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error running {component_key} crawler: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_crawler_data(required_components: set):
    """Check which crawlers successfully generated data for TODAY
    
    Args:
        required_components: Set of component keys that were crawled
    
    Returns:
        Dict mapping component_key to (has_data: bool, data_count: int, details: str)
    """
    import sys
    import json
    from pathlib import Path
    import pandas as pd
    
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow'))
    
    from common.csv_storage import get_csv_path, read_news_items_from_csv, CSV_BASE_DIR
    
    results = {}
    components = get_available_components()
    today = datetime.now()
    
    print()
    print("=" * 80)
    print("CHECKING CRAWLER DATA (FOR TODAY)")
    print("=" * 80)
    print(f"Checking for data dated: {today.strftime('%Y-%m-%d')} ({today.strftime('%B %d, %Y')})")
    print()
    
    for component_key in sorted(required_components):
        if component_key not in components:
            results[component_key] = (False, 0, "Component not found in config")
            continue
        
        component = components[component_key]
        crawler_config = component.get('crawler', {})
        output_config = crawler_config.get('output', {})
        output_type = output_config.get('type', 'csv')
        output_file = output_config.get('file', '')
        
        has_data = False
        data_count = 0
        details = ""
        
        if output_type == 'csv':
            # Check CSV file for today's data
            # Use the output file from config if specified, otherwise use component_key
            if output_file:
                # Use the output file specified in config
                csv_path = CSV_BASE_DIR / output_file
                news_type_for_csv = output_file.replace('.csv', '')
            else:
                # Default: use component_key
                csv_path = get_csv_path(component_key)
                news_type_for_csv = component_key
            
            if csv_path.exists():
                try:
                    # Use read_news_items_from_csv which handles date filtering properly
                    df = read_news_items_from_csv(news_type_for_csv, date=today)
                    data_count = len(df) if not df.empty else 0
                    has_data = data_count > 0
                    if has_data:
                        details = f"CSV file: {csv_path.name} ({data_count} items for today)"
                    else:
                        # Check if file has any data at all
                        df_all = pd.read_csv(csv_path, encoding='utf-8')
                        total_rows = max(0, len(df_all) - 1) if not df_all.empty else 0
                        details = f"CSV file: {csv_path.name} (0 items for today, {total_rows} total rows in file)"
                except Exception as e:
                    details = f"CSV file exists but error reading: {e}"
            else:
                details = f"CSV file not found: {csv_path.name}"
        
        elif output_type == 'json':
            # Check JSON file (for market_snapshot) for today's data
            json_path_str = output_config.get('path', 'workflow/data/market_snapshot/')
            json_file = output_config.get('file', 'market_data.json')
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = Path(script_dir) / json_path_str / json_file
            
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    # market_data.json is a list of daily entries, each with 'date' and 'data' fields
                    if isinstance(json_data, list):
                        # Check if there's today's data
                        today_str = today.strftime("%Y-%m-%d")
                        today_entries = [entry for entry in json_data if entry.get('date') == today_str]
                        if today_entries and len(today_entries) > 0:
                            # Get the data array from today's entry
                            today_data = today_entries[0].get('data', [])
                            data_count = len(today_data) if isinstance(today_data, list) else 0
                            has_data = data_count > 0
                            details = f"JSON file: {json_file} ({data_count} assets for today)"
                        else:
                            # Check total entries in file
                            total_entries = len(json_data)
                            details = f"JSON file: {json_file} (0 entries for today, {total_entries} total entries in file)"
                    else:
                        details = f"JSON file: {json_file} (unexpected format)"
                except Exception as e:
                    details = f"JSON file exists but error reading: {e}"
            else:
                details = f"JSON file not found: {json_path}"
        
        elif output_type == 'google_sheets':
            # For global_news, check CSV for today's data (it saves to both CSV and Google Sheets)
            csv_path = get_csv_path('global_news')
            if csv_path.exists():
                try:
                    # Use read_news_items_from_csv which handles date filtering properly
                    df = read_news_items_from_csv('global_news', date=today)
                    data_count = len(df) if not df.empty else 0
                    has_data = data_count > 0
                    if has_data:
                        details = f"CSV file: global_news.csv ({data_count} items for today) [Also saved to Google Sheets]"
                    else:
                        # Check if file has any data at all
                        df_all = pd.read_csv(csv_path, encoding='utf-8')
                        total_rows = max(0, len(df_all) - 1) if not df_all.empty else 0
                        details = f"CSV file: global_news.csv (0 items for today, {total_rows} total rows) [May be in Google Sheets only]"
                except Exception as e:
                    details = f"CSV file exists but error reading: {e}"
            else:
                details = f"CSV file not found: global_news.csv [May be in Google Sheets only]"
        
        else:
            details = f"Unknown output type: {output_type}"
        
        results[component_key] = (has_data, data_count, details)
    
    # Print summary table
    print(f"{'Component':<20} {'Status':<12} {'Count':<10} {'Details'}")
    print("-" * 80)
    
    for component_key in sorted(required_components):
        has_data, data_count, details = results[component_key]
        component_name = components.get(component_key, {}).get('name', component_key)
        status = "✓ HAS DATA" if has_data else "✗ NO DATA"
        print(f"{component_name:<20} {status:<12} {data_count:<10} {details}")
    
    print()
    
    # Summary
    total = len(results)
    with_data = sum(1 for has_data, _, _ in results.values() if has_data)
    without_data = total - with_data
    
    print(f"Summary: {with_data}/{total} crawlers have data for today, {without_data}/{total} have no data for today")
    if without_data > 0:
        print("⚠ Note: No data for today may indicate:")
        print("   - Crawler failed to run or encountered errors")
        print("   - No news/articles were found for today (this is normal for some components)")
        print("   - Date format mismatch in stored data")
    print()
    
    return results


def run_crawlers():
    """Run all crawlers for required components"""
    import asyncio
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow'))
    
    from run_newsletter_pipeline import run_crawlers, load_newsletter_config, get_required_components, extract_component_customizations
    
    print()
    print("=" * 80)
    print("RUNNING CRAWLERS")
    print("=" * 80)
    print()
    
    try:
        # Load config and get required components
        config = load_newsletter_config()
        newsletters_config = config["newsletters"]
        required_components = get_required_components(newsletters_config)
        component_customizations = extract_component_customizations(newsletters_config)
        
        print(f"Found {len(newsletters_config)} newsletter(s)")
        print(f"Required components: {', '.join(sorted(required_components))}")
        if component_customizations:
            print(f"Component customizations: {', '.join(component_customizations.keys())}")
        print()
        
        # Run crawlers for required components
        asyncio.run(run_crawlers(required_components, component_customizations))
        print()
        print("✅ Crawlers completed successfully!")
        
        # Check which crawlers generated data
        check_crawler_data(required_components)
        
        return True
    except Exception as e:
        print(f"❌ Error running crawlers: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_summarizers():
    """Generate summaries for required components"""
    import asyncio
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow'))
    
    from run_newsletter_pipeline import generate_summaries, load_newsletter_config, get_required_components, extract_component_customizations
    
    print()
    print("=" * 80)
    print("GENERATING SUMMARIES")
    print("=" * 80)
    print()
    
    try:
        # Load config and get required components
        config = load_newsletter_config()
        newsletters_config = config["newsletters"]
        required_components = get_required_components(newsletters_config)
        component_customizations = extract_component_customizations(newsletters_config)
        
        print(f"Found {len(newsletters_config)} newsletter(s)")
        print(f"Required components: {', '.join(sorted(required_components))}")
        if component_customizations:
            print(f"Component customizations: {', '.join(component_customizations.keys())}")
        print()
        
        # Generate summaries for required components
        summaries = asyncio.run(generate_summaries(required_components, component_customizations))
        print()
        print(f"✅ Generated {len(summaries)} summaries!")
        return True
    except Exception as e:
        print(f"❌ Error generating summaries: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_full_pipeline():
    """Run the full pipeline"""
    print()
    print("=" * 80)
    print("RUNNING FULL PIPELINE")
    print("=" * 80)
    print()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pipeline_script = os.path.join(script_dir, 'workflow', 'run_newsletter_pipeline.py')
    
    if not os.path.exists(pipeline_script):
        print(f"❌ Pipeline script not found: {pipeline_script}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, pipeline_script],
            cwd=script_dir,
            check=False
        )
        
        print()
        if result.returncode == 0:
            print("✅ Full pipeline completed successfully!")
            return True
        else:
            print(f"❌ Pipeline exited with code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Error running pipeline: {e}")
        return False


def main():
    """Main menu loop"""
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        try:
            choice = input("Enter your choice (0-5): ").strip()
            
            if choice == '0':
                print()
                print("Exiting...")
                break
            elif choice == '1':
                run_crawlers()
                input("\nPress Enter to continue...")
            elif choice == '1a' or choice == '1A':
                # Component-specific crawler selection
                component_list = print_component_menu()
                if component_list:
                    try:
                        comp_choice = input(f"Select component (1-{len(component_list)}, 0 to cancel): ").strip()
                        if comp_choice == '0':
                            continue
                        comp_idx = int(comp_choice) - 1
                        if 0 <= comp_idx < len(component_list):
                            component_key = component_list[comp_idx]
                            run_specific_component_crawler(component_key)
                        else:
                            print("\n❌ Invalid component selection.")
                    except (ValueError, IndexError):
                        print("\n❌ Invalid input. Please enter a valid number.")
                input("\nPress Enter to continue...")
            elif choice == '2':
                run_summarizers()
                input("\nPress Enter to continue...")
            elif choice == '2a' or choice == '2A':
                # Component-specific summarizer selection
                component_list = print_component_menu()
                if component_list:
                    try:
                        comp_choice = input(f"Select component (1-{len(component_list)}, 0 to cancel): ").strip()
                        if comp_choice == '0':
                            continue
                        comp_idx = int(comp_choice) - 1
                        if 0 <= comp_idx < len(component_list):
                            component_key = component_list[comp_idx]
                            run_specific_component_summarizer(component_key)
                        else:
                            print("\n[ERROR] Invalid component selection.")
                    except (ValueError, IndexError):
                        print("\n[ERROR] Invalid input. Please enter a valid number.")
                input("\nPress Enter to continue...")
            elif choice == '3':
                run_script('generate_newsletter.py', 'Generate Newsletter')
                input("\nPress Enter to continue...")
            elif choice == '4':
                run_send_newsletter_email()
                input("\nPress Enter to continue...")
            elif choice == '5':
                run_full_pipeline()
                input("\nPress Enter to continue...")
            else:
                print("\n❌ Invalid choice. Please enter a number between 0-5, or '1a'/'2a' for component-specific options.")
                input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()

