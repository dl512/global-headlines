"""
Common utilities for saving summaries to files
"""

import os
from datetime import datetime
from typing import Dict, Optional

from common.url_utils import normalize_markdown_links


def get_summaries_dir() -> str:
    """Get the summaries directory path"""
    workflow_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    summaries_dir = os.path.join(workflow_dir, "summaries")
    return summaries_dir


def ensure_summary_dir(component: str) -> str:
    """Ensure the summary directory for a component exists and return its path"""
    summaries_dir = get_summaries_dir()
    component_dir = os.path.join(summaries_dir, component)
    os.makedirs(component_dir, exist_ok=True)
    return component_dir


def save_summary(component: str, summary: str, date: Optional[datetime] = None, filename: Optional[str] = None) -> str:
    """Save a summary to a file
    
    Args:
        component: Component name (e.g., 'global_news', 'top_news')
        summary: Summary content (markdown)
        date: Optional date (defaults to today)
        filename: Optional custom filename (defaults to date-based)
    
    Returns:
        Full path to saved file
    """
    if date is None:
        date = datetime.now()
    
    component_dir = ensure_summary_dir(component)
    
    if filename is None:
        date_str = date.strftime("%Y%m%d")
        filename = f"{component}_summary_{date_str}.md"
    
    filepath = os.path.join(component_dir, filename)
    # Normalize links (e.g. stheadline.com -> ID-only) so saved files have mobile-safe URLs
    summary = normalize_markdown_links(summary)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    return filepath


def save_all_summaries(summaries: Dict[str, str], date: Optional[datetime] = None) -> Dict[str, str]:
    """Save all summaries to their respective folders
    
    Args:
        summaries: Dictionary mapping component names to summary content
        date: Optional date (defaults to today)
    
    Returns:
        Dictionary mapping component names to file paths
    """
    if date is None:
        date = datetime.now()
    
    saved_files = {}
    
    for component, summary in summaries.items():
        try:
            filepath = save_summary(component, summary, date)
            saved_files[component] = filepath
            print(f"  ✓ Saved {component} summary to: {filepath}")
        except Exception as e:
            print(f"  ✗ Failed to save {component} summary: {e}")
            saved_files[component] = None
    
    return saved_files


def get_latest_summary(component: str) -> Optional[str]:
    """Get the latest summary file path for a component
    
    Args:
        component: Component name
    
    Returns:
        Path to latest summary file, or None if not found
    """
    component_dir = os.path.join(get_summaries_dir(), component)
    
    if not os.path.exists(component_dir):
        return None
    
    files = [f for f in os.listdir(component_dir) if f.endswith('.md') and f.startswith(f"{component}_summary_")]
    
    if not files:
        return None
    
    # Sort by modification time, most recent first
    files.sort(key=lambda x: os.path.getmtime(os.path.join(component_dir, x)), reverse=True)
    return os.path.join(component_dir, files[0])

