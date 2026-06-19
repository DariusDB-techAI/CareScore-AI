from __future__ import annotations

import re
from typing import Any

from .criterion_apis import CRITERION_APIS
from .evaluation import CRITERIA_META, evaluate_text


CRITERION_KEYWORDS = {
    "positivity": ["positive", "positivity", "cam xuc", "negative", "tich cuc", "tieu cuc", "sentiment"],
    "empathy": ["empathy", "dong cam", "thau hieu", "ghi nhan cam xuc"],
    "politeness": ["polite", "politeness", "lich su", "ton trong", "xung ho"],
    "toxicity": ["toxic", "toxicity", "doc hai", "gay gat", "cong kich", "do loi"],
    "resolution": ["resolution", "giai quyet", "xu ly", "next step", "huong xu ly"],
}

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


def detect_criteria(message: str) -> list[str]:
    lowered = message.lower()
    selected = [
        criterion
        for criterion, keywords in CRITERION_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return selected or list(CRITERIA_META.keys())


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


def run_quality_agent(message: str) -> dict[str, Any]:
    selected_criteria = detect_criteria(message)
    transcript = extract_transcript(message)
    evaluation = evaluate_text(transcript, selected_criteria)
    return {
        "selected_criteria": selected_criteria,
        "transcript": transcript,
        "evaluation": evaluation,
        "agent_context": build_agent_context(evaluation),
        "fallback_reply": build_fallback_reply(evaluation),
        "routing": [
            {
                "criterion": criterion,
                "api_name": CRITERION_APIS[criterion].display_name,
                "owner_hint": CRITERION_APIS[criterion].owner_hint,
            }
            for criterion in selected_criteria
        ],
    }
