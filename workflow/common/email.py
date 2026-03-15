"""
Common utilities for sending emails via Mailjet
"""

import os
import sys
from typing import Optional, List
from mailjet_rest import Client
from dotenv import load_dotenv

# Find project root (where .env file should be)
# This file is in workflow/common/, so go up 2 levels
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, '.env')

# Load .env file from project root
# Try multiple approaches to ensure we find the .env file
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
elif os.path.exists('.env'):
    # If running from project root
    load_dotenv('.env', override=True)
else:
    # Fallback: try to find .env in current directory or parent directories
    load_dotenv(override=True)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    bcc_emails: Optional[List[str]] = None
) -> bool:
    """Send an email via Mailjet
    
    Args:
        to_email: Primary recipient email address
        subject: Email subject
        html_content: HTML content of the email
        from_email: Sender email (defaults to env variable)
        from_name: Sender name (defaults to env variable)
        bcc_emails: Optional list of BCC recipient email addresses
    
    Returns:
        True if successful, False otherwise
    """
    # Support both naming conventions: MAILJET_API_KEY/MJ_APIKEY_PUBLIC
    api_key = os.getenv('MAILJET_API_KEY') or os.getenv('MJ_APIKEY_PUBLIC')
    api_secret = os.getenv('MAILJET_API_SECRET') or os.getenv('MJ_APIKEY_PRIVATE')
    
    if not api_key or not api_secret:
        print("ERROR: Mailjet API credentials not found in environment variables")
        print("  Looking for: MAILJET_API_KEY or MJ_APIKEY_PUBLIC")
        print("  Looking for: MAILJET_API_SECRET or MJ_APIKEY_PRIVATE")
        return False
    
    if from_email is None:
        from_email = os.getenv('MAILJET_FROM_EMAIL', 'noreply@example.com')
    
    if from_name is None:
        from_name = os.getenv('MAILJET_FROM_NAME', 'Newsletter')
    
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    
    # Build message structure
    message = {
        'From': {
            'Email': from_email,
            'Name': from_name
        },
        'To': [
            {
                'Email': to_email,
                'Name': ''
            }
        ],
        'Subject': subject,
        'HTMLPart': html_content
    }
    
    # Add BCC recipients if provided
    if bcc_emails:
        message['Bcc'] = [
            {
                'Email': email,
                'Name': ''
            }
            for email in bcc_emails
        ]
    
    data = {
        'Messages': [message]
    }
    
    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            bcc_count = len(bcc_emails) if bcc_emails else 0
            if bcc_count > 0:
                print(f"Email sent successfully to {to_email} with {bcc_count} BCC recipient(s)")
            else:
                print(f"Email sent successfully to {to_email}")
            return True
        else:
            print(f"ERROR: Failed to send email. Status code: {result.status_code}")
            print(f"Response: {result.json()}")
            return False
    except Exception as e:
        print(f"ERROR: Exception while sending email: {e}")
        return False

