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
    """Draw CFG with fast circular nodes — used for full file CFG."""
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


def draw_cfg_ellipse(ax, G, status_map, title):
    """Draw CFG with elliptical nodes — used for function-specific CFG."""
    if G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, 'Empty CFG', ha='center', va='center',
                fontsize=12, color='gray')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.axis('off')
        return

    pos = get_hierarchical_layout(G)

    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    x_pad = max((max(xs) - min(xs)) * 0.25, 80)
    y_pad = max((max(ys) - min(ys)) * 0.25, 60)
    ax.set_xlim(min(xs) - x_pad, max(xs) + x_pad)
    ax.set_ylim(min(ys) - y_pad, max(ys) + y_pad)
    ax.set_aspect('auto')
    ax.axis('off')

    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                           arrowsize=14, edge_color='#444444',
                           connectionstyle='arc3,rad=0.05',
                           min_source_margin=40, min_target_margin=40)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=5, font_color='#333333')

    renderer = ax.get_figure().canvas.get_renderer()
    for node, data in G.nodes(data=True):
        x, y   = pos[node]
        color  = get_node_color(status_map.get(node, 'unchanged'))
        label  = get_block_label(data['code'], 22)

        txt = ax.text(x, y, label, ha='center', va='center',
                      fontsize=7, fontweight='bold', color='white',
                      zorder=5, multialignment='center')
        ax.get_figure().canvas.draw()
        bbox   = txt.get_window_extent(renderer=renderer)
        inv    = ax.transData.inverted()
        b      = inv.transform([[bbox.x0, bbox.y0], [bbox.x1, bbox.y1]])
        w_data = (b[1][0] - b[0][0]) * 2.0
        h_data = (b[1][1] - b[0][1]) * 3.0

        ellipse = mpatches.Ellipse(
            (x, y),
            width=max(abs(w_data), 30),
            height=max(abs(h_data), 18),
            facecolor=color, edgecolor='white',
            linewidth=1.2, alpha=0.93, zorder=4
        )
        ax.add_patch(ellipse)
        txt.set_zorder(5)

    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)


def generate_cfg_image(before_code, after_code, title, output_path):
    """Generate side-by-side CFG with fast circular nodes (full file)."""
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

    stats = {
        'before_nodes': cfg_before.number_of_nodes(),
        'after_nodes':  cfg_after.number_of_nodes(),
        'added':     sum(1 for s in diff_cfgs(cfg_before, cfg_after)['after_status'].values()  if s == 'added'),
        'deleted':   sum(1 for s in diff_cfgs(cfg_before, cfg_after)['before_status'].values() if s == 'deleted'),
        'modified':  sum(1 for s in diff_cfgs(cfg_before, cfg_after)['before_status'].values() if s == 'modified'),
        'unchanged': sum(1 for s in diff_cfgs(cfg_before, cfg_after)['before_status'].values() if s == 'unchanged'),
    }
    return stats


def generate_cfg_image_ellipse(before_code, after_code, title, output_path):
    """Generate side-by-side CFG with elliptical nodes (function-specific)."""
    cfg_before = build_cfg(before_code)
    cfg_after  = build_cfg(after_code)
    diff       = diff_cfgs(cfg_before, cfg_after)

    fig, axes = plt.subplots(1, 2, figsize=(24, 14))
    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.01)

    draw_cfg_ellipse(axes[0], cfg_before, diff['before_status'], 'BEFORE')
    draw_cfg_ellipse(axes[1], cfg_after,  diff['after_status'],  'AFTER')

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


