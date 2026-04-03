"""
Generate Newsletter Config from User Prompt
Uses LLM to parse user's natural language request and generate newsletter configuration
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.openai_utils import initialize_openai_client, chat_completion_with_fallback


def load_component_config() -> Dict:
    """Load component configuration"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "component_config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def generate_config_from_prompt(user_prompt: str, user_email: str = None) -> Dict:
    """Generate newsletter configuration from user prompt
    
    Args:
        user_prompt: Natural language description of desired newsletter
        user_email: Optional user email address
    
    Returns:
        Newsletter configuration dictionary
    """
    client = initialize_openai_client()
    component_config = load_component_config()
    
    # Extract available components
    available_components = list(component_config.get("components", {}).keys())
    component_descriptions = {}
    for comp_id, comp_data in component_config.get("components", {}).items():
        component_descriptions[comp_id] = {
            "name": comp_data.get("name", comp_id),
            "description": comp_data.get("description", "")
        }
    
    # Build prompt for LLM
    system_prompt = f"""You are a newsletter configuration generator. Your task is to parse a user's natural language request and generate a newsletter configuration JSON.

Available components:
{json.dumps(component_descriptions, indent=2)}

For market_snapshot component, you can customize the assets list. Common ticker formats:
- US stocks: "AAPL", "MSFT", "TSLA", "NVDA"
- HK stocks: "0700.HK", "9988.HK", "3690.HK"
- Indices: "^GSPC" (S&P 500), "^NDX" (Nasdaq 100), "^HSI" (Hang Seng Index)

CRITICAL INSTRUCTIONS:
- ONLY include components that are EXPLICITLY mentioned in the user's prompt
- Do NOT add components that are not mentioned (e.g., if user only mentions "financial news", do NOT add "top_news", "global_news", "hk_ipo", or "regulatory")
- Map user's natural language to component names:
  * "financial news" or "global markets" or "economic developments" → "financial_news"
  * "tech news" or "technology" or "startups" or "innovation" → "tech_news"
  * "market snapshot" or "stocks" or "market data" or specific stock names → "market_snapshot"
  * "top news" or "major news" or "important stories" → "top_news"
  * "global news" or "regional news" or "local news" → "global_news"
  * "IPO" or "initial public offering" or "HK IPO" → "hk_ipo"
  * "regulatory" or "announcements" or "HKEX" → "regulatory"
- If the user mentions "financial news", use ONLY "financial_news" component, NOT "top_news" or "global_news"
- If the user mentions "tech news", use ONLY "tech_news" component, NOT "top_news" or "global_news"
- Be precise and minimal - only include what the user explicitly requests

Generate a newsletter configuration that matches the user's request. The configuration should:
1. Include ONLY components explicitly mentioned in the prompt
2. For market_snapshot, include custom assets if specific stocks are mentioned
3. Set appropriate email settings
4. Determine if translation is needed based on language preferences

Return ONLY a valid JSON object matching this structure:
{{
  "name": "newsletter_name",
  "components": ["component1", "component2", ...],
  "component_customizations": {{
    "market_snapshot": {{
      "assets": [
        {{"name": "Stock Name", "ticker": "TICKER", "is_index": false}},
        {{"name": "Index Name", "ticker": "^INDEX", "is_index": true}}
      ],
      "output_file_suffix": "user_specific_suffix"
    }}
  }},
  "recipients": {{
    "en": ["email@example.com"]
  }},
  "email": {{
    "from_email": "david@xplorehk.com",
    "from_name": "Morning Coffee",
    "subject": "Your Daily Newsletter - {{date}}"
  }},
  "language": "EN",
  "translate": false
}}

If the user mentions multiple languages or translation, set "translate": true and include recipients for both "en" and "cn".
"""

    user_prompt_full = f"""User request:
{user_prompt}

User email: {user_email if user_email else "Not provided"}

Generate the newsletter configuration JSON:"""

    print("Generating newsletter configuration from prompt...")
    print(f"User prompt: {user_prompt[:100]}...")
    print()
    
    try:
        # Client is AsyncOpenAI, so await the call
        response = await chat_completion_with_fallback(
            client,
            "light",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        # Parse JSON
        newsletter_config = json.loads(response_text)
        
        # Add user email if provided and not in recipients
        if user_email and "recipients" in newsletter_config:
            if "en" not in newsletter_config["recipients"]:
                newsletter_config["recipients"]["en"] = []
            if user_email not in newsletter_config["recipients"]["en"]:
                newsletter_config["recipients"]["en"].append(user_email)
        
        print("OK Newsletter configuration generated successfully!")
        print()
        print("Generated configuration:")
        print(json.dumps(newsletter_config, indent=2))
        
        return newsletter_config
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON from LLM response: {e}")
        print(f"Response text: {response_text}")
        raise
    except Exception as e:
        print(f"ERROR: Failed to generate configuration: {e}")
        import traceback
        traceback.print_exc()
        raise


async def save_user_config(user_id: str, newsletter_config: Dict):
    """Save newsletter configuration for a user
    
    Args:
        user_id: User identifier
        newsletter_config: Newsletter configuration to save
    """
    from common.user_config_manager import save_user_newsletter_config
    
    # Extract newsletter name to determine filename
    newsletter_name = newsletter_config.get("name")
    
    # Determine if it's a standard newsletter or custom
    if newsletter_name in ["global_newsletter", "market_briefing"]:
        # Save as {user_id}_{newsletter_name}.json
        save_user_newsletter_config(user_id, newsletter_config, newsletter_name=newsletter_name)
        print(f"\nOK Configuration saved: {user_id}_{newsletter_name}.json")
    else:
        # Custom newsletter - save as {user_id}_custom_{name}.json
        custom_name = f"custom_{newsletter_name}"
        save_user_newsletter_config(user_id, newsletter_config, newsletter_name=custom_name)
        print(f"\nOK Configuration saved: {user_id}_{custom_name}.json")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate newsletter configuration from user prompt")
    parser.add_argument("--prompt", type=str, required=True, help="User's natural language prompt")
    parser.add_argument("--user-id", type=str, required=True, help="User ID for saving configuration")
    parser.add_argument("--user-email", type=str, help="User email address")
    parser.add_argument("--save", action="store_true", help="Save configuration to user config file")
    parser.add_argument("--output", type=str, help="Output file path (if not saving to user config)")
    
    args = parser.parse_args()
    
    # Generate configuration
    newsletter_config = await generate_config_from_prompt(args.prompt, args.user_email)
    
    # Save or output
    if args.save:
        await save_user_config(args.user_id, newsletter_config)
    elif args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(newsletter_config, f, indent=2, ensure_ascii=False)
        print(f"\nOK Configuration saved to: {args.output}")
    else:
        print("\n(Use --save to save to user config, or --output <file> to save to file)")


if __name__ == "__main__":
    asyncio.run(main())

