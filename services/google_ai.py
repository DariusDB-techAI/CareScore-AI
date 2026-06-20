from __future__ import annotations

import os
from pathlib import Path


PLACEHOLDER_API_KEYS = {
    "",
    "your_api_key_here",
    "paste_your_key_here",
    "changeme",
}

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip("'").strip('"')

        # Prefer explicit local `.env` values for Gemini settings so a stale
        # shell-level variable does not mask the key the project is configured with.
        if normalized_key in {"GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"}:
            os.environ[normalized_key] = normalized_value
        else:
            os.environ.setdefault(normalized_key, normalized_value)


_load_local_env()


def get_gemini_api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


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
