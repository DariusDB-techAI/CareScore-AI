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


INPUT_KEY = "politeness_input"
RESULT_KEY = "politeness_result"


def render_page() -> None:
    theme = render_theme("politeness")
    render_navigation(INPUT_KEY)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Tone Craft</div>
            <h1 class="hero-title">Politeness Atelier</h1>
            <p class="hero-copy">
                Nhap noi dung can danh gia politeness. Muc tieu la do ton trong, do mem va cach xung ho.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    left, right = st.columns([1, 1], gap="large")
    with left:
        transcript = render_transcript_editor(
            "Noi dung can danh gia politeness",
            "Vi du:\nKhach hang: Toi can duoc giai thich phi nay.\nNhan vien: Em xin phep kiem tra lai cho anh chi...",
            INPUT_KEY,
        )
        evaluate_clicked = st.button("Evaluate politeness", type="primary", use_container_width=True)
    with right:
        st.markdown(
            """
            <div class="section-card">
                <div class="stat-label">Focus Area</div>
                <div class="soft-copy">
                    Xem cach mo dau, xung ho, tu choi, va cau chot co giu duoc su lich su khong.
                </div>
                <div style="margin-top:12px;">
                    <span class="tiny-chip">xung ho</span>
                    <span class="tiny-chip">ton trong</span>
                    <span class="tiny-chip">phan hoi mem</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if evaluate_clicked:
        st.session_state[RESULT_KEY] = evaluate_text_input("politeness", transcript)

    result = st.session_state.get(RESULT_KEY)
    if result:
        top_left, top_right = st.columns([0.8, 1.2], gap="large")
        with top_left:
            render_result_snapshot(result, theme["accent"])
        with top_right:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Nhan xet tone giao tiep")
            st.write(result.get("summary", ""))
            st.caption(f"Raw label: {result.get('raw_label', '')}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Bang probability")
        render_probability_table(result)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Politeness Atelier", page_icon="🔵", layout="wide")
    render_page()
