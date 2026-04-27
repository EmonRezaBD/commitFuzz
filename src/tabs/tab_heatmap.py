# src/tabs/tab_heatmap.py
# Tab 3: Risk Heatmap Analysis

import os
import re
import base64
import difflib
import streamlit as st
import streamlit.components.v1 as components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch


# ============================================================
# CORE FUNCTIONS (from heatmap.py)
# ============================================================

def load_file(filepath):
    with open(filepath, 'r') as f:
        return f.readlines()


def compute_diff(before_lines, after_lines):
    diff = list(difflib.ndiff(before_lines, after_lines))
    result = []
    for line in diff:
        if line.startswith('+ '):
            result.append(('added', line[2:].rstrip()))
        elif line.startswith('- '):
            result.append(('deleted', line[2:].rstrip()))
        elif line.startswith('  '):
            result.append(('unchanged', line[2:].rstrip()))
    return result


def score_line(line):
    """
    Score a line's risk based on control flow keywords.
    McCabe 1976 — decision points = risk indicators.
    """
    high_risk_patterns = [
        r'\bif\b', r'\bfor\b', r'\bwhile\b',
        r'\bswitch\b', r'\bcase\b', r'\bcatch\b',
        r'\&\&', r'\|\|', r'\?'
    ]
    medium_risk_patterns = [
        r'\w+\s*\(',
        r'\bnew\b', r'\bdelete\b', r'\bmalloc\b', r'\bfree\b'
    ]
    score = 0
    for p in high_risk_patterns:
        if re.search(p, line):
            score += 2
    for p in medium_risk_patterns:
        if re.search(p, line):
            score += 1

    if score >= 2:   return 'HIGH'
    elif score >= 1: return 'MEDIUM'
    else:            return 'LOW'


def get_line_color(status, risk):
    if status == 'added':
        return {'HIGH': '#ffcccc', 'MEDIUM': '#ffe0b2', 'LOW': '#ccffcc'}.get(risk, '#ccffcc')
    elif status == 'deleted':
        return '#e0e0e0'
    return '#ffffff'


def get_line_prefix(status):
    return {'added': '+ ', 'deleted': '- ', 'unchanged': '  '}.get(status, '  ')


def generate_heatmap_image(diff_result, title, output_path):
    """Generate heatmap image from diff result."""
    display_lines = []
    unchanged_count = 0

    for status, line in diff_result:
        if status == 'unchanged':
            unchanged_count += 1
            if unchanged_count <= 3:
                display_lines.append((status, line, 'LOW'))
        else:
            unchanged_count = 0
            risk = score_line(line) if status == 'added' else 'LOW'
            display_lines.append((status, line, risk))

    if not display_lines:
        return None

    n_lines = len(display_lines)
    fig_height = max(8, n_lines * 0.28)
    fig, ax = plt.subplots(figsize=(18, fig_height))
    ax.axis('off')

    for i, (status, line, risk) in enumerate(display_lines):
        y = n_lines - i
        bg_color = get_line_color(status, risk)

        rect = FancyBboxPatch(
            (0, y - 0.5), 1, 1,
            boxstyle="square,pad=0",
            facecolor=bg_color,
            edgecolor='#dddddd',
            linewidth=0.3,
            transform=ax.transData
        )
        ax.add_patch(rect)

        prefix = get_line_prefix(status)
        badge  = f' [{risk}]' if status == 'added' else ''
        text   = line[:110] + '...' if len(line) > 110 else line
        color  = '#cc0000' if status == 'deleted' else '#000000'

        ax.text(0.005, y, f"{prefix}{text}{badge}",
                fontsize=6.5, fontfamily='monospace',
                color=color, va='center', ha='left',
                transform=ax.transData)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_lines + 1)
    fig.suptitle(title, fontsize=13, fontweight='bold', y=1.005)

    legend_items = [
        mpatches.Patch(color='#ffcccc', label='Added - HIGH'),
        mpatches.Patch(color='#ffe0b2', label='Added - MEDIUM'),
        mpatches.Patch(color='#ccffcc', label='Added - LOW'),
        mpatches.Patch(color='#e0e0e0', label='Deleted'),
        mpatches.Patch(color='#ffffff', label='Unchanged'),
    ]
    fig.legend(handles=legend_items, loc='lower center',
               ncol=5, fontsize=9, frameon=True,
               bbox_to_anchor=(0.5, -0.01))

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    # Return summary stats
    added   = [(s, l) for s, l in diff_result if s == 'added']
    deleted = [(s, l) for s, l in diff_result if s == 'deleted']
    stats = {
        'total':     len(diff_result),
        'added':     len(added),
        'deleted':   len(deleted),
        'unchanged': len(diff_result) - len(added) - len(deleted),
        'high':      sum(1 for s, l in added if score_line(l) == 'HIGH'),
        'medium':    sum(1 for s, l in added if score_line(l) == 'MEDIUM'),
        'low':       sum(1 for s, l in added if score_line(l) == 'LOW'),
        'high_lines': [l.strip()[:80] for s, l in added if score_line(l) == 'HIGH'][:5]
    }
    return stats


