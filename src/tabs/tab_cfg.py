# src/tabs/tab_cfg.py
# Tab 2: Differential CFG Analysis

import os
import base64
import streamlit as st
import streamlit.components.v1 as components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import re


# ============================================================
# CFG CORE FUNCTIONS (from cfg_combined.py)
# ============================================================

def parse_blocks(code):
    """Split C++ code into basic blocks at control flow boundaries."""
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

    blocks = [b for b in blocks if b.strip()]
    return blocks


def get_block_type(block):
    """Determine the type of a basic block."""
    stripped = block.strip()
    if stripped.startswith('if'):       return 'if'
    elif stripped.startswith('for'):    return 'for'
    elif stripped.startswith('while'):  return 'while'
    elif stripped.startswith('return'): return 'return'
    elif stripped.startswith('break'):  return 'break'
    elif stripped.startswith('case') or stripped.startswith('default'): return 'case'
    elif stripped.startswith('}') or stripped.startswith('{'):          return 'bracket'
    else: return 'sequential'


def get_block_label(block, max_len=30):
    """Shorten block text for display on graph nodes."""
    text = block.strip().replace('\n', ' ')
    return text[:max_len] + '...' if len(text) > max_len else text


def build_cfg(code):
    """Build a control flow graph from C++ code."""
    blocks = parse_blocks(code)
    G = nx.DiGraph()

    if not blocks:
        return G

    for i, block in enumerate(blocks):
        block_type = get_block_type(block)
        G.add_node(i, code=block, type=block_type)

    for i, block in enumerate(blocks):
        block_type = get_block_type(block)

        if block_type in ('return', 'break'):
            if i != len(blocks) - 1:
                G.add_edge(i, len(blocks) - 1, label='exit')
        elif block_type == 'if':
            if i + 1 < len(blocks):
                G.add_edge(i, i + 1, label='true')
            if i + 2 < len(blocks):
                G.add_edge(i, i + 2, label='false')
        elif block_type in ('for', 'while'):
            if i + 1 < len(blocks):
                G.add_edge(i, i + 1, label='loop_body')
            if i + 2 < len(blocks):
                G.add_edge(i, i + 2, label='loop_exit')
        else:
            if i + 1 < len(blocks):
                G.add_edge(i, i + 1, label='seq')

    return G


def diff_cfgs(cfg_before, cfg_after):
    """Compare two CFGs and label nodes as unchanged/modified/deleted/added."""
    before_nodes = dict(cfg_before.nodes(data=True))
    after_nodes  = dict(cfg_after.nodes(data=True))

    before_ids = set(before_nodes.keys())
    after_ids  = set(after_nodes.keys())

    result = {'before_status': {}, 'after_status': {}}

    for nid in before_ids:
        if nid not in after_ids:
            result['before_status'][nid] = 'deleted'
        else:
            before_code = before_nodes[nid]['code'].strip()
            after_code  = after_nodes[nid]['code'].strip()
            result['before_status'][nid] = 'unchanged' if before_code == after_code else 'modified'

    for nid in after_ids:
        if nid not in before_ids:
            result['after_status'][nid] = 'added'
        else:
            before_code = before_nodes[nid]['code'].strip()
            after_code  = after_nodes[nid]['code'].strip()
            result['after_status'][nid] = 'unchanged' if before_code == after_code else 'modified'

    return result


def get_node_color(status):
    """Map diff status to display color."""
    return {
        'unchanged': '#aaaaaa',
        'modified':  '#ff9900',
        'deleted':   '#ff4444',
        'added':     '#44bb44',
    }.get(status, '#aaaaaa')


def get_hierarchical_layout(G):
    """
    Try layouts in order of preference:
    1. graphviz 'dot' — best hierarchical/tree layout
    2. graphviz 'neato' — spring-based, better than networkx spring
    3. networkx shell layout — cleaner than spring
    4. networkx spring layout — last resort
    """
    try:
        return nx.nx_agraph.graphviz_layout(
            G, prog='dot',
            args='-Gnodesep=1.0 -Granksep=1.5 -Gsplines=ortho'
        )
    except Exception:
        pass
    try:
        return nx.nx_agraph.graphviz_layout(G, prog='neato')
    except Exception:
        pass
    try:
        return nx.shell_layout(G)
    except Exception:
        pass
    return nx.spring_layout(G, seed=42, k=4.0, iterations=200)


def draw_cfg(ax, G, status_map, title):
    """Draw a single CFG on a matplotlib axis with colored nodes."""
    if G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, 'Empty CFG', ha='center', va='center',
                fontsize=12, color='gray')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.axis('off')
        return

    pos = get_hierarchical_layout(G)

    node_colors = [get_node_color(status_map.get(n, 'unchanged'))
                   for n in G.nodes()]

    labels = {n: f"B{n}\n{get_block_label(d['code'], 20)}"
              for n, d in G.nodes(data=True)}

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=3000, alpha=0.92)
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                            font_size=6, font_color='white', font_weight='bold')
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                           arrowsize=15, edge_color='#444444',
                           connectionstyle='arc3,rad=0.05',
                           min_source_margin=20, min_target_margin=20)

    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=5, font_color='#333333')

    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.axis('off')


