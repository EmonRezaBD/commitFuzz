import json
import sys
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

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

# ---------- Helpers ----------
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

# ---------- Call Graph Helpers ----------
def extract_function_bodies(code):
    functions = {}
    pattern = r'(?:\w+[\s\*]+)(?:\w+::)?(\w+)\s*\([^)]*\)\s*\{'
    for match in re.finditer(pattern, code):
        func_name = match.group(1)
        start = match.end()
        brace_count = 1
        pos = start
        while pos < len(code) and brace_count > 0:
            if code[pos] == '{':
                brace_count += 1
            elif code[pos] == '}':
                brace_count -= 1
            pos += 1
        body = code[start:pos-1]
        functions[func_name] = body
    return functions

def extract_calls(body):
    pattern = r'(?:\.|\->)?\s*(\w+)\s*\('
    raw_calls = re.findall(pattern, body)
    keywords = {'if', 'for', 'while', 'switch', 'catch', 'return',
                'else', 'auto', 'new', 'delete', 'sizeof', 'typeof'}
    return list(set(c for c in raw_calls if c not in keywords))

def find_callers(functions, target_name):
    callers = []
    for func_name, body in functions.items():
        if func_name == target_name:
            continue
        if re.search(r'\b' + target_name + r'\s*\(', body):
            callers.append(func_name)
    return callers

def generate_call_graph_figure(target, outgoing_calls, incoming_calls):
    G = nx.DiGraph()
    G.add_node(target)
    for callee in outgoing_calls:
        G.add_edge(target, callee)
    for caller in incoming_calls:
        G.add_edge(caller, target)

    color_map = []
    for node in G.nodes():
        if node == target:
            color_map.append('orange')
        elif node in incoming_calls:
            color_map.append('lightblue')
        else:
            color_map.append('lightgreen')

    fig, ax = plt.subplots(figsize=(10, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, ax=ax,
            node_color=color_map,
            node_size=2000,
            with_labels=True,
            font_size=9,
            arrowstyle='-|>',
            arrowsize=20,
            edge_color='gray')
    ax.set_title(f"Call Graph for {target}()", fontsize=13, fontweight='bold')

    legend_items = [
        mpatches.Patch(color='orange',     label='Target function'),
        mpatches.Patch(color='lightblue',  label='Callers (incoming)'),
        mpatches.Patch(color='lightgreen', label='Callees (outgoing)'),
    ]
    fig.legend(handles=legend_items, loc='lower center', ncol=3,
               fontsize=9, frameon=True, bbox_to_anchor=(0.5, -0.05))
    plt.tight_layout()
    return fig

# ---------- CFG Helpers ----------
def parse_blocks(code):
    lines = code.split('\n')
    blocks = []
    current_block = []
    split_keywords = re.compile(
        r'^\s*(if\s*\(|for\s*\(|while\s*\(|return\b|break\b|case\b|default\b|\}|\{)'
    )
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if split_keywords.match(stripped) and current_block:
            blocks.append('\n'.join(current_block))
            current_block = [stripped]
        else:
            current_block.append(stripped)
    if current_block:
        blocks.append('\n'.join(current_block))
    return [b for b in blocks if b.strip()]

def get_block_type(block):
    s = block.strip()
    if s.startswith('if'):       return 'if'
    elif s.startswith('for'):    return 'for'
    elif s.startswith('while'):  return 'while'
    elif s.startswith('return'): return 'return'
    elif s.startswith('break'):  return 'break'
    elif s.startswith('case') or s.startswith('default'): return 'case'
    elif s.startswith('}') or s.startswith('{'):          return 'bracket'
    else: return 'sequential'

def get_block_label(block, max_len=25):
    text = block.strip().replace('\n', ' ')
    return text[:max_len] + '...' if len(text) > max_len else text

def build_cfg(code):
    blocks = parse_blocks(code)
    G = nx.DiGraph()
    if not blocks:
        return G
    for i, block in enumerate(blocks):
        G.add_node(i, code=block, type=get_block_type(block))
    for i, block in enumerate(blocks):
        bt = get_block_type(block)
        if bt in ('return', 'break'):
            if i != len(blocks) - 1:
                G.add_edge(i, len(blocks) - 1, label='exit')
        elif bt == 'if':
            if i + 1 < len(blocks): G.add_edge(i, i + 1, label='true')
            if i + 2 < len(blocks): G.add_edge(i, i + 2, label='false')
        elif bt in ('for', 'while'):
            if i + 1 < len(blocks): G.add_edge(i, i + 1, label='loop_body')
            if i + 2 < len(blocks): G.add_edge(i, i + 2, label='loop_exit')
        else:
            if i + 1 < len(blocks): G.add_edge(i, i + 1, label='seq')
    return G

def diff_cfgs(cfg_before, cfg_after):
    before_nodes = dict(cfg_before.nodes(data=True))
    after_nodes  = dict(cfg_after.nodes(data=True))
    before_ids   = set(before_nodes.keys())
    after_ids    = set(after_nodes.keys())
    result = {'before_status': {}, 'after_status': {}}
    for nid in before_ids:
        if nid not in after_ids:
            result['before_status'][nid] = 'deleted'
        else:
            result['before_status'][nid] = (
                'unchanged'
                if before_nodes[nid]['code'].strip() == after_nodes[nid]['code'].strip()
                else 'modified'
            )
    for nid in after_ids:
        if nid not in before_ids:
            result['after_status'][nid] = 'added'
        else:
            result['after_status'][nid] = (
                'unchanged'
                if before_nodes[nid]['code'].strip() == after_nodes[nid]['code'].strip()
                else 'modified'
            )
    return result

def get_node_color(status):
    return {
        'unchanged': '#aaaaaa',
        'modified':  '#ff9900',
        'deleted':   '#ff4444',
        'added':     '#44bb44',
    }.get(status, '#aaaaaa')

def draw_cfg(ax, G, status_map, title):
    if G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, 'Empty CFG', ha='center', va='center',
                fontsize=12, color='gray')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.axis('off')
        return
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except Exception:
        pos = nx.spring_layout(G, seed=42)
    node_colors = [get_node_color(status_map.get(n, 'unchanged')) for n in G.nodes()]
    labels = {n: f"B{n}\n{get_block_label(d['code'])}" for n, d in G.nodes(data=True)}
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1800, alpha=0.9)
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                            font_size=6, font_color='white', font_weight='bold')
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowsize=20,
                           edge_color='#555555', connectionstyle='arc3,rad=0.1')
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=6, font_color='#333333')
    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.axis('off')

