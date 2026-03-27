# src/cfg_combined.py
# Combines: cfg_generator.py + cfg_differ.py + cfg_visualizer.py

import re
import json
import os
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ============================================================
# PART 1: CFG GENERATOR
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


# ============================================================
# PART 2: CFG DIFFER
# ============================================================

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
            if before_code == after_code:
                result['before_status'][nid] = 'unchanged'
            else:
                result['before_status'][nid] = 'modified'

    for nid in after_ids:
        if nid not in before_ids:
            result['after_status'][nid] = 'added'
        else:
            before_code = before_nodes[nid]['code'].strip()
            after_code  = after_nodes[nid]['code'].strip()
            if before_code == after_code:
                result['after_status'][nid] = 'unchanged'
            else:
                result['after_status'][nid] = 'modified'

    return result


def get_node_color(status):
    """Map diff status to display color."""
    return {
        'unchanged': '#aaaaaa',
        'modified':  '#ff9900',
        'deleted':   '#ff4444',
        'added':     '#44bb44',
    }.get(status, '#aaaaaa')


# ============================================================
# PART 3: CFG VISUALIZER
# ============================================================

def draw_cfg(ax, G, status_map, title):
    """Draw a single CFG on a matplotlib axis with colored nodes."""
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

    node_colors = [get_node_color(status_map.get(n, 'unchanged'))
                   for n in G.nodes()]

    labels = {n: f"B{n}\n{get_block_label(d['code'], 25)}"
              for n, d in G.nodes(data=True)}

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=1800, alpha=0.9)
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                            font_size=6, font_color='white', font_weight='bold')
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                           arrowsize=20, edge_color='#555555',
                           connectionstyle='arc3,rad=0.1')

    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=6, font_color='#333333')

    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.axis('off')


def visualize_diff(before_code, after_code, title="Differential CFG",
                   output_path=None):
    """Generate side-by-side before/after CFG diff visualization."""
    cfg_before = build_cfg(before_code)
    cfg_after  = build_cfg(after_code)
    diff       = diff_cfgs(cfg_before, cfg_after)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
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

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")

    plt.close()
    return fig


# ============================================================
# MAIN: Run on dataset
# ============================================================

if __name__ == "__main__":
    with open('data/singleFuncDataset.jsonl', 'r') as f:
        entry = json.loads(f.readline())

    before = entry['Before_commit_codebase']
    after  = entry['After_commit_codebase']

    # Test CFG generation
    cfg_before = build_cfg(before)
    cfg_after  = build_cfg(after)
    print(f"Before: {cfg_before.number_of_nodes()} nodes")
    print(f"After:  {cfg_after.number_of_nodes()} nodes")

    # Test diff
    diff = diff_cfgs(cfg_before, cfg_after)
    print("\n=== BEFORE node statuses ===")
    for nid, status in diff['before_status'].items():
        code = cfg_before.nodes[nid]['code'][:40].replace('\n', ' ')
        print(f"  Block {nid} [{status}]: {code}")

    print("\n=== AFTER node statuses ===")
    for nid, status in diff['after_status'].items():
        code = cfg_after.nodes[nid]['code'][:40].replace('\n', ' ')
        print(f"  Block {nid} [{status}]: {code}")

    # Test visualization
    visualize_diff(
        before_code=before,
        after_code=after,
        title=entry['Commit title'],
        output_path='results/cfg_diff_entry0.png'
    )

    print("\nAll done! Check results/cfg_diff_entry0.png")