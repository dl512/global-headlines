"""
Link Cache Module
Stores and checks previously processed links to avoid reprocessing
"""

import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set
import hashlib

# Base directory for link cache
CACHE_BASE_DIR = Path(__file__).parent.parent / "data" / "link_cache"
CACHE_BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_file_path(website: str) -> Path:
    """Get the cache file path for a website
    
    Args:
        website: Website URL (e.g., "https://www.futunn.com/hk/stock/01347-HK/news")
    
    Returns:
        Path to the cache file
    """
    # Create a hash of the website URL to use as filename (to avoid filesystem issues with special chars)
    url_hash = hashlib.md5(website.encode('utf-8')).hexdigest()
    return CACHE_BASE_DIR / f"{url_hash}.json"


def normalize_url(url: str) -> str:
    """Normalize URL for consistent comparison
    
    Args:
        url: URL string
    
    Returns:
        Normalized URL (lowercase, remove trailing slash, remove query params for some sites)
    """
    if not url:
        return ""
    
    url = url.strip().lower()
    
    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    # For some sites, we might want to remove query parameters
    # But for now, keep them as they might be important
    
    return url


def load_seen_links(website: str) -> Set[str]:
    """Load previously seen links for a website
    
    Args:
        website: Website URL
    
    Returns:
        Set of normalized URLs that have been seen before
    """
    cache_file = get_cache_file_path(website)
    
    if not cache_file.exists():
        return set()
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Return set of normalized URLs
            return {normalize_url(url) for url in data.get('links', [])}
    except Exception as e:
        print(f"WARNING: Failed to load link cache for {website}: {e}")
        return set()


def save_seen_link(website: str, url: str, headline: Optional[str] = None, was_relevant: Optional[bool] = None):
    """Save a link to the cache
    
    Args:
        website: Website URL
        url: Link URL that was processed
        headline: Optional headline (for reference)
        was_relevant: Optional flag indicating if link was relevant (for debugging)
    """
    cache_file = get_cache_file_path(website)
    
    # Load existing data
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {'website': website, 'links': [], 'metadata': {}}
    else:
        data = {'website': website, 'links': [], 'metadata': {}}
    
    # Normalize URL
    normalized_url = normalize_url(url)
    
    # Add link if not already present
    if normalized_url not in data['links']:
        data['links'].append(normalized_url)
        
        # Store metadata if provided
        if headline or was_relevant is not None:
            if 'metadata' not in data:
                data['metadata'] = {}
            data['metadata'][normalized_url] = {
                'headline': headline,
                'was_relevant': was_relevant,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
        else:
            # Update last_seen if metadata exists
            if 'metadata' in data and normalized_url in data['metadata']:
                data['metadata'][normalized_url]['last_seen'] = datetime.now().isoformat()
    
    # Save back to file
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"WARNING: Failed to save link cache for {website}: {e}")


def is_link_seen(website: str, url: str) -> bool:
    """Check if a link has been seen before
    
    Args:
        website: Website URL
        url: Link URL to check
    
    Returns:
        True if link has been seen before, False otherwise
    """
    seen_links = load_seen_links(website)
    normalized_url = normalize_url(url)
    return normalized_url in seen_links


def get_link_relevance_status(website: str, url: str) -> Optional[bool]:
    """Get the relevance status of a cached link
    
    Args:
        website: Website URL
        url: Link URL to check
    
    Returns:
        True if link was marked as relevant, False if marked as not relevant, None if not cached or status unknown
    """
    cache_file = get_cache_file_path(website)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            normalized_url = normalize_url(url)
            metadata = data.get('metadata', {})
            if normalized_url in metadata:
                return metadata[normalized_url].get('was_relevant')
    except Exception as e:
        print(f"WARNING: Failed to read link cache metadata for {website}: {e}")
    
    return None


def clear_cache(website: Optional[str] = None):
    """Clear the link cache for a specific website or all websites
    
    Args:
        website: Website URL to clear cache for (if None, clears all)
    """
    if website:
        cache_file = get_cache_file_path(website)
        if cache_file.exists():
            cache_file.unlink()
            print(f"Cleared cache for {website}")
    else:
        # Clear all cache files
        for cache_file in CACHE_BASE_DIR.glob("*.json"):
            cache_file.unlink()
        print("Cleared all link caches")

