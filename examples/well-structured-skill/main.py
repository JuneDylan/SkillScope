import os
import json
from typing import Any


def analyze_text(text: str) -> dict[str, Any]:
    """Analyze text content and return structured results."""
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")

    try:
        result = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "has_unicode": any(ord(c) > 127 for c in text),
        }
        return result
    except Exception as e:
        raise ValueError(f"Analysis failed: {e}") from e


def get_api_config() -> dict[str, str]:
    """Read API configuration from environment variables."""
    return {
        "api_key": os.environ.get("SKILL_API_KEY", ""),
        "base_url": os.environ.get("SKILL_BASE_URL", "https://api.example.com"),
        "model": os.environ.get("SKILL_MODEL", "gpt-4"),
    }
