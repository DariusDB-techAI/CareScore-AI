from __future__ import annotations

from .apis.base import CriterionApiSpec
from .apis.empathy import evaluate_empathy
from .apis.politeness import evaluate_politeness
from .apis.positivity import evaluate_positivity
from .apis.resolution import evaluate_resolution
from .apis.toxicity import evaluate_toxicity


CRITERION_APIS: dict[str, CriterionApiSpec] = {
    "positivity": CriterionApiSpec(
        criterion="positivity",
        display_name="Positivity API",
        owner_hint="team-positivity",
        evaluator=evaluate_positivity,
    ),
    "empathy": CriterionApiSpec(
        criterion="empathy",
        display_name="Empathy API",
        owner_hint="team-empathy",
        evaluator=evaluate_empathy,
    ),
    "politeness": CriterionApiSpec(
        criterion="politeness",
        display_name="Politeness API",
        owner_hint="team-politeness",
        evaluator=evaluate_politeness,
    ),
    "toxicity": CriterionApiSpec(
        criterion="toxicity",
        display_name="Toxicity API",
        owner_hint="team-toxicity",
        evaluator=evaluate_toxicity,
    ),
    "resolution": CriterionApiSpec(
        criterion="resolution",
        display_name="Resolution API",
        owner_hint="team-resolution",
        evaluator=evaluate_resolution,
    ),
}


def call_criterion_api(criterion: str, transcript: str) -> dict[str, object]:
    api_spec = CRITERION_APIS[criterion]
    result = api_spec.evaluator(transcript)
    result["api_name"] = api_spec.display_name
    result["owner_hint"] = api_spec.owner_hint
    return result
