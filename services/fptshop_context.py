from __future__ import annotations

import html
import re
import time
import unicodedata
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _normalize_text(value: str) -> str:
    lowered = value.lower().strip()
    normalized = unicodedata.normalize("NFD", lowered)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


class FPTShopContextService:
    HOMEPAGE_URL = "https://fptshop.com.vn/"
    CACHE_TTL_SECONDS = 900

    CATEGORY_HINTS = {
        "dien_thoai": {
            "label": "Dien thoai",
            "keywords": ["dien thoai", "smartphone", "iphone", "samsung", "xiaomi", "oppo", "vivo", "realme"],
        },
        "laptop": {
            "label": "Laptop",
            "keywords": ["laptop", "macbook", "notebook", "gaming", "van phong"],
        },
        "may_tinh_bang": {
            "label": "May tinh bang",
            "keywords": ["tablet", "ipad", "may tinh bang"],
        },
        "phu_kien": {
            "label": "Phu kien",
            "keywords": ["phu kien", "tai nghe", "sac", "cap", "op lung", "chuot", "ban phim", "loa"],
        },
        "gia_dung": {
            "label": "Gia dung",
            "keywords": ["gia dung", "may giat", "tu lanh", "tivi", "dieu hoa", "may lanh", "noi chien", "robot hut bui"],
        },
        "dong_ho": {
            "label": "Dong ho thong minh",
            "keywords": ["dong ho", "smartwatch", "garmin", "amazfit", "watch"],
        },
        "sim": {
            "label": "SIM FPT",
            "keywords": ["sim", "4g", "5g", "esim"],
        },
    }

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def build_context(self, user_message: str) -> dict[str, Any]:
        homepage = self._get_homepage_snapshot()
        matched_categories = self._detect_categories(user_message)
        ranked_snippets = self._rank_snippets(user_message, homepage.get("snippets", []))
        return {
            "source": self.HOMEPAGE_URL,
            "matched_categories": matched_categories,
            "snippets": ranked_snippets[:8],
            "homepage_status": homepage.get("status", "unavailable"),
            "homepage_title": homepage.get("title", "FPTShop"),
        }

    def _get_homepage_snapshot(self) -> dict[str, Any]:
        cache_key = "homepage"
        cached = self._cache.get(cache_key)
        now = time.time()
        if cached and now - cached[0] < self.CACHE_TTL_SECONDS:
            return cached[1]

        snapshot = self._fetch_homepage()
        self._cache[cache_key] = (now, snapshot)
        return snapshot

    def _fetch_homepage(self) -> dict[str, Any]:
        request = Request(
            self.HOMEPAGE_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; FPTShopAdvisorBot/1.0)",
                "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                html_text = response.read().decode("utf-8", errors="ignore")
        except (TimeoutError, URLError, OSError):
            return {
                "status": "unavailable",
                "title": "FPTShop",
                "snippets": [],
            }

        title_match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_match.group(1).strip()) if title_match else "FPTShop"
        sanitized = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
        sanitized = re.sub(r"(?is)<style.*?>.*?</style>", " ", sanitized)
        sanitized = re.sub(r"(?is)<[^>]+>", "\n", sanitized)
        sanitized = html.unescape(sanitized)
        lines: list[str] = []
        for raw_line in sanitized.splitlines():
            line = " ".join(raw_line.split()).strip()
            if len(line) < 12:
                continue
            lines.append(line)
        unique_lines = list(dict.fromkeys(lines))
        return {
            "status": "ready",
            "title": title,
            "snippets": unique_lines[:300],
        }

    def _detect_categories(self, user_message: str) -> list[str]:
        normalized_message = _normalize_text(user_message)
        matches: list[str] = []
        for item in self.CATEGORY_HINTS.values():
            if any(keyword in normalized_message for keyword in item["keywords"]):
                matches.append(str(item["label"]))
        return matches

    def _rank_snippets(self, user_message: str, snippets: list[str]) -> list[str]:
        if not snippets:
            return []

        keywords = self._extract_keywords(user_message)
        scored: list[tuple[int, str]] = []
        for snippet in snippets:
            normalized_snippet = _normalize_text(snippet)
            score = sum(1 for keyword in keywords if keyword in normalized_snippet)
            if score > 0:
                scored.append((score, snippet))

        if scored:
            scored.sort(key=lambda item: (-item[0], len(item[1])))
            return [snippet for _, snippet in scored]

        featured_keywords = [
            "dien thoai",
            "laptop",
            "may tinh bang",
            "phu kien",
            "sim fpt",
            "tra gop",
            "thu cu",
            "bao hanh",
        ]
        fallback = [snippet for snippet in snippets if any(keyword in _normalize_text(snippet) for keyword in featured_keywords)]
        return fallback[:8] if fallback else snippets[:8]

    def _extract_keywords(self, user_message: str) -> list[str]:
        normalized = _normalize_text(user_message)
        tokens = re.findall(r"[a-z0-9]{3,}", normalized)
        seen: dict[str, None] = {}
        for token in tokens:
            seen.setdefault(token, None)
        phrase_candidates = [
            "dien thoai",
            "may tinh bang",
            "smartwatch",
            "tra gop",
            "thu cu",
            "bao hanh",
            "sim fpt",
            "tai nghe",
            "op lung",
        ]
        for phrase in phrase_candidates:
            if phrase in normalized:
                seen.setdefault(phrase, None)
        return list(seen.keys())
