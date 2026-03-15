"""
Script to copy the latest newsletter files to the public folder for website display
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def get_latest_newsletter(newsletter_dir, pattern="newsletter_*_en.md"):
    """Get the latest newsletter file from a directory"""
    newsletter_path = Path(newsletter_dir)
    if not newsletter_path.exists():
        return None
    
    files = list(newsletter_path.glob(pattern))
    if not files:
        return None
    
    # Sort by modification time, get the latest
    latest = max(files, key=lambda f: f.stat().st_mtime)
    return latest

def update_website_samples():
    """Copy latest newsletters to public folder"""
    project_root = Path(__file__).parent
    public_dir = project_root / "public" / "newsletters"
    workflow_dir = project_root / "workflow" / "newsletter"
    
    # Create newsletters directory if it doesn't exist
    public_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy Global Headlines newsletter
    global_newsletter_dir = workflow_dir / "global_newsletter"
    global_file = get_latest_newsletter(global_newsletter_dir)
    if global_file:
        dest = public_dir / "global_headlines_sample.md"
        shutil.copy2(global_file, dest)
        print(f"✓ Copied Global Headlines: {global_file.name} -> {dest.name}")
    else:
        print("⚠ No Global Headlines newsletter found")
    
    # Copy Market Briefing newsletter
    market_briefing_dir = workflow_dir / "market_briefing"
    market_file = get_latest_newsletter(market_briefing_dir)
    if market_file:
        dest = public_dir / "market_briefing_sample.md"
        shutil.copy2(market_file, dest)
        print(f"✓ Copied Market Briefing: {market_file.name} -> {dest.name}")
    else:
        print("⚠ No Market Briefing newsletter found")
    
    print(f"\n✓ Website samples updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    update_website_samples()

