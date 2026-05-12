"""
Load .env files for global_headlines + hkex scripts.

Order:
1. ``<repo>/.env``
2. ``<repo>/hkex/.env`` (overrides duplicate keys — useful when running from ``hkex/``)

If neither exists, falls back to current-directory ``.env`` or python-dotenv search.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


def project_root() -> str:
    """global_headlines/ (parent of workflow/)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_project_dotenv() -> None:
    root = project_root()
    env_path = os.path.join(root, ".env")
    hkex_env_path = os.path.join(root, "hkex", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    if os.path.exists(hkex_env_path):
        load_dotenv(hkex_env_path, override=True)
    if not os.path.exists(env_path) and not os.path.exists(hkex_env_path):
        if os.path.exists(".env"):
            load_dotenv(".env", override=True)
        else:
            load_dotenv(override=True)
