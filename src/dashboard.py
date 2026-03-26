import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import altair as alt

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

DATA_FILE = BASE_DIR / "data" / "singleFuncDataset.jsonl"
RESULTS_FILE = BASE_DIR / "results" / "risk_scores.csv"

# ---------- Page Config ----------
st.set_page_config(
    page_title="CommitRiskViz",
    page_icon="🧠",
    layout="wide"
)

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "singleFuncDataset.jsonl"
RESULTS_FILE = BASE_DIR / "results" / "risk_scores.csv"

# ---------- Helpers ----------
@st.cache_data
def load_results():
    if RESULTS_FILE.exists():
        return pd.read_csv(RESULTS_FILE)
    return pd.DataFrame()

@st.cache_data
def load_raw_data():
    rows = []
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
    return rows

def run_pipeline():
    from risk_engine import main
    main()
    
def risk_color(level: str):
    level = str(level).upper()
    if level == "HIGH":
        return "🔴 HIGH"
    elif level == "MEDIUM":
        return "🟠 MEDIUM"
    return "🟢 LOW"

# ---------- Header ----------
st.title("CommitRiskViz")
st.caption("Visual tool for predicting bug risk from code changes")

col1, col2 = st.columns([1, 4])
with col1:
   if st.button("Run Risk Analysis", use_container_width=True):
    try:
        run_pipeline()
        st.cache_data.clear()
        st.success("Risk analysis completed. Results file updated.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to run pipeline: {e}")

# ---------- Load Data ----------
df = load_results()
raw_data = load_raw_data()

if df.empty:
    st.warning("No results found yet. Click 'Run Risk Analysis' to generate results.")
    st.stop()

# ---------- KPIs ----------
total_commits = len(df)
high_count = (df["risk_level"] == "HIGH").sum()
medium_count = (df["risk_level"] == "MEDIUM").sum()
low_count = (df["risk_level"] == "LOW").sum()
avg_risk = df["risk_score"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Commits", total_commits)
k2.metric("High Risk", int(high_count))
k3.metric("Medium Risk", int(medium_count))
k4.metric("Average Risk", f"{avg_risk:.3f}")

st.divider()

# ---------- Sidebar Filters ----------
st.sidebar.header("Filters")
selected_levels = st.sidebar.multiselect(
    "Risk Level",
    options=["LOW", "MEDIUM", "HIGH"],
    default=["LOW", "MEDIUM", "HIGH"]
)

min_score, max_score = float(df["risk_score"].min()), float(df["risk_score"].max())
score_range = st.sidebar.slider(
    "Risk Score Range",
    min_value=min_score,
    max_value=max_score,
    value=(min_score, max_score)
)

search_text = st.sidebar.text_input("Search Commit Title")

filtered_df = df[
    (df["risk_level"].isin(selected_levels)) &
    (df["risk_score"] >= score_range[0]) &
    (df["risk_score"] <= score_range[1])
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["commit_title"].str.contains(search_text, case=False, na=False)
    ]

# ---------- Main Tabs ----------
tab1, tab2, tab3 = st.tabs(["Commit Table", "Charts", "Commit Details"])

with tab1:
    st.subheader("Commit Risk Table")

    display_df = filtered_df.copy()
    display_df["risk_label"] = display_df["risk_level"].apply(risk_color)

    st.dataframe(
        display_df[[
            "commit_title",
            "risk_label",
            "risk_score",
            "cc_delta",
            "flow_score",
            "change_ratio"
        ]].sort_values("risk_score", ascending=False),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Risk Visualizations")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Top 10 Riskiest Commits**")
        top10 = filtered_df.sort_values("risk_score", ascending=False).head(10)
        st.bar_chart(top10.set_index("commit_title")["risk_score"])

    with c2:
        st.markdown("**Risk Scores by Commit**")
        st.bar_chart(filtered_df.set_index("commit_title")["risk_score"])

    st.markdown("### Normalized Commit Metric Heatmap")

    heatmap_df = filtered_df[[
        "commit_title",
        "cc_delta",
        "flow_score",
        "change_ratio",
        "risk_score"
    ]].copy()

    heatmap_df = heatmap_df.sort_values("risk_score", ascending=False).head(20)

    metric_cols = ["cc_delta", "flow_score", "change_ratio", "risk_score"]

    for col in metric_cols:
        min_val = heatmap_df[col].min()
        max_val = heatmap_df[col].max()
        if max_val > min_val:
            heatmap_df[col] = (heatmap_df[col] - min_val) / (max_val - min_val)
        else:
            heatmap_df[col] = 0.0

    heatmap_long = heatmap_df.melt(
        id_vars="commit_title",
        var_name="metric",
        value_name="value"
    )

    heatmap = alt.Chart(heatmap_long).mark_rect().encode(
        x=alt.X("metric:N", title="Metric"),
        y=alt.Y("commit_title:N", sort="-x", title="Commit"),
        color=alt.Color("value:Q", title="Normalized Value"),
        tooltip=[
            alt.Tooltip("commit_title:N", title="Commit"),
            alt.Tooltip("metric:N", title="Metric"),
            alt.Tooltip("value:Q", title="Normalized Value", format=".3f")
        ]
    ).properties(
        width=700,
        height=500
    )

    st.altair_chart(heatmap, use_container_width=True)

with tab3:
    st.subheader("Commit Details")

    options = filtered_df["commit_title"].tolist()
    if not options:
        st.info("No commits match the current filters.")
    else:
        selected_commit = st.selectbox("Choose a commit", options)

        row = filtered_df[filtered_df["commit_title"] == selected_commit].iloc[0]

        left, right = st.columns([1, 1])

        with left:
            st.markdown(f"### {row['commit_title']}")
            st.write(f"**Risk Level:** {risk_color(row['risk_level'])}")
            st.write(f"**Risk Score:** {row['risk_score']:.3f}")
            st.write(f"**Cyclomatic Complexity Delta:** {row['cc_delta']}")
            st.write(f"**Control Flow Alteration:** {row['flow_score']}")
            st.write(f"**Change Size Ratio:** {row['change_ratio']:.3f}")

        with right:
            st.markdown("### Interpretation")
            if row["risk_level"] == "HIGH":
                st.error(
                    "This commit shows high bug risk. It likely changes control flow "
                    "significantly, increases complexity, or modifies a large portion of code."
                )
            elif row["risk_level"] == "MEDIUM":
                st.warning(
                    "This commit shows moderate bug risk. It may deserve targeted testing "
                    "around the modified logic."
                )
            else:
                st.success(
                    "This commit shows relatively low bug risk compared with the rest of the dataset."
                )