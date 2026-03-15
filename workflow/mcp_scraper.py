"""
Advanced MCP Web Scraper
Uses Playwright browser automation for dynamic news sites
Can be used as a standalone script or imported as a module
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from agents import Agent, OpenAIChatCompletionsModel, Runner, trace
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass  # May already be configured

# Load env when used as standalone
if __name__ == "__main__":
    load_dotenv()


async def scrape_website(url: str, headless: bool = True):
    """
    Scrape a website using Playwright browser automation to extract headlines
    
    Args:
        url: Website URL
        headless: If True, run browser in headless mode (no visible window)
    
    Returns:
        dict with 'headline', 'link', and 'summary' keys
    """
    
    # Define the task for headline extraction
    task = """EXTRACT TODAY'S MAIN NEWS HEADLINE AND ITS LINK:

STEP 1 - Find the headline:
- Look for the most prominent headline on the page (usually at the top, center, or highlighted)
- This should be TODAY's main news story, not an older article
- If there are multiple headlines, pick the LARGEST and MOST PROMINENT one
- Read the text of the headline directly from the page
- CRITICAL: The headline MUST be translated to English if it's in another language

STEP 2 - Get the link:
- Click on the headline you found
- Wait for the page to load completely
- After clicking, capture the CURRENT URL (this is the article link)
- The link should be DIFFERENT from the homepage URL

STEP 3 - Extract content (if possible):
- If you successfully clicked the headline and are on the article page:
  - Read the article content
  - Create a 2-3 bullet point summary in English
  - IMPORTANT: When referring to Donald Trump, always refer to him as "President Donald Trump" or "US President Donald Trump". He is the CURRENT President of the United States as of 2025. Do NOT label him as "Former President" or "Ex-President" - this is incorrect.
- If you couldn't access the article, leave summary empty

CRITICAL OUTPUT FORMAT - Use EXACTLY this format:
Headline: [the actual headline text in English]
Link: [the full article URL after clicking]
Summary: [bullet points or leave blank if not accessible]

IMPORTANT: 
- The Link must be the article URL after clicking, NOT the homepage URL
- Read the headline text exactly as it appears on the page
- CRITICAL: The headline MUST be in English - translate any non-English text to English
- Do NOT include any additional text or explanations
- All output (headline, summary) must be 100% in English"""
    
    # Setup model
    openai_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    )
    
    model = OpenAIChatCompletionsModel(
        model=os.getenv("MODEL_NAME", "deepseek/deepseek-chat"),
        openai_client=openai_client
    )
    
    # Setup Playwright MCP server
    headless_mode = "headless" if headless else "visible browser"
    print(f"🎭 Using Playwright (browser automation - {headless_mode})")
    server_params = {"command": "npx", "args": ["-y", "@playwright/mcp@latest"]}
    
    headless_instruction = "IMPORTANT: Launch the browser with headless=true (no visible window)." if headless else "You can launch the browser with headless=false to show the window."
    
    instructions = f"""You are an expert web scraper with Playwright browser automation.
    {headless_instruction}
    When launching the browser, explicitly use the headless parameter.
    
    Your workflow:
    1. Launch browser and navigate to the news website
    2. Locate the MOST PROMINENT headline on the page (usually large text at top/center)
    3. READ the headline text directly from the page and TRANSLATE to English if needed
    4. CLICK on that headline to go to the article page
    5. WAIT for the page to fully load after clicking
    6. CAPTURE the current URL (this is the article link)
    7. READ the article content and create a summary in English (if accessible)
    
    Key skills:
    - You can navigate pages, wait for JavaScript to load, interact with dynamic content
    - You can click buttons and links, wait for page transitions
    - You can read page content, capture URLs, and extract text
    - Be thorough and accurate in following the step-by-step instructions
    
    CRITICAL REQUIREMENTS: 
    - ALL OUTPUT MUST BE 100% IN ENGLISH - translate any non-English content
    - The headline text must be in English (translate if necessary)
    - Read the headline text BEFORE clicking it
    - Capture the URL AFTER clicking (it should be different from homepage)
    - Follow the exact output format specified in the task
    - Do NOT output anything in languages other than English
    - IMPORTANT: When referring to Donald Trump in summaries, always refer to him as "President Donald Trump" or "US President Donald Trump". He is the CURRENT President of the United States as of 2025. Do NOT label him as "Former President" or "Ex-President" - this is incorrect."""
    agent_name = "PlaywrightScraper"
    
    # Build action with explicit headless instruction
    if headless:
        action = f"""Launch a Playwright browser in HEADLESS mode (headless=true, no visible window), navigate to {url}, and complete the following task:
        
