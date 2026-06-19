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


INPUT_KEY = "resolution_input"
RESULT_KEY = "resolution_result"


def render_page() -> None:
    theme = render_theme("resolution")
    render_navigation(INPUT_KEY)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Next Step Check</div>
            <h1 class="hero-title">Resolution Control Room</h1>
            <p class="hero-copy">
                Nhap noi dung can danh gia resolution. Page nay tap trung vao next step, deadline va huong xu ly.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    col_a, col_b = st.columns([1.1, 0.9], gap="large")
    with col_a:
        transcript = render_transcript_editor(
            "Noi dung can danh gia resolution",
            "Vi du:\nKhach hang: Don cua toi bi tre.\nNhan vien: Em da tao yeu cau kiem tra va se goi lai truoc 17h hom nay.",
            INPUT_KEY,
        )
        evaluate_clicked = st.button("Evaluate resolution", type="primary", use_container_width=True)
    with col_b:
        st.markdown(
            """
            <div class="section-card">
                <div class="stat-label">Checklist</div>
                <div class="soft-copy">
                    Co next step khong? Co moc thoi gian khong? Co owner hoac bo phan phu trach khong?
                </div>
                <div style="margin-top:12px;">
                    <span class="tiny-chip">next step</span>
                    <span class="tiny-chip">deadline</span>
                    <span class="tiny-chip">owner</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if evaluate_clicked:
        st.session_state[RESULT_KEY] = evaluate_text_input("resolution", transcript)

    result = st.session_state.get(RESULT_KEY)
    if result:
        top, bottom = st.columns([0.9, 1.1], gap="large")
        with top:
            render_result_snapshot(result, theme["accent"])
        with bottom:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Danh gia kha nang chot huong xu ly")
            st.write(result.get("summary", ""))
            st.caption(f"Raw label: {result.get('raw_label', '')}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Probability")
        render_probability_table(result)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Resolution Control Room", page_icon="🟣", layout="wide")
    render_page()
