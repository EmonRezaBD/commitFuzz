# src/heatmap.py
# Risk Heatmap Generator
# Compares before/after C++ source files and visualizes line-by-line risk
#
# Theory:
# - Diff analysis: difflib (standard Python)
# - Risk scoring per line: McCabe 1976, Nagappan & Ball 2005
# - Color coding: red=high risk added, orange=medium, green=low, gray=deleted, white=unchanged

import difflib
import re
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch


# ============================================================
# PART 1: FILE LOADER
# ============================================================

def load_file(filepath):
    """Load a C++ file and return lines."""
    with open(filepath, 'r') as f:
        return f.readlines()


# ============================================================
# PART 2: LINE DIFF
# ============================================================

def compute_diff(before_lines, after_lines):
    """
    Use difflib to compute line-by-line diff.
    Returns list of (status, line_text) tuples.
    status: 'added', 'deleted', 'unchanged'
    """
    diff = list(difflib.ndiff(before_lines, after_lines))
    result = []
    for line in diff:
        if line.startswith('+ '):
            result.append(('added', line[2:].rstrip()))
        elif line.startswith('- '):
            result.append(('deleted', line[2:].rstrip()))
        elif line.startswith('  '):
            result.append(('unchanged', line[2:].rstrip()))
        # Skip '?' lines (difflib hints)
    return result


# ============================================================
# PART 3: LINE RISK SCORER
# ============================================================

def score_line(line):
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
    for pattern in high_risk_patterns:
        if re.search(pattern, line):
            score += 2

    for pattern in medium_risk_patterns:
        if re.search(pattern, line):
            score += 1

    # UPDATED thresholds
    if score >= 2:    # any control flow keyword = HIGH
        return 'HIGH'
    elif score >= 1:  # function call only = MEDIUM
        return 'MEDIUM'
    else:
        return 'LOW'


# ============================================================
# PART 4: COLOR MAPPING
# ============================================================

def get_line_color(status, risk_level):
    """
    Map line status + risk level to background color.
    - Added HIGH   → red
    - Added MEDIUM → orange
    - Added LOW    → light green
    - Deleted      → light gray with strikethrough effect
    - Unchanged    → white
    """
    if status == 'added':
        return {
            'HIGH':   '#ffcccc',   # red
            'MEDIUM': '#ffe0b2',   # orange
            'LOW':    '#ccffcc',   # green
        }.get(risk_level, '#ccffcc')
    elif status == 'deleted':
        return '#e0e0e0'           # gray
    else:
        return '#ffffff'           # white


def get_line_prefix(status):
    """Prefix symbol for each line status."""
    return {
        'added':     '+ ',
        'deleted':   '- ',
        'unchanged': '  ',
    }.get(status, '  ')


# ============================================================
# PART 5: VISUALIZER
# ============================================================

