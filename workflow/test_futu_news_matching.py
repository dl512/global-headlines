"""
Test script for debugging Futu News headline-to-link matching
This script isolates the issue and provides detailed debugging output
"""

import asyncio
import json
import sys
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.openai_utils import initialize_openai_client
from common import extract_html
from crawlers.generic_news_crawler import (
    extract_top_headlines,
    extract_links_from_html,
    match_headline_to_link,
    remove_html_tags
)


async def test_futu_news_matching():
    """Test Futu News headline and link extraction"""
    
    website = "https://news.futunn.com/en/main"
    
    print("=" * 80)
    print("FUTU NEWS MATCHING TEST")
    print("=" * 80)
    print(f"\nTesting website: {website}\n")
    
    # Step 1: Extract HTML
    print("Step 1: Extracting HTML...")
    html_dict = extract_html.get_raw_html(website)
    
    if not html_dict or not html_dict.get("html"):
        print(f"ERROR: Failed to retrieve HTML from {website}")
        return
    
    html_string = html_dict["html"]
    html_size = len(html_string)
    print(f"[OK] Retrieved HTML ({html_size:,} characters, {html_size / 1024:.1f} KB)")
    
    # Step 2: Extract headlines
    print("\n" + "=" * 80)
    print("Step 2: Extracting headlines...")
    print("=" * 80)
    
    client = initialize_openai_client()
    special_handling = {"is_futu_news": True}
    
    clean_text = remove_html_tags(html_string)
    if len(html_string) > 200000:
        html_string_input = clean_text[:200000]
    else:
        html_string_input = html_string
    
    headlines = await extract_top_headlines(client, website, html_string_input, special_handling)
    
    if not headlines:
        print("ERROR: No headlines extracted")
        return
    
    print(f"\n[OK] Extracted {len(headlines)} headlines:")
    for i, headline in enumerate(headlines, 1):
        print(f"  {i}. {headline}")
    
    # Step 3: Extract links
    print("\n" + "=" * 80)
    print("Step 3: Extracting links from HTML...")
    print("=" * 80)
    
    links_on_page = extract_links_from_html(html_string, website)
    
    if not links_on_page:
        print("ERROR: No links extracted")
        return
    
    # Parse links to show structure
    links_list = []
    for match in re.finditer(r'\[([^\]]+)\]\(([^\)]+)\)', links_on_page):
        link_text = match.group(1)
        link_url = match.group(2)
        links_list.append({"text": link_text, "url": link_url})
    
    print(f"\n[OK] Extracted {len(links_list)} links")
    print(f"\nSample links (first 20):")
    for i, link in enumerate(links_list[:20], 1):
        print(f"  {i}. [{link['text'][:60]}...]({link['url']})")
    
    print(f"\nTotal links: {len(links_list)}")
    print(f"Links data size: {len(links_on_page):,} characters")
    
    # Step 4: Test matching for specific headlines
    print("\n" + "=" * 80)
    print("Step 4: Testing headline-to-link matching...")
    print("=" * 80)
    
    # Test with first few headlines
    test_headlines = headlines[:5]
    
    for i, headline in enumerate(test_headlines, 1):
        print(f"\n{'-' * 80}")
        print(f"Test {i}/{len(test_headlines)}: {headline}")
        print(f"{'-' * 80}")
        
        # Search for keywords in links
        headline_words = [w.lower() for w in headline.split() if len(w) > 3]
        print(f"\nHeadline keywords: {headline_words[:10]}")
        
        # Find links that contain these keywords
        matching_links = []
        for link in links_list:
            link_text_lower = link['text'].lower()
            url_lower = link['url'].lower()
            
            # Count keyword matches
            matches = sum(1 for word in headline_words if word in link_text_lower or word in url_lower)
            if matches > 0:
                matching_links.append({
                    "link": link,
                    "match_count": matches,
                    "matched_words": [w for w in headline_words if w in link_text_lower or w in url_lower]
                })
        
        # Sort by match count
        matching_links.sort(key=lambda x: x['match_count'], reverse=True)
        
        print(f"\nFound {len(matching_links)} links with matching keywords:")
        for j, match_info in enumerate(matching_links[:10], 1):  # Show top 10
            link = match_info['link']
            print(f"  {j}. [{link['text'][:60]}...]")
            print(f"     URL: {link['url']}")
            print(f"     Matches: {match_info['match_count']} keywords: {match_info['matched_words'][:5]}")
        
        # Now try the LLM matching
        print(f"\n>> Attempting LLM-based matching...")
        matched_url = await match_headline_to_link(client, headline, links_on_page, website)
        
        if matched_url:
            print(f"[OK] LLM matched URL: {matched_url}")
            # Check if this URL is in our matching links
            found_in_list = any(m['link']['url'] == matched_url for m in matching_links)
            if found_in_list:
                print(f"  >> This URL was found in our keyword search!")
            else:
                print(f"  >> This URL was NOT in our keyword search (LLM found it differently)")
        else:
            print(f"[FAIL] LLM could not find a matching URL")
            
            # If we found matching links but LLM didn't, show them
            if matching_links:
                print(f"\n  [WARNING] But we found {len(matching_links)} links with matching keywords!")
                print(f"  Best match: {matching_links[0]['link']['url']}")
                print(f"  Link text: {matching_links[0]['link']['text']}")
    
    # Step 5: Show all unique URL patterns
    print("\n" + "=" * 80)
    print("Step 5: Analyzing URL patterns...")
    print("=" * 80)
    
    url_patterns = {}
    for link in links_list:
        url = link['url']
        parsed = urlparse(url)
        path = parsed.path
        
        # Categorize by path structure
        if '/en/main' in path:
            if path == '/en/main' or path == '/en/main/':
                pattern = 'BASE_PAGE'
            else:
                # Extract pattern after /en/main/
                parts = path.split('/en/main/')
                if len(parts) > 1:
                    next_part = parts[1].split('/')[0]
                    pattern = f'/en/main/{next_part}/...'
                else:
                    pattern = 'UNKNOWN_PATTERN'
        elif '/news/' in path:
            pattern = '/news/...'
        elif '/article/' in path:
            pattern = '/article/...'
        elif '/main/' in path:
            pattern = '/main/...'
        else:
            pattern = 'OTHER'
        
        if pattern not in url_patterns:
            url_patterns[pattern] = []
        url_patterns[pattern].append(link)
    
    print(f"\nURL Patterns found:")
    for pattern, links in sorted(url_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n  {pattern}: {len(links)} links")
        if len(links) <= 5:
            for link in links:
                print(f"    - {link['url']}")
        else:
            print(f"    Sample URLs:")
            for link in links[:3]:
                print(f"      - {link['url']}")
            print(f"      ... and {len(links) - 3} more")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_futu_news_matching())

