"""
Quick script to send the latest Semi AI newsletter email
"""
import os
import sys
import json
import markdown
from datetime import datetime
from pathlib import Path

# Add workflow to path
script_dir = os.path.dirname(os.path.abspath(__file__))
workflow_dir = os.path.join(script_dir, 'workflow')
sys.path.insert(0, workflow_dir)

# Import email function
import importlib.util
email_module_path = os.path.join(workflow_dir, 'common', 'email.py')
spec = importlib.util.spec_from_file_location("workflow_email", email_module_path)
workflow_email = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_email)
send_email = workflow_email.send_email

# Load config
config_path = os.path.join(workflow_dir, 'config', 'user_configs', 'semiconductor_ai_newsletter.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

newsletter_config = config['newsletters'][0]  # Get first (and only) newsletter
email_intro = config.get('email_intro', '')
recipients = newsletter_config.get('recipients', {})
email_config = newsletter_config.get('email', {})

# Find latest newsletter file
newsletter_dir = os.path.join(workflow_dir, 'newsletter', 'semiconductor_ai_newsletter')
newsletter_files = list(Path(newsletter_dir).glob('newsletter_*_en.md'))

if not newsletter_files:
    print(f"[ERROR] No newsletter files found in {newsletter_dir}")
    sys.exit(1)

# Get the latest file (sorted by modification time)
latest_file = max(newsletter_files, key=lambda p: p.stat().st_mtime)
print(f"Found latest newsletter: {latest_file.name}")

# Read newsletter content
with open(latest_file, 'r', encoding='utf-8') as f:
    newsletter_text = f.read()

# Convert to HTML
html_content = markdown.markdown(email_intro + "\n\n" + newsletter_text, extensions=['tables'])

# Format subject
subject = email_config.get('subject', 'Semiconductor / AI Newsletter - {date}').format(
    date=datetime.now().strftime('%B %d, %Y')
)

# Send email
primary_recipient = 'david@xplorehk.com'
en_recipients = recipients.get('en', [])
from_email = email_config.get('from_email')
from_name = email_config.get('from_name', 'Semiconductor / AI Newsletter')

print(f"\nSending newsletter to {primary_recipient} with {len(en_recipients)} BCC recipient(s)...")
if send_email(primary_recipient, subject, html_content, from_email=from_email, from_name=from_name, bcc_emails=en_recipients):
    print(f"[OK] Newsletter sent successfully!")
else:
    print(f"[ERROR] Failed to send newsletter")
    sys.exit(1)

