from __future__ import annotations

import importlib.util
from pathlib import Path

import streamlit as st

from services.evaluation import CRITERIA_META


BASE_DIR = Path(__file__).resolve().parent
PAGE_FILES = {
    "positivity": BASE_DIR / "pages" / "01_sentiment_page.py",
    "empathy": BASE_DIR / "pages" / "02_empathy_page.py",
    "politeness": BASE_DIR / "pages" / "03_politeness_page.py",
    "toxicity": BASE_DIR / "pages" / "04_toxicity_page.py",
    "resolution": BASE_DIR / "pages" / "05_resolution_page.py",
}


def load_page_renderer(criterion: str):
    page_path = PAGE_FILES[criterion]
    module_name = f"criterion_page_{criterion}"
    spec = importlib.util.spec_from_file_location(module_name, page_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Khong the nap page file: {page_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    render_page = getattr(module, "render_page", None)
    if render_page is None:
        raise RuntimeError(f"Page file {page_path.name} chua khai bao render_page().")
    return render_page


st.set_page_config(page_title="Criteria Workspace", page_icon="🎛️", layout="wide")

selected_criterion = str(st.query_params.get("criterion", "")).strip().lower()
if selected_criterion in CRITERIA_META:
    load_page_renderer(selected_criterion)()
    st.stop()

st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="collapsedControl"],
    #MainMenu,
    header,
    footer {
        display: none !important;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(255, 120, 0, 0.12), transparent 28%),
            radial-gradient(circle at bottom right, rgba(13, 91, 215, 0.10), transparent 30%),
            linear-gradient(180deg, #fff9f3 0%, #eef4ff 100%);
    }
    .block-container {
        max-width: 1220px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hub-hero {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 30px;
        padding: 30px;
        box-shadow: 0 20px 70px rgba(0,0,0,0.07);
    }
    .hub-kicker {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #111827;
        color: white;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }
    .hub-title {
        margin: 12px 0 8px 0;
        font-size: 3rem;
        line-height: 1;
        color: #171717;
    }
    .hub-copy {
        color: #4b5563;
        max-width: 760px;
        font-size: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hub-hero">
        <span class="hub-kicker">Streamlit Criterion Workspace</span>
        <h1 class="hub-title">Khong co criterion duoc chon</h1>
        <p class="hub-copy">
            App Streamlit nay duoc nhung ben trong Flask criterion wrapper.
            Hay mo no qua route /criterion/&lt;criterion&gt; tu page tong.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