{task}

CRITICAL: You must use headless=true parameter when launching the browser."""
    else:
        action = f"""Launch a Playwright browser with visible window (headless=false), navigate to {url}, and complete the following task:
        
{task}"""
    
    # Scrape
    async with MCPServerStdio(params=server_params, client_session_timeout_seconds=120) as server:
        agent = Agent(
            name=agent_name,
            instructions=instructions,
            model=model,
            mcp_servers=[server]
        )
        
        print(f"🔍 Target: {url}")
        print(f"📋 Task: {task}\n")
        
        with trace("Scraping"):
            result = await Runner.run(agent, action)
        
        raw_output = result.final_output
        
        # Parse the output into structured format
        return parse_headline_output(raw_output, url)


def parse_headline_output(output: str, fallback_url: str) -> dict:
    """
    Parse the agent's output into headline, link, and summary
    
    Args:
        output: Raw text output from agent
        fallback_url: URL to use if link extraction fails
    
    Returns:
        dict with 'headline', 'link', and 'summary' keys
    """
    headline = ""
    link = ""
    summary = ""
    
    lines = output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.lower().startswith('headline:'):
            headline = line.split(':', 1)[1].strip()
        elif line.lower().startswith('link:'):
            link = line.split(':', 1)[1].strip()
        elif line.lower().startswith('summary:'):
            summary = line.split(':', 1)[1].strip()
    
    # Use fallback if link is missing or invalid
    if not link or link in ["#", "javascript:void(0)"]:
        link = fallback_url
    
    # Ensure link has protocol
    if link and not link.startswith(('http://', 'https://')):
        # Try to construct full URL
        from urllib.parse import urljoin
        link = urljoin(fallback_url, link)
    
    return {
        "headline": headline,
        "link": link,
        "summary": summary
    }


async def main():
    print("="*60)
    print("🌐 Advanced MCP Web Scraper - Testing Mode")
    print("="*60)
    print()
    
    # ========================================
    # CUSTOMIZE YOUR SCRAPING HERE:
    # ========================================
    
    # Replace this URL with your website to test
    test_url = "https://www.vaterland.li/"
    print(f"🔍 Testing URL: {test_url}")
    print("📋 Extracting: headline + link + summary")
    print()
    
    # Test with Playwright (handles JavaScript, dynamic content)
    print("🎭 Testing with Playwright (browser automation)...")
    result = await scrape_website(
        url=test_url,
        headless=True          # Run in background (set to False to see browser)
    )
    
    print(result)
    
    print(f"\n✅ Playwright Result:")
    print(f"  📰 Headline: {result.get('headline', 'N/A')}")
    print(f"  🔗 Link: {result.get('link', 'N/A')}")
    print(f"  📄 Summary: {result.get('summary', 'N/A')}")
    
    print("\n" + "="*60)
    print("✨ Testing Complete!")
    print()
    print("💡 Tips:")
    print("  • Change 'test_url' variable to test your website")
    print("  • headless=False      → See browser in action (debugging)")
    print("  • Perfect for news sites with JavaScript and dynamic content")
    print("="*60)


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found")
    else:
        asyncio.run(main())

