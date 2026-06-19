from __future__ import annotations

from statistics import mean
from typing import Any

from .criterion_apis import call_criterion_api
from .model_registry import MODEL_SPECS
from .text_preprocess import preprocess_text_for_criterion


CRITERIA_META = {
    "positivity": {"label": "Sentiment", "summary": "Muc do tich cuc hay tieu cuc cua hoi thoai."},
    "empathy": {"label": "Empathy", "summary": "Muc do ghi nhan cam xuc va boi canh cua khach hang."},
    "politeness": {"label": "Politeness", "summary": "Do ton trong va mem mai trong cach giao tiep."},
    "toxicity": {"label": "Toxicity", "summary": "Dau hieu gay gat, cong kich, do loi hoac doc hai."},
    "resolution": {"label": "Resolution", "summary": "Muc do ro rang cua huong xu ly va next step."},
}

CRITERION_ACTIONS = {
    "positivity": "Them cau mo dau giu binh tinh va giai toa cang thang som hon.",
    "empathy": "Ghi nhan bat tien cua khach hang truoc khi giai thich hoac huong dan.",
    "politeness": "Dieu chinh cach xung ho va tranh cau phan hoi mang tinh phong thu.",
    "toxicity": "Loai bo cum tu do loi, tranh tu ngu gay gat va uu tien ngon ngu trung tinh.",
    "resolution": "Chot next step, nguoi phu trach va moc thoi gian cu the.",
}


NON_ACTIONABLE_STATUSES = {"empty", "error", "missing_model"}


def is_actionable_result(result: dict[str, Any]) -> bool:
    return result.get("status") not in NON_ACTIONABLE_STATUSES and float(result.get("score", 0)) > 0


def get_actionable_results(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [result for result in results.values() if is_actionable_result(result)]


def get_quality_score(result: dict[str, Any]) -> float:
    criterion = str(result.get("criterion") or "")
    score = float(result.get("score", 0))
    if not criterion or score <= 0:
        return 0.0
    spec = MODEL_SPECS.get(criterion)
    if spec is None:
        return score
    return score if spec.higher_is_better else 6 - score


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
    preprocessed = preprocess_text_for_criterion(transcript, criterion)
    if not preprocessed.model_input_text.strip():
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
            "preprocess": {
                "notebook_source": preprocessed.notebook_source,
                "preprocessing_steps": preprocessed.preprocessing_steps,
                "line_count": preprocessed.line_count,
                "input_preview": preprocessed.model_input_text[:240],
            },
        }
    result = normalize_result(criterion, call_criterion_api(criterion, preprocessed.model_input_text))
    result["preprocess"] = {
        "notebook_source": preprocessed.notebook_source,
        "preprocessing_steps": preprocessed.preprocessing_steps,
        "line_count": preprocessed.line_count,
        "input_preview": preprocessed.model_input_text[:240],
    }
    return result


def build_overall_summary(results: dict[str, dict[str, Any]]) -> str:
    actionable = sorted(get_actionable_results(results), key=get_quality_score)
    if not actionable:
        return "Chua du du lieu hop le de tong hop ket qua danh gia."

    if len(actionable) == 1:
        item = actionable[0]
        if get_quality_score(item) >= 4:
            return f"Ket qua {item['label'].lower()} dang tot. {item['summary']}"
        return f"Can uu tien cai thien {item['label'].lower()}. {item['summary']}"

    ordered = actionable
    return (
        f"Manh nhat o {ordered[-1]['label'].lower()}, "
        f"nhung can uu tien cai thien {ordered[0]['label'].lower()}."
    )


def build_improvement_actions(results: dict[str, dict[str, Any]]) -> list[str]:
    actions = []
    for criterion, result in sorted(results.items(), key=lambda item: get_quality_score(item[1])):
        if not is_actionable_result(result):
            continue
        if get_quality_score(result) <= 3:
            actions.append(CRITERION_ACTIONS[criterion])
    return actions[:3] or ["Tiep tuc giu van phong ro rang, lich su va chot next step cu the."]


def build_coaching_note(results: dict[str, dict[str, Any]]) -> str:
    weak_spots = [
        result["label"]
        for result in results.values()
        if is_actionable_result(result) and get_quality_score(result) <= 3
    ]
    if not weak_spots:
        if not get_actionable_results(results):
            return "Khong co ket qua model hop le de dua ra coaching note."
        return "Hoi thoai dang on. Co the tap trung vao viec rut gon va tang do cu the cua huong xu ly."
    return f"Can huan luyen them o cac nhom ky nang: {', '.join(label.lower() for label in weak_spots)}."


def evaluate_text(transcript: str, selected_criteria: list[str] | None = None) -> dict[str, Any]:
    criteria = selected_criteria or list(MODEL_SPECS.keys())
    results = {criterion: evaluate_criterion_text(transcript, criterion) for criterion in criteria}
    scored = [get_quality_score(item) for item in results.values() if is_actionable_result(item)]
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
