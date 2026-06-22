from __future__ import annotations

import json
from dataclasses import dataclass
from statistics import mean
from typing import Any

from google import genai

from .evaluation import (
    CRITERIA_META,
    build_coaching_note,
    build_improvement_actions,
    build_overall_summary,
    evaluate_criterion_text,
    get_quality_score,
    is_actionable_result,
)
from .evaluator_orchestration_prompt import build_evaluator_orchestration_prompt
from .google_ai import (
    describe_gemini_request_error,
    get_gemini_model,
    is_gemini_configured,
    validate_gemini_api_key,
)


VALID_CRITERIA = list(CRITERIA_META.keys())
CRITERION_ALIASES = {
    "positivity": ["positivity", "sentiment", "cam xuc", "tich cuc", "tieu cuc", "positive", "negative"],
    "toxicity": ["toxicity", "toxic", "doc hai", "gay gat", "cong kich", "do loi"],
    "empathy": ["empathy", "dong cam", "thau hieu"],
    "politeness": ["politeness", "polite", "lich su", "ton trong"],
    "resolution": ["resolution", "resolve", "giai quyet", "next step", "huong xu ly"],
}


@dataclass(frozen=True)
class EvaluatorPlan:
    route: str
    selected_criteria: list[str]
    reason: str
    objective: str
    source: str
    raw_response: str | None = None


def _gemini_is_configured() -> bool:
    return is_gemini_configured()


def _normalize_criteria(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        criterion = str(value or "").strip().lower()
        if criterion in CRITERIA_META and criterion not in result:
            result.append(criterion)
    return result


def _heuristic_plan(user_prompt: str, selected_criteria: list[str]) -> EvaluatorPlan:
    normalized_selected = _normalize_criteria(selected_criteria)
    if normalized_selected:
        return EvaluatorPlan(
            route="evaluate_current_session",
            selected_criteria=normalized_selected,
            reason="Dung tieu chi duoc UI chon san.",
            objective="Tien xu ly transcript session va goi dung local models cho cac tieu chi da chon.",
            source="ui_selection",
        )

    lowered = user_prompt.lower()
    detected: list[str] = []
    for criterion, aliases in CRITERION_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            detected.append(criterion)

    selected = detected or VALID_CRITERIA
    reason = "Suy ra tieu chi tu evaluator prompt." if detected else "Khong du tin hieu cu the nen danh gia tat ca tieu chi."
    return EvaluatorPlan(
        route="evaluate_current_session",
        selected_criteria=selected,
        reason=reason,
        objective="Tien xu ly transcript session va goi dung local models theo tieu chi duoc route.",
        source="heuristic",
    )


def _parse_plan_payload(raw_response: str) -> dict[str, Any]:
    candidate = raw_response.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Evaluator planner did not return JSON.")
    return json.loads(candidate[start : end + 1])


def create_evaluator_plan(
    user_prompt: str,
    transcript: str,
    selected_criteria: list[str] | None = None,
) -> EvaluatorPlan:
    selected = _normalize_criteria(selected_criteria or [])
    if not user_prompt.strip() and selected:
        return _heuristic_plan("", selected)

    if not _gemini_is_configured():
        return _heuristic_plan(user_prompt, selected)

    model = get_gemini_model()
    client = genai.Client(api_key=validate_gemini_api_key())
    prompt = build_evaluator_orchestration_prompt(user_prompt, selected, transcript[:1200])
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        raise RuntimeError(describe_gemini_request_error(exc)) from exc
    text = (response.text or "").strip()
    if not text:
        return _heuristic_plan(user_prompt, selected)

    try:
        payload = _parse_plan_payload(text)
        routed = _normalize_criteria(payload.get("selected_criteria") or [])
        return EvaluatorPlan(
            route=str(payload.get("route") or "evaluate_current_session"),
            selected_criteria=routed or VALID_CRITERIA,
            reason=str(payload.get("reason") or "LLM planner selected criteria."),
            objective=str(payload.get("objective") or "Preprocess transcript and run routed models."),
            source="llm_orchestration",
            raw_response=text,
        )
    except Exception:
        return _heuristic_plan(user_prompt, selected)


def run_orchestrated_evaluation(
    *,
    transcript: str,
    user_prompt: str,
    selected_criteria: list[str] | None = None,
) -> dict[str, Any]:
    plan = create_evaluator_plan(user_prompt, transcript, selected_criteria)
    results: dict[str, dict[str, Any]] = {}
    preprocess_log: dict[str, dict[str, Any]] = {}

    for criterion in plan.selected_criteria:
        result = evaluate_criterion_text(transcript, criterion)
        results[criterion] = result
        preprocess_log[criterion] = result.get("preprocess", {})

    scored = [get_quality_score(item) for item in results.values() if is_actionable_result(item)]
    overall_score = round(mean(scored), 2) if scored else 0.0
    return {
        "criteria": results,
        "overall_score": overall_score,
        "summary": build_overall_summary(results),
        "coaching_note": build_coaching_note(results),
        "improvement_actions": build_improvement_actions(results),
        "available_criteria": len(scored),
        "requested_criteria": len(plan.selected_criteria),
        "orchestrator": {
            "route": plan.route,
            "selected_criteria": plan.selected_criteria,
            "reason": plan.reason,
            "objective": plan.objective,
            "source": plan.source,
            "raw_response": plan.raw_response,
        },
        "preprocess_log": preprocess_log,
    }