def render_zoomable_image(png_path, height=650):
    """Render a PNG with mouse wheel zoom, drag-to-pan, and gray scrollbar."""
    with open(png_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    uid = f"cfg_{height}"
    html = f"""
<style>
  #wrap_{uid} {{
    overflow: auto;
    width: 100%;
    height: {height}px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #fafafa;
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
  <div id="cfg_container_{uid}" style="transform-origin:top left;
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
    const c = document.getElementById('cfg_container_{uid}');
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
    if 'cfg_png'       not in st.session_state: st.session_state.cfg_png       = None
    if 'cfg_stats'     not in st.session_state: st.session_state.cfg_stats     = None
    if 'cfg_func_png'  not in st.session_state: st.session_state.cfg_func_png  = None
    if 'cfg_before_code' not in st.session_state: st.session_state.cfg_before_code = None
    if 'cfg_after_code'  not in st.session_state: st.session_state.cfg_after_code  = None

    # ── Feature 1: Full Differential CFG ──────────────────────
    st.subheader("1️⃣ Full File Differential CFG")

    if st.button("🚀 Generate Differential CFG", type="primary",
                 key="btn_full_cfg"):
        if not before_path or not after_path:
            st.error("Please provide both before and after files.")
        else:
            with st.spinner("Generating CFGs... please wait"):
                try:
                    with open(before_path, 'r') as f:
                        before_code = f.read()
                    with open(after_path, 'r') as f:
                        after_code = f.read()

                    st.session_state.cfg_before_code = before_code
                    st.session_state.cfg_after_code  = after_code

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

    if st.session_state.cfg_png and os.path.exists(st.session_state.cfg_png):
        render_zoomable_image(st.session_state.cfg_png, height=1100)
        with open(st.session_state.cfg_png, 'rb') as f:
            st.download_button(
                label="⬇️ Download CFG Image", data=f,
                file_name="cfg_diff.png", mime="image/png",
                key="dl_full_cfg"
            )

    st.divider()

    # ── Feature 2: Function-Specific CFG ──────────────────────
    st.subheader("2️⃣ Function-Specific Differential CFG")
    st.caption("Select a function to see its CFG before and after the commit.")

    if st.session_state.cfg_before_code is None:
        st.info("👆 Generate the Full CFG first to enable this feature.")
    else:
        before_code = st.session_state.cfg_before_code
        after_code  = st.session_state.cfg_after_code

        # Extract function names from both files
        import re as _re
        func_pattern = r'(?:\w+[\s\*]+)(?:\w+::)?(\w+)\s*\([^)]*\)\s*\{'
        before_funcs = set(_re.findall(func_pattern, before_code))
        after_funcs  = set(_re.findall(func_pattern, after_code))
        all_funcs    = sorted(before_funcs | after_funcs)

        col1, col2 = st.columns([3, 1])
        with col1:
            typed_func = st.text_input(
                "Type function name",
                placeholder="e.g. analyzeColumn, loadCSV...",
                key="cfg_func_input"
            )
        with col2:
            selected_func = st.selectbox(
                "Or pick from list",
                options=["— select —"] + all_funcs,
                key="cfg_func_select"
            )

        target_func = None
        if typed_func.strip():
            target_func = typed_func.strip()
        elif selected_func != "— select —":
            target_func = selected_func

        if target_func:
            st.caption(f"Target: **`{target_func}`**")

        if st.button("🔍 Generate Function CFG", type="primary",
                     key="btn_func_cfg"):
            if not target_func:
                st.warning("Please enter or select a function name.")
            else:
                with st.spinner(f"Generating CFG for {target_func}..."):
                    try:
                        # Extract function body from before
                        def extract_func_body(code, fname):
                            pattern = (r'(?:\w+[\s\*]+)(?:\w+::)?' +
                                       _re.escape(fname) +
                                       r'\s*\([^)]*\)\s*\{')
                            match = _re.search(pattern, code)
                            if not match:
                                return None
                            start = match.end()
                            brace = 1
                            pos   = start
                            while pos < len(code) and brace > 0:
                                if code[pos] == '{': brace += 1
                                elif code[pos] == '}': brace -= 1
                                pos += 1
                            return code[start:pos-1]

                        before_body = extract_func_body(before_code, target_func)
                        after_body  = extract_func_body(after_code,  target_func)

                        if before_body is None and after_body is None:
                            st.error(f"❌ `{target_func}` not found in either file.")
                        elif before_body is None:
                            st.info(f"ℹ️ `{target_func}` is new in the after commit — no before CFG.")
                            out = os.path.join(results_dir, "cfg_func.png")
                            generate_cfg_image_ellipse(after_body, after_body,
                                               f"{target_func} (new)", out)
                            st.session_state.cfg_func_png = out
                        elif after_body is None:
                            st.info(f"ℹ️ `{target_func}` was removed in the after commit.")
                            out = os.path.join(results_dir, "cfg_func.png")
                            generate_cfg_image_ellipse(before_body, before_body,
                                               f"{target_func} (removed)", out)
                            st.session_state.cfg_func_png = out
                        else:
                            if before_body.strip() == after_body.strip():
                                st.warning(
                                    f"ℹ️ `{target_func}` has **not changed** "
                                    f"between before and after commits."
                                )
                                st.session_state.cfg_func_png = None
                            else:
                                out = os.path.join(results_dir, "cfg_func.png")
                                generate_cfg_image_ellipse(
                                    before_body, after_body,
                                    f"Differential CFG: {target_func}()", out
                                )
                                st.session_state.cfg_func_png = out
                                st.success(f"✅ CFG generated for `{target_func}`!")

                    except Exception as e:
                        st.error(f"❌ Error: {e}")

        if st.session_state.cfg_func_png and \
           os.path.exists(st.session_state.cfg_func_png):
            render_zoomable_image(st.session_state.cfg_func_png, height=900)
            with open(st.session_state.cfg_func_png, 'rb') as f:
                st.download_button(
                    label="⬇️ Download Function CFG", data=f,
                    file_name="cfg_func.png", mime="image/png",
                    key="dl_func_cfg"
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