def generate_cfg_figure(before_code, after_code, title):
    cfg_before = build_cfg(before_code)
    cfg_after  = build_cfg(after_code)
    diff       = diff_cfgs(cfg_before, cfg_after)
    fig, axes  = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(title, fontsize=14, fontweight='bold')
    draw_cfg(axes[0], cfg_before, diff['before_status'], 'BEFORE')
    draw_cfg(axes[1], cfg_after,  diff['after_status'],  'AFTER')
    legend_items = [
        mpatches.Patch(color='#aaaaaa', label='Unchanged'),
        mpatches.Patch(color='#ff9900', label='Modified'),
        mpatches.Patch(color='#ff4444', label='Deleted'),
        mpatches.Patch(color='#44bb44', label='Added'),
    ]
    fig.legend(handles=legend_items, loc='lower center', ncol=4,
               fontsize=10, frameon=True, bbox_to_anchor=(0.5, -0.04))
    plt.tight_layout()
    return fig, diff, cfg_before, cfg_after

# ============================================================
# LAYOUT
# ============================================================

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
df       = load_results()
raw_data = load_raw_data()

if df.empty:
    st.warning("No results found yet. Click 'Run Risk Analysis' to generate results.")
    st.stop()

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Commits",  len(df))
k2.metric("High Risk",      int((df["risk_level"] == "HIGH").sum()))
k3.metric("Medium Risk",    int((df["risk_level"] == "MEDIUM").sum()))
k4.metric("Average Risk",   f"{df['risk_score'].mean():.3f}")

