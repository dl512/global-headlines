"""
User Config Manager
Handles loading, saving, and managing user-specific newsletter configurations
Supports multiple config files per user (global_newsletter, market_briefing, custom_*)
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Base config directory
CONFIG_DIR = Path(__file__).parent.parent / "config"
USER_CONFIGS_DIR = CONFIG_DIR / "user_configs"


def ensure_user_configs_dir():
    """Ensure the user_configs directory exists"""
    USER_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def get_user_config_path(user_id: str, newsletter_name: str = None) -> Path:
    """Get the path to a user's newsletter config file
    
    Args:
        user_id: Unique identifier for the user
        newsletter_name: Optional newsletter name (e.g., "global_newsletter", "market_briefing", "custom_tech_news")
                        If None, returns the old format path for backward compatibility
    
    Returns:
        Path to user's config file
    """
    ensure_user_configs_dir()
    
    if newsletter_name:
        # New format: {user_id}_{newsletter_name}.json
        return USER_CONFIGS_DIR / f"{user_id}_{newsletter_name}.json"
    else:
        # Old format: {user_id}_newsletter_config.json (for backward compatibility)
        return USER_CONFIGS_DIR / f"{user_id}_newsletter_config.json"




def load_all_user_configs(user_id: str = None) -> Dict:
    """Load all newsletter configs from user_configs folder
    
    Args:
        user_id: Optional user ID to filter configs. If None, loads all configs from all users.
    
    Returns:
        Combined newsletter config dictionary with all newsletters from all config files
    """
    ensure_user_configs_dir()
    
    # Get all JSON files in user_configs directory
    if user_id:
        # Filter by user_id
        pattern = f"{user_id}_*.json"
    else:
        # Get all config files (excluding backups)
        pattern = "*.json"
    
    config_files = list(USER_CONFIGS_DIR.glob(pattern))
    
    # Filter out backup files
    config_files = [f for f in config_files if "backup" not in f.name]
    
    # Combine all newsletters
    all_newsletters = []
    newsletter_names = set()
    email_intro = ""
    
    # Load from each user config file
    for config_file in sorted(config_files):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # Get email_intro (use first non-empty one found)
            if not email_intro and user_config.get("email_intro"):
                email_intro = user_config.get("email_intro")
            
            # Add newsletters from this file
            for newsletter in user_config.get("newsletters", []):
                name = newsletter.get("name")
                if name:
                    # If newsletter with same name exists, replace it (user configs take precedence)
                    if name in newsletter_names:
                        # Remove old one
                        all_newsletters = [n for n in all_newsletters if n.get("name") != name]
                    all_newsletters.append(newsletter)
                    newsletter_names.add(name)
        except Exception as e:
            print(f"WARNING: Error loading config file {config_file.name}: {e}")
            continue
    
    return {
        "email_intro": email_intro,
        "newsletters": all_newsletters
    }


def load_user_newsletter_config(user_id: str) -> Dict:
    """Load a user's newsletter configuration (backward compatibility)
    
    This function maintains backward compatibility with the old single-file-per-user format.
    For new code, use load_all_user_configs() instead.
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        User's newsletter config dictionary (merged with base if user config exists)
    """
    # Try new format first (load all configs for this user)
    all_configs = load_all_user_configs(user_id=user_id)
    
    # If we found user-specific configs, return them
    user_config_path = get_user_config_path(user_id)
    if user_config_path.exists() or any(f.name.startswith(f"{user_id}_") for f in USER_CONFIGS_DIR.glob(f"{user_id}_*.json") if "backup" not in f.name):
        return all_configs
    
    # Otherwise, return empty config structure
    return {
        "email_intro": "",
        "newsletters": []
    }


def save_user_newsletter_config(user_id: str, newsletter_config: Dict, newsletter_name: str = None, backup: bool = True) -> Path:
    """Save a newsletter configuration for a user
    
    Args:
        user_id: Unique identifier for the user
        newsletter_config: Newsletter configuration dictionary (can be a single newsletter or full config)
        newsletter_name: Optional newsletter name. If provided, saves as {user_id}_{newsletter_name}.json
                        If None, extracts from newsletter_config or uses old format
        backup: Whether to create a backup of existing config
    
    Returns:
        Path to the saved config file
    """
    ensure_user_configs_dir()
    
    # Determine newsletter name
    if not newsletter_name:
        # Try to extract from newsletter_config
        if "newsletters" in newsletter_config and len(newsletter_config["newsletters"]) > 0:
            newsletter_name = newsletter_config["newsletters"][0].get("name")
        elif "name" in newsletter_config:
            # It's a single newsletter dict
            newsletter_name = newsletter_config.get("name")
        else:
            # Use old format for backward compatibility
            newsletter_name = None
    
    # Determine file path
    if newsletter_name:
        user_config_path = get_user_config_path(user_id, newsletter_name)
    else:
        user_config_path = get_user_config_path(user_id)
    
    # Create backup if requested and file exists
    if backup and user_config_path.exists():
        backup_path = user_config_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(user_config_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    # Prepare config structure
    # If newsletter_config is a single newsletter dict, wrap it
    if "name" in newsletter_config and "components" in newsletter_config:
        # It's a single newsletter, wrap it
        config_to_save = {
            "email_intro": "",
            "newsletters": [newsletter_config]
        }
    elif "newsletters" in newsletter_config:
        # It's already a full config
        config_to_save = newsletter_config
    else:
        raise ValueError("Invalid newsletter config structure")
    
    # Validate config structure
    if "newsletters" not in config_to_save:
        raise ValueError("Config must contain 'newsletters' key")
    
    # Save user config
    with open(user_config_path, 'w', encoding='utf-8') as f:
        json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    
    return user_config_path


def add_newsletter_to_user_config(user_id: str, newsletter_config: Dict, backup: bool = True) -> Dict:
    """Add or update a newsletter in user's config (backward compatibility)
    
    Args:
        user_id: Unique identifier for the user
        newsletter_config: Newsletter configuration dictionary
        backup: Whether to create a backup
    
    Returns:
        Updated user config dictionary
    """
    # Load existing config
    try:
        existing_config = load_user_newsletter_config(user_id)
    except:
        # If user config doesn't exist, start with empty config
        existing_config = {
            "email_intro": "",
            "newsletters": []
        }
    
    # Add or update newsletter
    newsletter_name = newsletter_config.get("name")
    existing_newsletters = existing_config.get("newsletters", [])
    
    # Check if newsletter with same name exists
    updated = False
    for i, existing_newsletter in enumerate(existing_newsletters):
        if existing_newsletter.get("name") == newsletter_name:
            existing_newsletters[i] = newsletter_config
            updated = True
            break
    
    if not updated:
        existing_newsletters.append(newsletter_config)
    
    existing_config["newsletters"] = existing_newsletters
    
    # Save
    save_user_newsletter_config(user_id, existing_config, backup=backup)
    
    return existing_config


def remove_newsletter_from_user_config(user_id: str, newsletter_name: str, backup: bool = True) -> Dict:
    """Remove a newsletter from user's config
    
    Args:
        user_id: Unique identifier for the user
        newsletter_name: Name of newsletter to remove
        backup: Whether to create a backup
    
    Returns:
        Updated user config dictionary
    """
    # Load existing config
    try:
        existing_config = load_user_newsletter_config(user_id)
    except:
        return {"email_intro": "", "newsletters": []}
    
    # Remove newsletter
    existing_newsletters = existing_config.get("newsletters", [])
    existing_newsletters = [n for n in existing_newsletters if n.get("name") != newsletter_name]
    existing_config["newsletters"] = existing_newsletters
    
    # Save
    save_user_newsletter_config(user_id, existing_config, backup=backup)
    
    return existing_config


def list_user_newsletters(user_id: str = None) -> List[str]:
    """List all newsletter names for a user (or all users if user_id is None)
    
    Args:
        user_id: Optional user ID to filter
    
    Returns:
        List of newsletter names
    """
    config = load_all_user_configs(user_id=user_id)
    return [n.get("name") for n in config.get("newsletters", []) if n.get("name")]


def get_user_newsletter(user_id: str, newsletter_name: str) -> Optional[Dict]:
    """Get a specific newsletter config for a user
    
    Args:
        user_id: Unique identifier for the user
        newsletter_name: Name of the newsletter
    
    Returns:
        Newsletter config dictionary or None if not found
    """
    config = load_all_user_configs(user_id=user_id)
    for newsletter in config.get("newsletters", []):
        if newsletter.get("name") == newsletter_name:
            return newsletter
    return None


def validate_newsletter_config(config: Dict) -> bool:
    """Validate newsletter configuration structure
    
    Args:
        config: Newsletter configuration dictionary
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    
    if "newsletters" not in config:
        raise ValueError("Config must contain 'newsletters' key")
    
    if not isinstance(config["newsletters"], list):
        raise ValueError("'newsletters' must be a list")
    
    for newsletter in config["newsletters"]:
        if not isinstance(newsletter, dict):
            raise ValueError("Each newsletter must be a dictionary")
        if "name" not in newsletter:
            raise ValueError("Each newsletter must have a 'name' key")
        if "components" not in newsletter:
            raise ValueError("Each newsletter must have a 'components' key")
    
    return True
