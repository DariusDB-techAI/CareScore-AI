from __future__ import annotations

from statistics import mean
from typing import Any

from .criterion_apis import call_criterion_api
from .model_registry import MODEL_SPECS


CRITERIA_META = {
    "positivity": {"label": "Positivity", "summary": "Muc do tich cuc hay tieu cuc cua hoi thoai."},
    "empathy": {"label": "Dong cam", "summary": "Muc do ghi nhan cam xuc va boi canh cua khach hang."},
    "politeness": {"label": "Lich su", "summary": "Do ton trong va mem mai trong cach giao tiep."},
    "toxicity": {"label": "Toxicity", "summary": "Dau hieu gay gat, cong kich, do loi hoac doc hai."},
    "resolution": {"label": "Giai quyet van de", "summary": "Muc do ro rang cua huong xu ly va next step."},
}

CRITERION_ACTIONS = {
    "positivity": "Them cau mo dau giu binh tinh va giai toa cang thang som hon.",
    "empathy": "Ghi nhan bat tien cua khach hang truoc khi giai thich hoac huong dan.",
    "politeness": "Dieu chinh cach xung ho va tranh cau phan hoi mang tinh phong thu.",
    "toxicity": "Loai bo cum tu do loi, tranh tu ngu gay gat va uu tien ngon ngu trung tinh.",
    "resolution": "Chot next step, nguoi phu trach va moc thoi gian cu the.",
}
def normalize_result(criterion: str, result: dict[str, Any]) -> dict[str, Any]:
    meta = CRITERIA_META[criterion]
    return {
        "criterion": criterion,
        "label": meta["label"],
        "score": result["score"],
        "confidence": result["confidence"],
        "summary": result["summary"],
        "raw_label": result["raw_label"],
        "probabilities": result["probabilities"],
        "status": result["status"],
        "model_hint": result["model_hint"],
        "api_name": result.get("api_name", ""),
        "owner_hint": result.get("owner_hint", ""),
    }


def evaluate_criterion_text(transcript: str, criterion: str) -> dict[str, Any]:
    if not transcript.strip():
        return {
            "criterion": criterion,
            "label": CRITERIA_META[criterion]["label"],
            "score": 0,
            "confidence": 0.0,
            "summary": "Chua co noi dung hoi thoai de danh gia.",
            "raw_label": "empty",
            "probabilities": {},
            "status": "empty",
            "model_hint": "No transcript available",
            "api_name": "",
            "owner_hint": "",
        }
    return normalize_result(criterion, call_criterion_api(criterion, transcript))


def build_overall_summary(results: dict[str, dict[str, Any]]) -> str:
    ordered = sorted(results.values(), key=lambda item: item["score"])
    return (
        f"Manh nhat o {ordered[-1]['label'].lower()}, "
        f"nhung can uu tien cai thien {ordered[0]['label'].lower()}."
    )


def build_improvement_actions(results: dict[str, dict[str, Any]]) -> list[str]:
    actions = []
    for criterion, result in sorted(results.items(), key=lambda item: item[1]["score"]):
        if result["score"] <= 3:
            actions.append(CRITERION_ACTIONS[criterion])
    return actions[:3] or ["Tiep tuc giu van phong ro rang, lich su va chot next step cu the."]


def build_coaching_note(results: dict[str, dict[str, Any]]) -> str:
    weak_spots = [result["label"] for result in results.values() if result["score"] <= 3]
    if not weak_spots:
        return "Hoi thoai dang on. Co the tap trung vao viec rut gon va tang do cu the cua huong xu ly."
    return f"Can huan luyen them o cac nhom ky nang: {', '.join(label.lower() for label in weak_spots)}."


def evaluate_text(transcript: str, selected_criteria: list[str] | None = None) -> dict[str, Any]:
    criteria = selected_criteria or list(MODEL_SPECS.keys())
    results = {criterion: evaluate_criterion_text(transcript, criterion) for criterion in criteria}
    scored = [item["score"] for item in results.values() if item["score"] > 0]
    overall_score = round(mean(scored), 2) if scored else 0.0
    return {
        "criteria": results,
        "overall_score": overall_score,
        "summary": build_overall_summary(results),
        "coaching_note": build_coaching_note(results),
        "improvement_actions": build_improvement_actions(results),
        "available_criteria": len(scored),
        "requested_criteria": len(criteria),
    }
