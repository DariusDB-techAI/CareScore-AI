from __future__ import annotations

from typing import Any

import streamlit as st

from services.evaluation import CRITERIA_META, evaluate_criterion_text


THEMES: dict[str, dict[str, str]] = {
    "positivity": {
        "title": "Sentiment Studio",
        "eyebrow": "Criterion Page",
        "icon": "02",
        "accent": "#ff7a00",
        "accent_soft": "rgba(255, 122, 0, 0.14)",
        "bg_start": "#fff3e8",
        "bg_end": "#ffe1bf",
        "surface": "#fffaf4",
        "ink": "#311300",
        "muted": "#7a4b27",
        "chip": "#ffd5ad",
    },
    "empathy": {
        "title": "Empathy Garden",
        "eyebrow": "Criterion Page",
        "icon": "03",
        "accent": "#0f9d7a",
        "accent_soft": "rgba(15, 157, 122, 0.15)",
        "bg_start": "#e8fff8",
        "bg_end": "#cbf7e6",
        "surface": "#f7fffb",
        "ink": "#07271f",
        "muted": "#42695f",
        "chip": "#c9f1e4",
    },
    "politeness": {
        "title": "Politeness Atelier",
        "eyebrow": "Criterion Page",
        "icon": "04",
        "accent": "#0d5bd7",
        "accent_soft": "rgba(13, 91, 215, 0.14)",
        "bg_start": "#eef4ff",
        "bg_end": "#dce7ff",
        "surface": "#fbfdff",
        "ink": "#0c1933",
        "muted": "#4f638c",
        "chip": "#d6e4ff",
    },
    "toxicity": {
        "title": "Toxicity Watchtower",
        "eyebrow": "Criterion Page",
        "icon": "05",
        "accent": "#c62828",
        "accent_soft": "rgba(198, 40, 40, 0.14)",
        "bg_start": "#fff0ef",
        "bg_end": "#ffd7d3",
        "surface": "#fff8f7",
        "ink": "#341111",
        "muted": "#885151",
        "chip": "#ffd6d2",
    },
    "resolution": {
        "title": "Resolution Control Room",
        "eyebrow": "Criterion Page",
        "icon": "06",
        "accent": "#7057ff",
        "accent_soft": "rgba(112, 87, 255, 0.14)",
        "bg_start": "#f4f0ff",
        "bg_end": "#e1d9ff",
        "surface": "#fbfaff",
        "ink": "#1d173b",
        "muted": "#5f5890",
        "chip": "#ddd7ff",
    },
}


def ensure_state() -> None:
    st.session_state.setdefault("shared_transcript", "")


def render_theme(theme_name: str) -> dict[str, str]:
    theme = THEMES[theme_name]
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"],
        #MainMenu,
        header,
        footer {{
            display: none !important;
        }}
        .stApp {{
            background:
                radial-gradient(circle at top right, {theme["accent_soft"]}, transparent 32%),
                linear-gradient(180deg, {theme["bg_start"]} 0%, {theme["bg_end"]} 100%);
            color: {theme["ink"]};
        }}
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }}
        .hero-card {{
            background: linear-gradient(135deg, {theme["surface"]}, rgba(255,255,255,0.7));
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 28px;
            padding: 28px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
        }}
        .hero-eyebrow {{
            display: inline-block;
            margin-bottom: 8px;
            padding: 6px 10px;
            border-radius: 999px;
            background: {theme["chip"]};
            color: {theme["ink"]};
            font-size: 0.76rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 700;
        }}
        .hero-title {{
            margin: 0;
            font-size: 2.6rem;
            line-height: 1.05;
        }}
        .hero-copy, .soft-copy {{
            color: {theme["muted"]};
            font-size: 1rem;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.74);
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 22px;
            padding: 18px;
            height: 100%;
        }}
        .stat-label {{
            font-size: 0.8rem;
            color: {theme["muted"]};
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 800;
            color: {theme["accent"]};
            margin-top: 6px;
        }}
        .section-card {{
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 24px;
            padding: 22px;
        }}
        .tiny-chip {{
            display: inline-block;
            padding: 5px 10px;
            margin: 0 8px 8px 0;
            border-radius: 999px;
            background: {theme["chip"]};
            color: {theme["ink"]};
            font-size: 0.85rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return theme


def evaluate_text_input(criterion: str, text: str) -> dict[str, Any]:
    return evaluate_criterion_text(str(text).strip(), criterion)


def render_result_snapshot(result: dict[str, Any], accent: str) -> None:
    score = result.get("score", 0)
    confidence = round(float(result.get("confidence", 0.0)) * 100)
    status = result.get("status", "unknown")
    st.markdown(
        f"""
        <div class="section-card">
            <div class="stat-label">Current Score</div>
            <div class="stat-value" style="color:{accent};">{score}/5</div>
            <div class="soft-copy">Status: {status} | Confidence: {confidence}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_probability_table(result: dict[str, Any]) -> None:
    probabilities = result.get("probabilities") or {}
    if not probabilities:
        st.info("Chua co probability detail cho transcript hien tai.")
        return

    rows = [
        {
            "label": label,
            "probability": f"{round(float(score) * 100, 2)}%",
        }
        for label, score in probabilities.items()
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_transcript_editor(title: str, placeholder: str, state_key: str) -> str:
    ensure_state()
    st.session_state.setdefault(state_key, st.session_state.get("shared_transcript", ""))
    st.session_state[state_key] = st.text_area(
        title,
        value=st.session_state.get(state_key, ""),
        height=220,
        placeholder=placeholder,
        key=f"{state_key}_textarea",
    )
    return str(st.session_state[state_key])


def render_navigation(state_key: str) -> None:
    cols = st.columns([1, 5])
    with cols[0]:
        if st.button("Xoa text", use_container_width=True):
            st.session_state[state_key] = ""
            st.rerun()


def criterion_label(criterion: str) -> str:
    return CRITERIA_META[criterion]["label"]
