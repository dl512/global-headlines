"""
Daily Global Headlines Pipeline
Runs the complete workflow:
1. Update headlines in Google Sheet
2. Generate global news summary from Google Sheet
3. Generate daily news summary from top news sites
4. Combine both summaries into final newsletter
5. Translate newsletter to Chinese
6. Send both newsletters via email

Usage:
    python run_daily_pipeline.py
    python run_daily_pipeline.py          # Quick mode (default, no MCP)
    python run_daily_pipeline.py --full   # Full mode with MCP fallback
    python run_daily_pipeline.py --skip-update  # Skip headline update
    python run_daily_pipeline.py --skip-email  # Skip email sending
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import markdown

# Add workflow directory to path
workflow_dir = os.path.join(os.path.dirname(__file__), 'workflow')
sys.path.insert(0, workflow_dir)
sys.path.insert(0, os.path.join(workflow_dir, 'common'))

# Import from new modular structure
from crawlers.global_news_crawler import crawl_global_news
from crawlers.top_news_crawler import crawl_top_news
from summarizers.global_news_summarizer import summarize_global_news
from summarizers.top_news_summarizer import summarize_top_news
from generate_newsletter import generate_newsletter, save_newsletter, find_latest_file, read_file_content
from common.translation import translate_to_chinese
from common.email import send_email


# Load environment variables
load_dotenv(override=True)


async def main():
    """Main pipeline function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run daily global headlines pipeline')
    parser.add_argument('--full', action='store_true', 
                        help='Full mode with MCP fallback (default is quick mode)')
    parser.add_argument('--mcp', action='store_true',
                        help='Full mode with MCP fallback (same as --full)')
    parser.add_argument('--skip-update', action='store_true',
                        help='Skip headline update step')
    parser.add_argument('--skip-email', action='store_true',
                        help='Skip email sending step')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DAILY GLOBAL HEADLINES PIPELINE")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    use_full_mode = args.full or args.mcp
    if use_full_mode:
        print("Mode: FULL (with MCP fallback)")
    else:
        print("Mode: QUICK (traditional scraping only, default)")
    print("=" * 80)
    print()
    
    success_count = 0
    error_count = 0
    
    # Step 1: Crawl global news
    if not args.skip_update:
        print("STEP 1: Crawling global news...")
        print("-" * 80)
        try:
            await crawl_global_news()
            success_count += 1
            print("\n✅ Global news crawled successfully!")
        except Exception as e:
            print(f"\n❌ Failed to crawl global news: {e}")
            error_count += 1
            # Continue with pipeline even if crawl fails (might have existing data)
        print()
    else:
        print("STEP 1: SKIPPED (--skip-update flag)")
        print()
    
    # Step 2: Crawl top news
    print("STEP 2: Crawling top news...")
    print("-" * 80)
    try:
        await crawl_top_news()
        success_count += 1
        print("✅ Top news crawled successfully!")
    except Exception as e:
        print(f"❌ Failed to crawl top news: {e}")
        error_count += 1
    print()
    
    # Step 3: Generate global news summary
    print("STEP 3: Generating global news summary...")
    print("-" * 80)
    global_summary = None
    try:
        global_summary = await summarize_global_news()
        if global_summary:
            success_count += 1
            print("✅ Global news summary generated successfully!")
        else:
            print("❌ Failed to generate global news summary")
            error_count += 1
    except Exception as e:
        print(f"❌ Failed to generate global news summary: {e}")
        error_count += 1
    print()
    
    # Step 4: Generate top news summary
    print("STEP 4: Generating top news summary...")
    print("-" * 80)
    top_summary = None
    try:
        top_summary = await summarize_top_news()
        if top_summary:
            success_count += 1
            print("✅ Top news summary generated successfully!")
        else:
            print("❌ Failed to generate top news summary")
            error_count += 1
    except Exception as e:
        print(f"❌ Failed to generate top news summary: {e}")
        error_count += 1
    print()
    
    # Step 5: Generate newsletter from summaries
    print("STEP 5: Generating newsletter from summaries...")
    print("-" * 80)
    newsletter_en = None
    en_file = None
    if global_summary and top_summary:
        try:
            newsletter_en = generate_newsletter(global_summary, top_summary)
            if newsletter_en:
                en_file = save_newsletter(newsletter_en)
                success_count += 1
                print("✅ Newsletter generated successfully!")
            else:
                print("❌ Failed to combine newsletter")
                error_count += 1
        except Exception as e:
            print(f"❌ Failed to combine newsletter: {e}")
            error_count += 1
    else:
        print("❌ Missing summaries - cannot combine newsletter")
        if not global_summary:
            print("   Missing: global news summary")
        if not top_summary:
            print("   Missing: top news summary")
        error_count += 1
    print()
    
    # Step 6: Translate newsletter to Chinese
    print("STEP 6: Translating newsletter to Chinese...")
    print("-" * 80)
    newsletter_cn = None
    cn_file = None
    if en_file:
        try:
            # Read English newsletter
            with open(en_file, 'r', encoding='utf-8') as f:
                newsletter_en_text = f.read()
            
            # Translate using common module
            newsletter_cn = await translate_to_chinese(newsletter_en_text)
            if newsletter_cn:
                # Generate the expected CN filename
                if en_file.endswith('_en.md'):
                    cn_file = en_file.replace('_en.md', '_cn.md')
                else:
                    cn_file = en_file[:-3] + '_cn.md'
                
                # Save translated newsletter
                with open(cn_file, 'w', encoding='utf-8') as f:
                    f.write(newsletter_cn)
                
                success_count += 1
                print("✅ Newsletter translated successfully!")
            else:
                print("❌ Failed to translate newsletter")
                error_count += 1
        except Exception as e:
            print(f"❌ Failed to translate newsletter: {e}")
            error_count += 1
    else:
        print("❌ No English newsletter to translate")
        error_count += 1
    print()
    
    if not newsletter_en:
        print("=" * 80)
        print("Pipeline failed: No English newsletter generated")
        print(f"Errors: {error_count}")
        print("=" * 80)
        sys.exit(1)
    
    # Step 6: Send both newsletters via email
    if not args.skip_email:
        print("STEP 6: Sending newsletters via email...")
        print("-" * 80)
        
        # Load config
        config_path = os.path.join(workflow_dir, 'config', 'newsletter_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Use first newsletter config (global_newsletter) for email settings
            newsletter_config = config['newsletters'][0] if config.get('newsletters') else {}
            recipients = newsletter_config.get('recipients', {"en": ["davidlau512@gmail.com"], "cn": ["davidlau512@gmail.com"]})
            email_config = newsletter_config.get('email', {})
            email_intro = config.get('email_intro', '')
        except Exception as e:
            print(f"⚠️  Failed to load config: {e}, using defaults")
            recipients = {"en": ["davidlau512@gmail.com"], "cn": ["davidlau512@gmail.com"]}
            email_config = {}
            email_intro = ""
        
        en_recipients = recipients.get('en', [])
        cn_recipients = recipients.get('cn', [])
        from_email = email_config.get('from_email')
        from_name = email_config.get('from_name', 'Global Headlines')
        
        if not en_recipients and not cn_recipients:
            print("⚠️  No email recipients found in config")
        else:
            # Send English newsletter
            if en_file and en_recipients:
                try:
                    with open(en_file, 'r', encoding='utf-8') as f:
                        newsletter_text = f.read()
                    html_content = markdown.markdown(email_intro + "\n\n" + newsletter_text, extensions=['tables'])
                    subject = email_config.get('subject', 'Global Headlines Newsletter - {date}').format(date=datetime.now().strftime('%B %d, %Y'))
                    
                    # Send to each recipient
                    for recipient in en_recipients:
                        en_sent = send_email(recipient, subject, html_content, from_email=from_email, from_name=from_name)
                        if en_sent:
                            success_count += 1
                        else:
                            error_count += 1
                except Exception as e:
                    print(f"❌ Error sending English newsletter: {e}")
                    error_count += 1
            elif en_file and not en_recipients:
                print("⚠️  No English recipients found in config - skipping EN newsletter")
            
            # Send Chinese newsletter
            if cn_file and cn_recipients:
                try:
                    with open(cn_file, 'r', encoding='utf-8') as f:
                        newsletter_text = f.read()
                    html_content = markdown.markdown(email_intro + "\n\n" + newsletter_text, extensions=['tables'])
                    subject = f"Global Headlines Newsletter (繁體中文版) - {datetime.now().strftime('%B %d, %Y')}"
                    
                    # Send to each recipient
                    for recipient in cn_recipients:
                        cn_sent = send_email(recipient, subject, html_content, from_email=from_email, from_name=from_name)
                        if cn_sent:
                            success_count += 1
                        else:
                            error_count += 1
                except Exception as e:
                    print(f"❌ Error sending Chinese newsletter: {e}")
                    error_count += 1
            elif cn_file and not cn_recipients:
                print("⚠️  No Chinese recipients found in config - skipping CN newsletter")
        
        print()
    else:
        print("STEP 3: SKIPPED (--skip-email flag)")
        print()
    
    # Summary
    print("=" * 80)
    print("PIPELINE COMPLETION SUMMARY")
    print("=" * 80)
    print(f"Successful steps: {success_count}")
    print(f"Failed steps: {error_count}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())



