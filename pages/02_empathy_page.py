from __future__ import annotations

import streamlit as st

from streamlit_shared import (
    evaluate_text_input,
    render_navigation,
    render_probability_table,
    render_result_snapshot,
    render_theme,
    render_transcript_editor,
)


INPUT_KEY = "empathy_input"
RESULT_KEY = "empathy_result"


def render_page() -> None:
    theme = render_theme("empathy")
    render_navigation(INPUT_KEY)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Listening Lens</div>
            <h1 class="hero-title">Empathy Garden</h1>
            <p class="hero-copy">
                Nhap noi dung can danh gia empathy. Page nay chi route vao model empathy.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    intro, editor = st.columns([0.8, 1.2], gap="large")
    with intro:
        st.markdown(
            """
            <div class="section-card">
                <div class="stat-label">Checklist</div>
                <div class="soft-copy">
                    Co ghi nhan cam xuc khong? Co nhac lai boi canh khong? Co chuyen qua huong ho tro sau khi dong cam khong?
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with editor:
        transcript = render_transcript_editor(
            "Noi dung can danh gia empathy",
            "Vi du:\nKhach hang: Toi rat met vi phai doi qua lau.\nNhan vien: Em hieu su bat tien nay va se kiem tra ngay...",
            INPUT_KEY,
        )
        evaluate_clicked = st.button("Evaluate empathy", type="primary", use_container_width=True)

    if evaluate_clicked:
        st.session_state[RESULT_KEY] = evaluate_text_input("empathy", transcript)

    result = st.session_state.get(RESULT_KEY)
    if result:
        left, center, right = st.columns([0.9, 1.2, 0.9], gap="large")
        with left:
            render_result_snapshot(result, theme["accent"])
        with center:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Tom tat dien giai")
            st.write(result.get("summary", ""))
            st.caption(f"Raw label: {result.get('raw_label', '')}")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Xac suat nhan dien")
            render_probability_table(result)
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Empathy Garden", page_icon="🟢", layout="wide")
    render_page()
