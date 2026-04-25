# src/dashboard.py
# CommitFuzz - Main Dashboard Entry Point

import streamlit as st
import os
import tempfile
import sys

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CommitFuzz",
    page_icon="🔍",
    layout="wide"
)

# ============================================================
# GLOBAL CSS — larger text + tab hover effects
# ============================================================

st.markdown("""
<style>
    /* ── Global font size ── */
    html, body, [class*="css"] {
        font-size: 16px !important;
    }
    .stMarkdown p, .stMarkdown li {
        font-size: 16px !important;
    }
    .stCaption {
        font-size: 14px !important;
    }
    label, .stSelectbox label, .stFileUploader label {
        font-size: 15px !important;
        font-weight: 500 !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 6px 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 600;
        padding: 10px 20px;
        border-radius: 8px;
        color: #444;
        background-color: transparent;
        border: none;
        transition: background-color 0.2s ease, color 0.2s ease,
                    transform 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e0e7ff;
        color: #1a1aff;
        transform: translateY(-2px);
        cursor: pointer;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1aff !important;
        color: white !important;
        border-radius: 8px;
    }

    /* ── Sidebar text ── */
    .css-1d391kg, [data-testid="stSidebar"] {
        font-size: 15px !important;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 15px !important;
    }

    /* ── Metric labels ── */
    [data-testid="stMetricLabel"] {
        font-size: 15px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 22px !important;
    }

    /* ── Button ── */
    .stButton > button {
        font-size: 15px !important;
        padding: 10px 24px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR  = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Add src to path so tab imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# TAB IMPORTS
# ============================================================

from tabs.tab_callgraph import render_callgraph_tab
from tabs.tab_cfg       import render_cfg_tab
from tabs.tab_heatmap   import render_heatmap_tab
from tabs.tab_riskscore import render_riskscore_tab
from tabs.tab_insights  import render_insights_tab

# ============================================================
# HELPER
# ============================================================

def save_uploaded_file(uploaded_file, suffix='.cpp'):
    """Save Streamlit uploaded file to a temp location."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
        dir='/tmp'
    )
    tmp.write(uploaded_file.read())
    tmp.close()
    return tmp.name

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🔍 CommitFuzz")
st.sidebar.caption("Commit-Level Risk Scoring & Visualization")
st.sidebar.divider()

# --- Call Graph file upload ---
st.sidebar.subheader("Call Graph")
uploaded_cpp = st.sidebar.file_uploader(
    "C++ Source File",
    type=['cpp', 'c', 'h'],
    help="Upload any C/C++ source file to generate its call graph"
)

st.sidebar.divider()

# --- Commit Analysis file uploads ---
st.sidebar.subheader("Commit Analysis")
uploaded_before = st.sidebar.file_uploader(
    "Before Commit (.cpp)",
    type=['cpp', 'c'],
    key="before"
)
uploaded_after = st.sidebar.file_uploader(
    "After Commit (.cpp)",
    type=['cpp', 'c'],
    key="after"
)

st.sidebar.divider()

# --- Sample files toggle ---
use_sample = st.sidebar.checkbox(
    "Use sample files (data_analyzer V1/V2)",
    value=True
)

# Resolve paths based on uploads or sample
sample_cpp    = os.path.join(PROJECT_ROOT, "data", "data_analyzer_V1.cpp")
sample_before = os.path.join(PROJECT_ROOT, "data", "data_analyzer_V1.cpp")
sample_after  = os.path.join(PROJECT_ROOT, "data", "data_analyzer_V2.cpp")

# Call graph file
if uploaded_cpp is not None:
    cpp_path   = save_uploaded_file(uploaded_cpp)
    cpp_label  = uploaded_cpp.name
elif use_sample and os.path.exists(sample_cpp):
    cpp_path   = sample_cpp
    cpp_label  = "data_analyzer_V1.cpp (sample)"
else:
    cpp_path   = None
    cpp_label  = None

# Before/after files
if uploaded_before is not None:
    before_path  = save_uploaded_file(uploaded_before)
    before_label = uploaded_before.name
elif use_sample and os.path.exists(sample_before):
    before_path  = sample_before
    before_label = "data_analyzer_V1.cpp (sample)"
else:
    before_path  = None
    before_label = None

if uploaded_after is not None:
    after_path  = save_uploaded_file(uploaded_after)
    after_label = uploaded_after.name
elif use_sample and os.path.exists(sample_after):
    after_path  = sample_after
    after_label = "data_analyzer_V2.cpp (sample)"
else:
    after_path  = None
    after_label = None

# ============================================================
# MAIN AREA
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Call Graph",
    "Differential CFG",
    "Risk Heatmap",
    "Risk Score",
    "Actionable Insights"
])

# ============================================================
# RENDER TABS
# ============================================================

with tab1:
    render_callgraph_tab(
        cpp_path=cpp_path,
        file_label=cpp_label,
        project_root=PROJECT_ROOT,
        results_dir=RESULTS_DIR
    )

with tab2:
    render_cfg_tab(
        before_path=before_path,
        after_path=after_path,
        before_label=before_label,
        after_label=after_label,
        results_dir=RESULTS_DIR
    )

with tab3:
    render_heatmap_tab(
        before_path=before_path,
        after_path=after_path,
        before_label=before_label,
        after_label=after_label,
        results_dir=RESULTS_DIR
    )

with tab4:
    render_riskscore_tab(
        before_path=before_path,
        after_path=after_path,
        before_label=before_label,
        after_label=after_label,
        results_dir=RESULTS_DIR
    )

with tab5:
    render_insights_tab(
        before_path=before_path,
        after_path=after_path,
        before_label=before_label,
        after_label=after_label,
        results_dir=RESULTS_DIR
    )