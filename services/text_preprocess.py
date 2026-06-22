from __future__ import annotations

from dataclasses import dataclass
import re


NOTEBOOK_BY_CRITERION = {
    "positivity": "train_sentiment_phobert_notebook_complete_visible_outputs.ipynb",
    "toxicity": "train_binary_toxicity_victsd_phobert_notebook_complete_visible_outputs.ipynb",
    "empathy": "train_empathy_pair_cskh_anhnhc_notebook.ipynb",
    "politeness": "train_politeness_xlm_roberta_notebook_complete_visible_outputs.ipynb",
    "resolution": "train_problem_resolution_xlm_roberta_notebook_complete_visible_outputs.ipynb",
}

CUSTOMER_PREFIX = "Khach hang: "
AGENT_PREFIX = "Nhan vien: "

CUSTOMER_ROLE_PATTERN = re.compile(r"^(customer|user|client|khach hang|kh|buyer)\s*:\s*", re.IGNORECASE)
AGENT_ROLE_PATTERN = re.compile(
    r"^(agent|assistant|staff|support|nhan vien|employee|bot|shop)\s*:\s*",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"http\S+|www\S+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\S+@\S+", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b\d{9,11}\b")
SPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class PreprocessedTextInput:
    criterion: str
    original_text: str
    model_input_text: str
    notebook_source: str
    preprocessing_steps: list[str]
    line_count: int


def _canonicalize_role_prefix(line: str) -> str:
    stripped = SPACE_PATTERN.sub(" ", line.strip())
    if not stripped:
        return ""
    if CUSTOMER_ROLE_PATTERN.search(stripped):
        return CUSTOMER_ROLE_PATTERN.sub(CUSTOMER_PREFIX, stripped)
    if AGENT_ROLE_PATTERN.search(stripped):
        return AGENT_ROLE_PATTERN.sub(AGENT_PREFIX, stripped)
    return stripped


def _normalize_training_style_text(text: str) -> str:
    normalized = text.lower()
    normalized = URL_PATTERN.sub(" <url> ", normalized)
    normalized = EMAIL_PATTERN.sub(" <email> ", normalized)
    normalized = PHONE_PATTERN.sub(" <phone> ", normalized)
    normalized = SPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def normalize_transcript_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        normalized_line = _canonicalize_role_prefix(raw_line)
        if normalized_line:
            lines.append(normalized_line)
    return "\n".join(lines).strip()


def _build_notebook_style_conversation_text(text: str) -> str:
    normalized_multiline = normalize_transcript_text(text)
    if not normalized_multiline:
        return ""

    customer_parts: list[str] = []
    agent_parts: list[str] = []
    other_parts: list[str] = []

    for line in normalized_multiline.split("\n"):
        if line.startswith(CUSTOMER_PREFIX):
            customer_parts.append(line[len(CUSTOMER_PREFIX) :].strip())
        elif line.startswith(AGENT_PREFIX):
            agent_parts.append(line[len(AGENT_PREFIX) :].strip())
        else:
            other_parts.append(line.strip())

    merged_parts: list[str] = []
    if customer_parts:
        merged_parts.append(f"{CUSTOMER_PREFIX}{' '.join(customer_parts)}")
    if agent_parts:
        merged_parts.append(f"{AGENT_PREFIX}{' '.join(agent_parts)}")
    if other_parts and not merged_parts:
        merged_parts.append(" ".join(other_parts))
    elif other_parts:
        merged_parts.append(" ".join(other_parts))

    return " ".join(part for part in merged_parts if part).strip()


def preprocess_text_for_criterion(text: str, criterion: str) -> PreprocessedTextInput:
    normalized_multiline = normalize_transcript_text(text)
    notebook_style_text = _build_notebook_style_conversation_text(text)
    model_input = _normalize_training_style_text(notebook_style_text)
    steps = [
        "normalize_line_breaks",
        "canonicalize_speaker_prefixes",
        "merge_transcript_to_notebook_style_conversation",
        "lowercase_text",
        "replace_url_email_phone_tokens",
        "collapse_extra_spaces",
    ]
    return PreprocessedTextInput(
        criterion=criterion,
        original_text=text,
        model_input_text=model_input,
        notebook_source=NOTEBOOK_BY_CRITERION.get(criterion, ""),
        preprocessing_steps=steps,
        line_count=(normalized_multiline.count("\n") + 1) if normalized_multiline else 0,
    )
