from __future__ import annotations

import streamlit as st

from streamlit_shared import (
    criterion_label,
    evaluate_text_input,
    render_navigation,
    render_probability_table,
    render_result_snapshot,
    render_theme,
    render_transcript_editor,
)


INPUT_KEY = "positivity_input"
RESULT_KEY = "positivity_result"


def render_page() -> None:
    theme = render_theme("positivity")
    render_navigation(INPUT_KEY)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Warm Signal</div>
            <h1 class="hero-title">Sentiment Studio</h1>
            <p class="hero-copy">
                Nhap 1 tu, 1 cau, hoac 1 doan hoi thoai. Khi bam Evaluate, page nay chi goi model sentiment.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    left, right = st.columns([1.3, 0.9], gap="large")
    with left:
        transcript = render_transcript_editor(
            "Noi dung can danh gia sentiment",
            "Vi du:\nKhach hang: Toi that vong ve don hang nay.\nNhan vien: Em xin loi vi trai nghiem nay...",
            INPUT_KEY,
        )
        evaluate_clicked = st.button("Evaluate sentiment", type="primary", use_container_width=True)

    with right:
        st.markdown(
            """
            <div class="section-card">
                <div class="stat-label">Input Type</div>
                <div class="soft-copy">
                    Ho tro nhap tu don, cau ngan, hoac transcript hoi thoai day du.
                </div>
                <div style="margin-top:12px;">
                    <span class="tiny-chip">positive</span>
                    <span class="tiny-chip">neutral</span>
                    <span class="tiny-chip">negative</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if evaluate_clicked:
        st.session_state[RESULT_KEY] = evaluate_text_input("positivity", transcript)

    result = st.session_state.get(RESULT_KEY)
    if result:
        a, b, c = st.columns(3)
        with a:
            render_result_snapshot(result, theme["accent"])
        with b:
            st.markdown(
                f"""
                <div class="section-card">
                    <div class="stat-label">Criterion</div>
                    <div class="stat-value" style="font-size:1.45rem;color:{theme["ink"]};">{criterion_label("positivity")}</div>
                    <div class="soft-copy">Raw label: {result.get("raw_label", "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c:
            st.markdown(
                f"""
                <div class="section-card">
                    <div class="stat-label">Input Size</div>
                    <div class="stat-value" style="font-size:1.45rem;color:{theme["ink"]};">{len(transcript.splitlines())}</div>
                    <div class="soft-copy">So dong duoc gui vao model.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        d, e = st.columns([1.2, 1], gap="large")
        with d:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Nhan xet nhanh")
            st.write(result.get("summary", ""))
            st.markdown("</div>", unsafe_allow_html=True)
        with e:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Probability")
            render_probability_table(result)
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Sentiment Studio", page_icon="🟠", layout="wide")
    render_page()
