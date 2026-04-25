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
# Future imports (uncomment as you build each tab):
# from tabs.tab_cfg       import render_cfg_tab
# from tabs.tab_heatmap   import render_heatmap_tab
# from tabs.tab_riskscore import render_riskscore_tab
# from tabs.tab_insights  import render_insights_tab

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

st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/LSU_Tigers_logo.svg/200px-LSU_Tigers_logo.svg.png",
    width=80
)
st.sidebar.title("CommitFuzz")
st.sidebar.caption("Commit-Level Risk Scoring & Visualization")
st.sidebar.divider()

# --- Call Graph file upload ---
st.sidebar.subheader("📌 Call Graph")
uploaded_cpp = st.sidebar.file_uploader(
    "C++ Source File",
    type=['cpp', 'c', 'h'],
    help="Upload any C/C++ source file to generate its call graph"
)

st.sidebar.divider()

# --- Commit Analysis file uploads ---
st.sidebar.subheader("📊 Commit Analysis")
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

st.title("🔍 CommitFuzz: Commit-Level Risk Scoring")
st.caption("A static analysis tool for predicting bug introduction from code changes")
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 Call Graph",
    "🌊 Differential CFG",
    "🌡️ Risk Heatmap",
    "📊 Risk Score",
    "💡 Actionable Insights"
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
    st.header("🌊 Differential CFG")
    st.info("Coming soon — will show before/after control flow graphs side by side.")

with tab3:
    st.header("🌡️ Risk Heatmap")
    st.info("Coming soon — will show line-by-line risk coloring of code changes.")

with tab4:
    st.header("📊 Risk Score")
    st.info("Coming soon — will show cyclomatic complexity delta, flow alteration score, and change ratio.")

with tab5:
    st.header("💡 Actionable Insights")
    st.info("Coming soon — will show review checklist and high-risk lines to inspect.")