st.divider()

# ---------- Sidebar ----------
st.sidebar.header("Filters")
selected_levels = st.sidebar.multiselect(
    "Risk Level", options=["LOW", "MEDIUM", "HIGH"],
    default=["LOW", "MEDIUM", "HIGH"]
)
min_score, max_score = float(df["risk_score"].min()), float(df["risk_score"].max())
score_range  = st.sidebar.slider("Risk Score Range", min_score, max_score, (min_score, max_score))
search_text  = st.sidebar.text_input("Search Commit Title")

filtered_df = df[
    (df["risk_level"].isin(selected_levels)) &
    (df["risk_score"] >= score_range[0]) &
    (df["risk_score"] <= score_range[1])
].copy()
if search_text:
    filtered_df = filtered_df[
        filtered_df["commit_title"].str.contains(search_text, case=False, na=False)
    ]

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Commit Table", "Charts", "Commit Details", "Call Graph", "Differential CFG", "Actionable Insights"
])

# ── Tab 1 ────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Commit Risk Table")
    display_df = filtered_df.copy()
    display_df["risk_label"] = display_df["risk_level"].apply(risk_color)
    st.dataframe(
        display_df[[
            "commit_title", "risk_label", "risk_score",
            "cc_delta", "flow_score", "change_ratio"
        ]].sort_values("risk_score", ascending=False),
        use_container_width=True, hide_index=True
    )

# ── Tab 2 ────────────────────────────────────────────────────────────────────
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
    hm = filtered_df[["commit_title","cc_delta","flow_score","change_ratio","risk_score"]].copy()
    hm = hm.sort_values("risk_score", ascending=False).head(20)
    for col in ["cc_delta","flow_score","change_ratio","risk_score"]:
        mn, mx = hm[col].min(), hm[col].max()
        hm[col] = (hm[col] - mn) / (mx - mn) if mx > mn else 0.0
    hm_long = hm.melt(id_vars="commit_title", var_name="metric", value_name="value")
    heatmap = alt.Chart(hm_long).mark_rect().encode(
        x=alt.X("metric:N", title="Metric"),
        y=alt.Y("commit_title:N", sort="-x", title="Commit"),
        color=alt.Color("value:Q", title="Normalized Value"),
        tooltip=[
            alt.Tooltip("commit_title:N", title="Commit"),
            alt.Tooltip("metric:N",       title="Metric"),
            alt.Tooltip("value:Q",        title="Normalized Value", format=".3f")
        ]
    ).properties(width=700, height=500)
    st.altair_chart(heatmap, use_container_width=True)

# ── Tab 3 ────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Commit Details")
    options = filtered_df["commit_title"].tolist()
    if not options:
        st.info("No commits match the current filters.")
    else:
        selected_commit = st.selectbox("Choose a commit", options)
        row = filtered_df[filtered_df["commit_title"] == selected_commit].iloc[0]
        left, right = st.columns(2)
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
                st.error("This commit shows high bug risk. It likely changes control flow significantly, increases complexity, or modifies a large portion of code.")
            elif row["risk_level"] == "MEDIUM":
                st.warning("This commit shows moderate bug risk. It may deserve targeted testing around the modified logic.")
            else:
                st.success("This commit shows relatively low bug risk compared with the rest of the dataset.")

