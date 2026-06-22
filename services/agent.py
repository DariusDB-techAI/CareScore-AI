from __future__ import annotations

import re
from typing import Any

AGENT_INTENT_KEYWORDS = [
    "danh gia",
    "review",
    "phan tich",
    "analyze",
    "hoi thoai",
    "conversation",
    "toxic",
    "positivity",
    "sentiment",
    "dong cam",
    "lich su",
]


def is_agent_request(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in AGENT_INTENT_KEYWORDS)


def extract_transcript(message: str) -> str:
    patterns = [
        r"(?:hoi thoai|conversation|transcript)\s*[:\-]\s*(.+)",
        r"(?:noi dung|chat log)\s*[:\-]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return message.strip()


def build_agent_context(result: dict[str, Any]) -> str:
    criteria_lines = []
    for item in result["criteria"].values():
        criteria_lines.append(
            f"- {item['label']}: score={item['score']}/5, confidence={item['confidence']}, "
            f"status={item['status']}, api={item.get('api_name', '')}, summary={item['summary']}"
        )
    actions = "\n".join(f"- {action}" for action in result["improvement_actions"])
    return (
        "Agent evaluation result:\n"
        f"overall_score={result['overall_score']}/5\n"
        f"summary={result['summary']}\n"
        f"coaching_note={result['coaching_note']}\n"
        "criteria:\n"
        f"{chr(10).join(criteria_lines)}\n"
        "improvement_actions:\n"
        f"{actions}"
    )


def build_fallback_reply(result: dict[str, Any]) -> str:
    routed = []
    orchestrator = result.get("orchestrator") or {}
    if isinstance(orchestrator, dict):
        routed = orchestrator.get("selected_criteria") or []

    parts = [
        f"Gemini tong hop tu ket qua danh gia cho thay diem tong quan cua hoi thoai la {result['overall_score']}/5.",
        f"Nhan dinh tong quan: {result['summary']}",
        f"Coaching note: {result['coaching_note']}",
    ]
    if routed:
        parts.append(f"Cac tieu chi da duoc agent orchestrator route de danh gia gom: {', '.join(str(item) for item in routed)}.")

    criterion_parts = []
    for item in result["criteria"].values():
        criterion_parts.append(
            f"{item['label']} dat {item['score']}/5, trang thai {item['status']}, nhan xet: {item['summary']}"
        )
    if criterion_parts:
        parts.append("Ket qua theo tung tieu chi: " + " ".join(criterion_parts))

    if result["improvement_actions"]:
        parts.append(
            "De xuat cai thien uu tien: "
            + " ".join(str(action).strip().rstrip(".") + "." for action in result["improvement_actions"] if str(action).strip())
        )

    return " ".join(part.strip() for part in parts if str(part).strip())