def visualize_heatmap(diff_result, title="Risk Heatmap", output_path=None):
    """
    Draw the risk heatmap as a source code viewer
    with colored lines based on risk level.
    """
    # Filter to show only relevant lines
    # (skip long unchanged blocks for readability)
    display_lines = []
    unchanged_count = 0

    for status, line in diff_result:
        if status == 'unchanged':
            unchanged_count += 1
            if unchanged_count <= 3:  # show max 3 consecutive unchanged lines
                display_lines.append((status, line, 'LOW'))
        else:
            unchanged_count = 0
            risk = score_line(line) if status == 'added' else 'LOW'
            display_lines.append((status, line, risk))

    if not display_lines:
        print("No diff lines to display.")
        return

    # Figure sizing
    n_lines = len(display_lines)
    fig_height = max(6, n_lines * 0.28)
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis('off')

    # Draw each line as a colored rectangle + text
    for i, (status, line, risk) in enumerate(display_lines):
        y = n_lines - i  # top to bottom

        # Background color
        bg_color = get_line_color(status, risk)

        # Draw background rectangle
        rect = FancyBboxPatch(
            (0, y - 0.5), 1, 1,
            boxstyle="square,pad=0",
            facecolor=bg_color,
            edgecolor='#dddddd',
            linewidth=0.3,
            transform=ax.transData
        )
        ax.add_patch(rect)

        # Line prefix (+ / - / space)
        prefix = get_line_prefix(status)

        # Risk badge for added lines
        badge = ''
        if status == 'added':
            badge = f' [{risk}]'

        # Truncate long lines
        display_text = line[:100] + '...' if len(line) > 100 else line

        # Text color
        text_color = '#cc0000' if status == 'deleted' else '#000000'

        ax.text(
            0.005, y,
            f"{prefix}{display_text}{badge}",
            fontsize=7,
            fontfamily='monospace',
            color=text_color,
            va='center',
            ha='left',
            transform=ax.transData
        )

    # Axis limits
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_lines + 1)

    # Title
    fig.suptitle(title, fontsize=13, fontweight='bold', y=1.01)

    # Legend
    legend_items = [
        mpatches.Patch(color='#ffcccc', label='Added - HIGH risk'),
        mpatches.Patch(color='#ffe0b2', label='Added - MEDIUM risk'),
        mpatches.Patch(color='#ccffcc', label='Added - LOW risk'),
        mpatches.Patch(color='#e0e0e0', label='Deleted'),
        mpatches.Patch(color='#ffffff', label='Unchanged'),
    ]
    fig.legend(handles=legend_items, loc='lower center',
               ncol=5, fontsize=9, frameon=True,
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")

    plt.close()


# ============================================================
# PART 6: SUMMARY STATS
# ============================================================

def print_summary(diff_result):
    """Print a summary of the diff and risk scores."""
    added = [(s, l) for s, l in diff_result if s == 'added']
    deleted = [(s, l) for s, l in diff_result if s == 'deleted']
    unchanged = [(s, l) for s, l in diff_result if s == 'unchanged']

    high   = [l for s, l in added if score_line(l) == 'HIGH']
    medium = [l for s, l in added if score_line(l) == 'MEDIUM']
    low    = [l for s, l in added if score_line(l) == 'LOW']

    print("\n===== Heatmap Summary =====")
    print(f"Total lines:     {len(diff_result)}")
    print(f"Added lines:     {len(added)}")
    print(f"Deleted lines:   {len(deleted)}")
    print(f"Unchanged lines: {len(unchanged)}")
    print(f"\nAdded line risk breakdown:")
    print(f"  HIGH   risk: {len(high)}")
    print(f"  MEDIUM risk: {len(medium)}")
    print(f"  LOW    risk: {len(low)}")

    if high:
        print(f"\nHigh risk lines to review:")
        for line in high[:5]:  # show top 5
            print(f"  >> {line.strip()[:80]}")
    print("===========================\n")


# ============================================================
# MAIN: Test on data_analyzer v1 vs v2
# ============================================================

if __name__ == "__main__":

    # Paths to before/after files
    before_path = "data/data_analyzer_V1.cpp"    # v1
    after_path  = "data/data_analyzer_V2.cpp" # v2

    print(f"Loading files...")
    print(f"  Before: {before_path}")
    print(f"  After:  {after_path}")

    # Load files
    before_lines = load_file(before_path)
    after_lines  = load_file(after_path)

    print(f"  Before: {len(before_lines)} lines")
    print(f"  After:  {len(after_lines)} lines")

    # Compute diff
    print("\nComputing diff...")
    diff_result = compute_diff(before_lines, after_lines)

    # Print summary
    print_summary(diff_result)

    # Generate heatmap
    print("Generating heatmap...")
    visualize_heatmap(
        diff_result=diff_result,
        title="Risk Heatmap: data_analyzer v1 → v2",
        output_path="results/heatmap.png"
    )

    print("Done! Check results/heatmap.png")