# ── Tab 4: Call Graph ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("Call Graph")
    st.caption("Visualize outgoing and incoming function calls for a selected commit.")

    cg_options = filtered_df["commit_title"].tolist()
    if not cg_options:
        st.info("No commits match the current filters.")
    else:
        selected_cg = st.selectbox("Choose a commit", cg_options, key="cg_commit")
        raw_entry   = next((r for r in raw_data if r.get("Commit title") == selected_cg), None)

        if raw_entry is None:
            st.warning("Raw code not found for this commit.")
        else:
            after_code = raw_entry.get("After_commit_codebase", "")
            if not after_code.strip():
                st.warning("No after-commit code available for this commit.")
            else:
                functions = extract_function_bodies(after_code)
                if not functions:
                    st.warning("Could not extract any function bodies from this commit.")
                else:
                    selected_func = st.selectbox(
                        "Select function to analyze",
                        list(functions.keys()),
                        key="cg_func"
                    )
                    outgoing = extract_calls(functions[selected_func])
                    incoming = find_callers(functions, selected_func)

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Functions in file", len(functions))
                    m2.metric("Outgoing calls",    len(outgoing))
                    m3.metric("Incoming calls",    len(incoming))

                    with st.spinner("Generating call graph..."):
                        fig = generate_call_graph_figure(selected_func, outgoing, incoming)
                        st.pyplot(fig)
                        plt.close(fig)

                    with st.expander("Call details"):
                        ca, cb = st.columns(2)
                        with ca:
                            st.markdown("**Calls out (outgoing)**")
                            for fn in sorted(outgoing): st.write(f"→ `{fn}`")
                            if not outgoing: st.write("None detected")
                        with cb:
                            st.markdown("**Called by (incoming)**")
                            for fn in sorted(incoming): st.write(f"← `{fn}`")
                            if not incoming: st.write("None detected")

# ── Tab 5: Differential CFG ───────────────────────────────────────────────────
with tab5:
    st.subheader("Differential CFG")
    st.caption("Side-by-side control flow graphs showing what changed between before and after the commit.")

    cfg_options = filtered_df["commit_title"].tolist()
    if not cfg_options:
        st.info("No commits match the current filters.")
    else:
        selected_cfg = st.selectbox("Choose a commit", cfg_options, key="cfg_commit")
        raw_cfg      = next((r for r in raw_data if r.get("Commit title") == selected_cfg), None)

        if raw_cfg is None:
            st.warning("Raw code not found for this commit.")
        else:
            before_code = raw_cfg.get("Before_commit_codebase", "")
            after_code  = raw_cfg.get("After_commit_codebase", "")

            if not before_code.strip() and not after_code.strip():
                st.warning("No before/after code available for this commit.")
            else:
                # Risk context strip
                risk_row = filtered_df[filtered_df["commit_title"] == selected_cfg]
                if not risk_row.empty:
                    r = risk_row.iloc[0]
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Risk Level",  r["risk_level"])
                    m2.metric("Risk Score",  f"{r['risk_score']:.3f}")
                    m3.metric("CC Delta",    r["cc_delta"])
                    m4.metric("Flow Score",  r["flow_score"])

                with st.spinner("Building CFG diff..."):
                    fig, diff, cfg_before, cfg_after = generate_cfg_figure(
                        before_code, after_code, selected_cfg
                    )
                    st.pyplot(fig)
                    plt.close(fig)

                with st.expander("CFG node summary"):
                    before_counts, after_counts = {}, {}
                    for s in diff["before_status"].values():
                        before_counts[s] = before_counts.get(s, 0) + 1
                    for s in diff["after_status"].values():
                        after_counts[s] = after_counts.get(s, 0) + 1
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**Before CFG**")
                        st.write(f"Nodes: {cfg_before.number_of_nodes()}")
                        for s, c in before_counts.items(): st.write(f"- {s}: {c}")
                    with cb:
                        st.markdown("**After CFG**")
                        st.write(f"Nodes: {cfg_after.number_of_nodes()}")
                        for s, c in after_counts.items(): st.write(f"- {s}: {c}")

                with st.expander("View before / after code"):
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**Before**")
                        st.code(before_code, language="cpp")
                    with cb:
                        st.markdown("**After**")
                        st.code(after_code, language="cpp")

