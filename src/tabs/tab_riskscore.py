# src/tabs/tab_riskscore.py
# Tab 4: Risk Score Analysis

import os
import re
import streamlit as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ============================================================
# RISK ENGINE FUNCTIONS (from risk_engine.py)
# ============================================================

def count_decision_points(code):
    """McCabe 1976 — count decision points for cyclomatic complexity."""
    keywords = r'\b(if|else|for|while|switch|case|catch)\b'
    operators = re.findall(r'(\&\&|\|\||\?)', code)
    keyword_matches = re.findall(keywords, code)
    return len(keyword_matches) + len(operators)


def cyclomatic_complexity_delta(before_code, after_code):
    """Difference in cyclomatic complexity between versions."""
    return count_decision_points(after_code) - count_decision_points(before_code)


def control_flow_alteration(before_code, after_code):
    """
    Total control flow disruption (Nagappan & Ball 2005).
    Counts added + deleted control flow keywords.
    """
    import difflib
    before_lines = before_code.splitlines()
    after_lines  = after_code.splitlines()
    diff = list(difflib.ndiff(before_lines, after_lines))

    added_flow   = sum(1 for l in diff if l.startswith('+ ') and
                       re.search(r'\b(if|for|while|switch|case|catch)\b', l))
    deleted_flow = sum(1 for l in diff if l.startswith('- ') and
                       re.search(r'\b(if|for|while|switch|case|catch)\b', l))
    return added_flow + deleted_flow


def change_size_ratio(before_code, after_code):
    """Relative code churn (Moser et al. 2008)."""
    import difflib
    before_lines = before_code.splitlines()
    after_lines  = after_code.splitlines()
    diff = list(difflib.ndiff(before_lines, after_lines))

    added   = sum(1 for l in diff if l.startswith('+ '))
    deleted = sum(1 for l in diff if l.startswith('- '))
    before  = max(len(before_lines), 1)
    return (added + deleted) / before