def render_zoomable_image(png_path, height=800):
    with open(png_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    uid = f"hm_{height}"
    html = f"""
<style>
  #wrap_{uid} {{
    overflow: auto;
    width: 100%;
    height: {height}px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #fff;
    position: relative;
    cursor: grab;
    scrollbar-width: thin;
    scrollbar-color: #aaaaaa #f0f0f0;
  }}
  #wrap_{uid}::-webkit-scrollbar {{ width:14px; height:14px; }}
  #wrap_{uid}::-webkit-scrollbar-track {{ background:#f0f0f0; border-radius:4px; }}
  #wrap_{uid}::-webkit-scrollbar-thumb {{ background:#aaaaaa; border-radius:4px; }}
  #wrap_{uid}::-webkit-scrollbar-thumb:hover {{ background:#888888; }}
</style>
<div id="wrap_{uid}">
  <div id="hm_container_{uid}" style="transform-origin:top left;
                                       position:absolute; top:0; left:0; width:100%;">
    <img src="data:image/png;base64,{encoded}"
         style="display:block; width:100%;"/>
  </div>
</div>
<p style="font-size:12px; color:gray; margin-top:4px;">
  🖱️ Scroll to zoom &nbsp;|&nbsp; Click + drag to pan &nbsp;|&nbsp; Double-click to reset
</p>
<script>
(function() {{
    const c = document.getElementById('hm_container_{uid}');
    const w = document.getElementById('wrap_{uid}');
    let scale=1, px=0, py=0, drag=false, sx, sy;
    w.addEventListener('wheel', e => {{
        e.preventDefault();
        scale=Math.min(Math.max(0.3,scale+(e.deltaY>0?-0.1:0.1)),5);
        c.style.transform=`translate(${{px}}px,${{py}}px) scale(${{scale}})`;
    }}, {{passive:false}});
    w.addEventListener('mousedown', e => {{
        drag=true; sx=e.clientX-px; sy=e.clientY-py;
        w.style.cursor='grabbing';
    }});
    window.addEventListener('mousemove', e => {{
        if(!drag) return;
        px=e.clientX-sx; py=e.clientY-sy;
        c.style.transform=`translate(${{px}}px,${{py}}px) scale(${{scale}})`;
    }});
    window.addEventListener('mouseup',()=>{{drag=false;w.style.cursor='grab';}});
    w.addEventListener('dblclick',()=>{{
        scale=1;px=0;py=0;
        c.style.transform='translate(0px,0px) scale(1)';
    }});
}})();
</script>
"""
    components.html(html, height=height + 30)


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_heatmap_tab(before_path, after_path, before_label, after_label, results_dir):
    """Main render function called from dashboard.py"""

    st.header("🌡️ Risk Heatmap Analysis")
    st.write("Highlights line-by-line risk of code changes based on control flow complexity.")

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

    # Session state init
    if 'heatmap_png'   not in st.session_state:
        st.session_state.heatmap_png   = None
    if 'heatmap_stats' not in st.session_state:
        st.session_state.heatmap_stats = None

    # Analyze button
    if st.button("🚀 Generate Risk Heatmap", type="primary"):
        if not before_path or not after_path:
            st.error("Please provide both before and after files.")
        else:
            with st.spinner("Analyzing code changes..."):
                try:
                    before_lines = load_file(before_path)
                    after_lines  = load_file(after_path)
                    diff_result  = compute_diff(before_lines, after_lines)
                    output_path  = os.path.join(results_dir, "heatmap.png")
                    stats = generate_heatmap_image(
                        diff_result=diff_result,
                        title="Risk Heatmap",
                        output_path=output_path
                    )
                    st.session_state.heatmap_png   = output_path
                    st.session_state.heatmap_stats = stats
                    st.success("✅ Risk Heatmap generated successfully!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Display results
    if st.session_state.heatmap_png and os.path.exists(st.session_state.heatmap_png):
        png_path = st.session_state.heatmap_png
        stats    = st.session_state.heatmap_stats

        # Heatmap image
        render_zoomable_image(png_path, height=900)

        # Download
        with open(png_path, 'rb') as f:
            st.download_button(
                label="⬇️ Download Heatmap",
                data=f,
                file_name="heatmap.png",
                mime="image/png"
            )

    # Info box
    with st.expander("ℹ️ About Risk Heatmap"):
        st.markdown("""
        **What is a Risk Heatmap?**
        A line-by-line visualization of source code changes, colored by risk level.

        **Color coding:**
        - 🔴 **Red** = Added line with HIGH risk (control flow: if/for/while/&&/||)
        - 🟠 **Orange** = Added line with MEDIUM risk (function calls)
        - 🟢 **Green** = Added line with LOW risk (assignments, declarations)
        - ⬜ **Gray** = Deleted line
        - ⬜ **White** = Unchanged line

        **Risk scoring per line (McCabe 1976):**
        - Control flow keyword = +2 points → HIGH if score ≥ 2
        - Function call = +1 point → MEDIUM if score = 1
        - Otherwise → LOW

        **Reference:** Nagappan & Ball (2005). "Use of Relative Code Churn Measures to Predict System Defect Density." ICSE.
        """)