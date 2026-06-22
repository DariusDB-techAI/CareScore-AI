from __future__ import annotations

import os
from dotenv import load_dotenv

from .paths import PROJECT_ROOT


PLACEHOLDER_API_KEYS = {
    "",
    "your_api_key_here",
    "paste_your_key_here",
    "changeme",
}

BASE_DIR = PROJECT_ROOT
load_dotenv(BASE_DIR / ".env")


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_gemini_model() -> str:
    return (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()


def is_gemini_configured() -> bool:
    return get_gemini_api_key() not in PLACEHOLDER_API_KEYS


def describe_gemini_api_key_issue(api_key: str) -> str:
    if api_key in PLACEHOLDER_API_KEYS:
        return "Chua cau hinh GEMINI_API_KEY. Mo file .env va dan Gemini API key that tu Google AI Studio."
    return ""


def validate_gemini_api_key() -> str:
    api_key = get_gemini_api_key()
    issue = describe_gemini_api_key_issue(api_key)
    if issue:
        raise RuntimeError(issue)

    return api_key


def describe_gemini_request_error(exc: Exception) -> str:
    return str(exc)