# ── Tab 6: Actionable Insights ────────────────────────────────────────────────
with tab6:
    st.subheader("Actionable Insights")
    st.caption("Reviewer suggestions and review checklist based on the specific type of code change.")

    ai_options = filtered_df["commit_title"].tolist()
    if not ai_options:
        st.info("No commits match the current filters.")
    else:
        selected_ai = st.selectbox("Choose a commit", ai_options, key="ai_commit")
        row = filtered_df[filtered_df["commit_title"] == selected_ai].iloc[0]

        # ── Risk context ──────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Level",    risk_color(row["risk_level"]))
        m2.metric("Risk Score",    f"{row['risk_score']:.3f}")
        m3.metric("CC Delta",      row["cc_delta"])
        m4.metric("Flow Score",    row["flow_score"])

        st.divider()
        left, right = st.columns(2)

        # ── Suggested Reviewers ───────────────────────────────────────────────
        with left:
            st.markdown("### 👥 Suggested Reviewers")

            reviewers = []

            if row["risk_level"] == "HIGH":
                reviewers.append(("Senior Developer",
                                  "High overall risk — commit needs experienced review before merge."))
            if row["flow_score"] > filtered_df["flow_score"].quantile(0.75):
                reviewers.append(("Security Reviewer",
                                  "High control flow alteration may affect execution paths and security boundaries."))
            if row["cc_delta"] > filtered_df["cc_delta"].quantile(0.75):
                reviewers.append(("Architecture Reviewer",
                                  "Large complexity increase may have structural implications."))
            if row["change_ratio"] > filtered_df["change_ratio"].quantile(0.75):
                reviewers.append(("Module Owner",
                                  "Large portion of the function was rewritten — owner review recommended."))
            if not reviewers:
                reviewers.append(("Peer Reviewer",
                                  "Low risk commit — standard peer review is sufficient."))

            for name, reason in reviewers:
                st.markdown(f"**{name}**")
                st.caption(reason)
                st.write("")

        # ── Review Checklist ──────────────────────────────────────────────────
        with right:
            st.markdown("### ✅ Review Checklist")

            checklist = []

            # CC Delta driven items
            if row["cc_delta"] > 0:
                checklist.append("Verify new conditional logic behaves as intended")
                checklist.append("Check for unintended side effects in added branches")
            if row["cc_delta"] > filtered_df["cc_delta"].quantile(0.75):
                checklist.append("Consider whether added complexity can be simplified")
                checklist.append("Review maintainability of the updated logic")

            # Flow score driven items
            if row["flow_score"] > filtered_df["flow_score"].median():
                checklist.append("Check for unintended side effects in control flow changes")
                checklist.append("Test boundary conditions around modified control flow")
            if row["flow_score"] > filtered_df["flow_score"].quantile(0.75):
                checklist.append("Verify removed branches did not handle edge cases")
                checklist.append("Trace all new execution paths end-to-end")

            # Change ratio driven items
            if row["change_ratio"] > filtered_df["change_ratio"].median():
                checklist.append("Run targeted regression tests for the modified areas")
            if row["change_ratio"] > filtered_df["change_ratio"].quantile(0.75):
                checklist.append("Check whether dependent callers are affected by the rewrite")
                checklist.append("Confirm function signature and return behaviour are unchanged")

            # Default if nothing fired
            if not checklist:
                checklist = [
                    "Perform standard code review",
                    "Run normal unit and integration tests",
                ]

            # Deduplicate while preserving order
            seen, deduped = set(), []
            for item in checklist:
                if item not in seen:
                    seen.add(item)
                    deduped.append(item)

            for item in deduped:
                st.checkbox(item, key=f"ai_check_{selected_ai}_{item[:30]}")

        st.divider()

        # ── Testing Recommendation ────────────────────────────────────────────
        st.markdown("### 🧪 Testing Recommendation")
        if row["risk_level"] == "HIGH":
            st.error(
                "**Manual review required** before merge. "
                "Run focused regression tests on all functions that call this one. "
                "Consider adding new unit tests that cover the changed branches."
            )
        elif row["risk_level"] == "MEDIUM":
            st.warning(
                "**Targeted review recommended.** "
                "Run unit and integration tests around the modified logic. "
                "Pay attention to edge cases in any changed conditionals."
            )
        else:
            st.success(
                "**Standard review sufficient.** "
                "Normal unit tests and a peer review pass should be adequate for this commit."
            )