def generate_cfg_image(before_code, after_code, title, output_path):
    """Generate side-by-side differential CFG image."""
    cfg_before = build_cfg(before_code)
    cfg_after  = build_cfg(after_code)
    diff       = diff_cfgs(cfg_before, cfg_after)

    fig, axes = plt.subplots(1, 2, figsize=(36, 22))
    fig.suptitle(title, fontsize=15, fontweight='bold', y=1.01)

    draw_cfg(axes[0], cfg_before, diff['before_status'], 'BEFORE')
    draw_cfg(axes[1], cfg_after,  diff['after_status'],  'AFTER')

    legend_items = [
        mpatches.Patch(color='#aaaaaa', label='Unchanged'),
        mpatches.Patch(color='#ff9900', label='Modified'),
        mpatches.Patch(color='#ff4444', label='Deleted'),
        mpatches.Patch(color='#44bb44', label='Added'),
    ]
    fig.legend(handles=legend_items, loc='lower center',
               ncol=4, fontsize=10, frameon=True,
               bbox_to_anchor=(0.5, -0.04))

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    # Return diff stats
    stats = {
        'before_nodes': cfg_before.number_of_nodes(),
        'after_nodes':  cfg_after.number_of_nodes(),
        'added':     sum(1 for s in diff['after_status'].values()  if s == 'added'),
        'deleted':   sum(1 for s in diff['before_status'].values() if s == 'deleted'),
        'modified':  sum(1 for s in diff['before_status'].values() if s == 'modified'),
        'unchanged': sum(1 for s in diff['before_status'].values() if s == 'unchanged'),
    }
    return stats


def render_zoomable_image(png_path, height=650):
    """Render a PNG with mouse wheel zoom and drag-to-pan."""
    with open(png_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    html = f"""
<div style="overflow:hidden; width:100%; height:{height}px;
            border:1px solid #ddd; border-radius:8px;
            background:#fafafa; position:relative; cursor:grab;">
    <div id="cfg_container" style="transform-origin:top left;
                                    position:absolute; top:0; left:0;">
        <img src="data:image/png;base64,{encoded}"
             style="display:block; width:100%;"/>
    </div>
</div>
<p style="font-size:12px; color:gray; margin-top:4px;">
    🖱️ Scroll to zoom &nbsp;|&nbsp; Click + drag to pan &nbsp;|&nbsp; Double-click to reset
</p>
<script>
    const c = document.getElementById('cfg_container');
    const w = c.parentElement;
    let scale=1, px=0, py=0, drag=false, sx, sy;

    w.addEventListener('wheel', e => {{
        e.preventDefault();
        scale = Math.min(Math.max(0.3, scale + (e.deltaY>0?-0.1:0.1)), 5);
        c.style.transform = `translate(${{px}}px,${{py}}px) scale(${{scale}})`;
    }}, {{passive:false}});

    w.addEventListener('mousedown', e => {{
        drag=true; sx=e.clientX-px; sy=e.clientY-py;
        w.style.cursor='grabbing';
    }});
    window.addEventListener('mousemove', e => {{
        if(!drag) return;
        px=e.clientX-sx; py=e.clientY-sy;
        c.style.transform = `translate(${{px}}px,${{py}}px) scale(${{scale}})`;
    }});
    window.addEventListener('mouseup', () => {{ drag=false; w.style.cursor='grab'; }});
    w.addEventListener('dblclick', () => {{
        scale=1; px=0; py=0;
        c.style.transform='translate(0px,0px) scale(1)';
    }});
</script>
"""
    components.html(html, height=height + 30)


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_cfg_tab(before_path, after_path, before_label, after_label, results_dir):
    """Main render function called from dashboard.py"""

    st.header("🌊 Differential CFG Analysis")
    st.write("Compares control flow graphs before and after a commit to highlight structural changes.")

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
    if 'cfg_png' not in st.session_state:
        st.session_state.cfg_png  = None
    if 'cfg_stats' not in st.session_state:
        st.session_state.cfg_stats = None

    # Analyze button
    if st.button("🚀 Generate Differential CFG", type="primary"):
        if not before_path or not after_path:
            st.error("Please provide both before and after files.")
        else:
            with st.spinner("Generating CFGs... please wait"):
                try:
                    # Read files
                    with open(before_path, 'r') as f:
                        before_code = f.read()
                    with open(after_path, 'r') as f:
                        after_code = f.read()

                    output_path = os.path.join(results_dir, "cfg_diff.png")
                    stats = generate_cfg_image(
                        before_code=before_code,
                        after_code=after_code,
                        title="Differential CFG",
                        output_path=output_path
                    )
                    st.session_state.cfg_png   = output_path
                    st.session_state.cfg_stats = stats
                    st.success("✅ Differential CFG generated successfully!")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Display results (persists via session state)
    if st.session_state.cfg_png and os.path.exists(st.session_state.cfg_png):
        png_path = st.session_state.cfg_png

        # CFG image with zoom
        render_zoomable_image(png_path, height=1100)

        # Download button
        with open(png_path, 'rb') as f:
            st.download_button(
                label="⬇️ Download CFG Image",
                data=f,
                file_name="cfg_diff.png",
                mime="image/png"
            )

    # Info box
    with st.expander("ℹ️ About Differential CFG"):
        st.markdown("""
        **What is a CFG?**
        A Control Flow Graph (CFG) models execution paths through a function.
        Nodes = code blocks, Edges = execution transitions.

        **What is Differential CFG?**
        Side-by-side comparison of CFGs before and after a commit.

        **Color coding:**
        - ⬜ **Gray** = Unchanged block
        - 🟠 **Orange** = Modified block
        - 🔴 **Red** = Deleted block
        - 🟢 **Green** = Added block

        **What to look for:**
        - New branches (if/for/while) = increased complexity = higher AC attack risk
        - Modified blocks near loop boundaries = potential pathological input surface

        **Reference:** McCabe, T.J. (1976). "A Complexity Measure." IEEE TSE.
        """)