def normalize_single(value, min_val, max_val):
    """Normalize a single value given known min/max."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def compute_risk_score(before_code, after_code):
    """
    Compute final risk score from three metrics.
    Returns dict with all metrics and final score.
    """
    cc_delta   = cyclomatic_complexity_delta(before_code, after_code)
    flow_score = control_flow_alteration(before_code, after_code)
    ratio      = change_size_ratio(before_code, after_code)

    # Normalize using reasonable reference ranges
    norm_cc    = normalize_single(abs(cc_delta), 0, 20)
    norm_flow  = normalize_single(flow_score, 0, 15)
    norm_ratio = normalize_single(ratio, 0, 3.0)

    # Weighted combination (Menzies et al. 2007)
    risk = 0.33 * norm_cc + 0.33 * norm_flow + 0.34 * norm_ratio

    if risk < 0.3:   level = 'LOW'
    elif risk < 0.6: level = 'MEDIUM'
    else:            level = 'HIGH'

    return {
        'cc_before':   count_decision_points(before_code),
        'cc_after':    count_decision_points(after_code),
        'cc_delta':    cc_delta,
        'flow_score':  flow_score,
        'change_ratio': round(ratio, 3),
        'norm_cc':     round(norm_cc, 3),
        'norm_flow':   round(norm_flow, 3),
        'norm_ratio':  round(norm_ratio, 3),
        'risk_score':  round(risk, 3),
        'risk_level':  level
    }


# ============================================================
# VISUALIZATION
# ============================================================

def generate_risk_chart(metrics, output_path):
    """Generate a bar chart of the three normalized metrics."""
    labels = ['CC Delta\n(McCabe 1976)',
              'Flow Alteration\n(Nagappan & Ball 2005)',
              'Change Ratio\n(Moser et al. 2008)']
    values = [metrics['norm_cc'], metrics['norm_flow'], metrics['norm_ratio']]

    colors = []
    for v in values:
        if v >= 0.6:   colors.append('#ff4444')
        elif v >= 0.3: colors.append('#ff9900')
        else:          colors.append('#44bb44')

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(labels, values, color=colors, edgecolor='white',
                  linewidth=1.5, width=0.5)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom',
                fontsize=16, fontweight='bold')

    # Threshold lines
    ax.axhline(y=0.3, color='orange', linestyle='--',
               linewidth=1.5, alpha=0.7, label='Medium threshold (0.3)')
    ax.axhline(y=0.6, color='red',    linestyle='--',
               linewidth=1.5, alpha=0.7, label='High threshold (0.6)')

    ax.set_ylim(0, 1.1)
    ax.set_ylabel('Normalized Score (0-1)', fontsize=14)
    ax.set_title('Risk Metric Breakdown', fontsize=16, fontweight='bold')
    ax.tick_params(axis='both', labelsize=13)
    ax.legend(fontsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_gauge_chart(risk_score, risk_level, output_path):
    """Generate a gauge/speedometer chart for overall risk score."""
    fig, ax = plt.subplots(figsize=(6, 4),
                           subplot_kw={'projection': 'polar'})

    # Draw colored arc segments
    theta_low    = np.linspace(np.pi, np.pi * 1.6, 100)
    theta_medium = np.linspace(np.pi * 1.6, np.pi * 1.87, 100)
    theta_high   = np.linspace(np.pi * 1.87, np.pi * 2, 100)

    ax.fill_between(theta_low,    0.7, 1.0, color='#44bb44', alpha=0.7)
    ax.fill_between(theta_medium, 0.7, 1.0, color='#ff9900', alpha=0.7)
    ax.fill_between(theta_high,   0.7, 1.0, color='#ff4444', alpha=0.7)

    # Needle
    needle_angle = np.pi + (risk_score * np.pi)
    ax.annotate('', xy=(needle_angle, 0.85),
                xytext=(needle_angle + np.pi, 0.0),
                arrowprops=dict(arrowstyle='->', color='black',
                                lw=2.5, mutation_scale=15))

    # Labels
    color_map = {'LOW': '#44bb44', 'MEDIUM': '#ff9900', 'HIGH': '#ff4444'}
    ax.text(0, 0, f'{risk_score:.2f}\n{risk_level}',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=color_map.get(risk_level, 'black'))

    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines['polar'].set_visible(False)
    ax.set_title('Overall Risk Score', fontsize=12,
                 fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_riskscore_tab(before_path, after_path,
                         before_label, after_label, results_dir):
    """Main render function called from dashboard.py"""

    st.header("📊 Risk Score Analysis")
    st.write("Quantifies commit risk using three established software metrics.")

    # Show selected files
    col1, col2 = st.columns(2)
    with col1:
        if before_label:
            st.info(f"📄 Before: `{before_label}`")
        else:
            st.warning("No before file selected.")
    with col2:
        if after_label:
            st.info(f"📄 After: `{after_label}`")
        else:
            st.warning("No after file selected.")

    # Session state
    if 'risk_metrics' not in st.session_state:
        st.session_state.risk_metrics   = None
    if 'risk_chart'   not in st.session_state:
        st.session_state.risk_chart     = None
    if 'gauge_chart'  not in st.session_state:
        st.session_state.gauge_chart    = None

    # Analyze button
    if st.button("🚀 Compute Risk Score", type="primary"):
        if not before_path or not after_path:
            st.error("Please provide both before and after files.")
        else:
            with st.spinner("Computing risk metrics..."):
                try:
                    with open(before_path, 'r') as f:
                        before_code = f.read()
                    with open(after_path, 'r') as f:
                        after_code = f.read()

                    metrics = compute_risk_score(before_code, after_code)
                    st.session_state.risk_metrics = metrics

                    chart_path = os.path.join(results_dir, "risk_chart.png")
                    gauge_path = os.path.join(results_dir, "gauge_chart.png")
                    generate_risk_chart(metrics, chart_path)
                    generate_gauge_chart(metrics['risk_score'],
                                         metrics['risk_level'], gauge_path)
                    st.session_state.risk_chart  = chart_path
                    st.session_state.gauge_chart = gauge_path
                    st.success("✅ Risk Score computed successfully!")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Display results
    if st.session_state.risk_metrics:
        m = st.session_state.risk_metrics

        st.divider()

        # Overall risk banner
        color_map = {'LOW': '🟢', 'MEDIUM': '🟠', 'HIGH': '🔴'}
        emoji = color_map.get(m['risk_level'], '⚪')
        st.markdown(
            f"### {emoji} Overall Risk: **{m['risk_level']}** "
            f"(Score: `{m['risk_score']}`)"
        )

        st.divider()

        # Gauge + bar chart side by side
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.session_state.gauge_chart and \
               os.path.exists(st.session_state.gauge_chart):
                st.image(st.session_state.gauge_chart, width=320)

        with col2:
            if st.session_state.risk_chart and \
               os.path.exists(st.session_state.risk_chart):
                st.image(st.session_state.risk_chart, width=600)

        st.divider()

        # Metric details table
        st.subheader("📋 Detailed Metrics")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Cyclomatic Complexity")
            st.markdown(f"- **Before:** `{m['cc_before']}`")
            st.markdown(f"- **After:** `{m['cc_after']}`")
            st.markdown(f"- **Delta:** `{m['cc_delta']:+d}`")
            st.markdown(f"- **Normalized:** `{m['norm_cc']}`")
            st.caption("📖 McCabe (1976)")

        with col2:
            st.markdown("#### Control Flow Alteration")
            st.markdown(f"- **Score:** `{m['flow_score']}`")
            st.markdown(f"- **Normalized:** `{m['norm_flow']}`")
            st.caption("📖 Nagappan & Ball (2005)")

        with col3:
            st.markdown("#### Change Size Ratio")
            st.markdown(f"- **Ratio:** `{m['change_ratio']}`")
            st.markdown(f"- **Normalized:** `{m['norm_ratio']}`")
            st.caption("📖 Moser et al. (2008)")

    # Info box
    with st.expander("ℹ️ About Risk Score"):
        st.markdown("""
        **Three metrics combined:**

        | Metric | Formula | Reference |
        |---|---|---|
        | CC Delta | after_CC − before_CC | McCabe 1976 |
        | Flow Alteration | added_flow + deleted_flow | Nagappan & Ball 2005 |
        | Change Ratio | (added + deleted) / before_lines | Moser et al. 2008 |

        **Final score:**
        ```
        risk = 0.33 × norm_CC + 0.33 × norm_flow + 0.34 × norm_ratio
        ```

        **Thresholds (Arisholm et al. 2010):**
        - LOW: score < 0.3
        - MEDIUM: 0.3 ≤ score < 0.6
        - HIGH: score ≥ 0.6
        """)