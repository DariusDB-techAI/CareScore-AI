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


INPUT_KEY = "toxicity_input"
RESULT_KEY = "toxicity_result"


def render_page() -> None:
    theme = render_theme("toxicity")
    render_navigation(INPUT_KEY)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Risk Scan</div>
            <h1 class="hero-title">Toxicity Watchtower</h1>
            <p class="hero-copy">
                Nhap noi dung can danh gia toxicity. Trang nay dung tong mau canh bao va chi route vao model toxicity.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    watch_left, watch_right = st.columns([1.15, 0.85], gap="large")
    with watch_left:
        transcript = render_transcript_editor(
            "Noi dung can danh gia toxicity",
            "Vi du:\nKhach hang: Toi rat buc xuc.\nNhan vien: Anh dang noi chuyen kieu gi day?",
            INPUT_KEY,
        )
        evaluate_clicked = st.button("Evaluate toxicity", type="primary", use_container_width=True)
    with watch_right:
        st.markdown(
            """
            <div class="section-card">
                <div class="stat-label">Note</div>
                <div class="soft-copy">
                    Criterion nay la truong hop dac biet: model phat hien toxic la xau, nen can doc score cung voi summary.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if evaluate_clicked:
        st.session_state[RESULT_KEY] = evaluate_text_input("toxicity", transcript)

    result = st.session_state.get(RESULT_KEY)
    if result:
        one, two, three = st.columns(3, gap="large")
        with one:
            render_result_snapshot(result, theme["accent"])
        with two:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Canh bao")
            st.write(result.get("summary", ""))
            st.caption(f"Raw label: {result.get('raw_label', '')}")
            st.markdown("</div>", unsafe_allow_html=True)
        with three:
            st.markdown(
                """
                <div class="section-card">
                    <div class="stat-label">Reading Guide</div>
                    <div class="soft-copy">
                        Neu summary noi co ngon ngu cong kich hoac do loi, can sua script ngay ca khi confidence chua qua cao.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Probability")
        render_probability_table(result)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Toxicity Watchtower", page_icon="🔴", layout="wide")
    render_page()
