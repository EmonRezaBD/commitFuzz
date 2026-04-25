# src/tabs/tab_insights.py
# Tab 5: Actionable Insights

import os
import re
import difflib
import streamlit as st


# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================

def count_decision_points(code):
    keywords = r'\b(if|else|for|while|switch|case|catch)\b'
    operators = re.findall(r'(\&\&|\|\||\?)', code)
    return len(re.findall(keywords, code)) + len(operators)


def get_high_risk_lines(before_code, after_code):
    """Return added lines with HIGH risk (control flow keywords)."""
    before_lines = before_code.splitlines()
    after_lines  = after_code.splitlines()
    diff = list(difflib.ndiff(before_lines, after_lines))

    high_risk = []
    medium_risk = []

    high_patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b',
                     r'\bswitch\b', r'\bcatch\b', r'\&\&', r'\|\|']
    medium_patterns = [r'\w+\s*\(', r'\bnew\b', r'\bdelete\b',
                       r'\bmalloc\b', r'\bfree\b']

    for line in diff:
        if not line.startswith('+ '):
            continue
        text = line[2:].strip()
        score = sum(2 for p in high_patterns if re.search(p, text))
        score += sum(1 for p in medium_patterns if re.search(p, text))

        if score >= 2:
            high_risk.append(text)
        elif score >= 1:
            medium_risk.append(text)

    return high_risk[:8], medium_risk[:8]


def get_new_functions(before_code, after_code):
    """Detect newly added function definitions."""
    func_pattern = r'(?:\w+[\s\*]+)(?:\w+::)?(\w+)\s*\([^)]*\)\s*\{'

    before_funcs = set(re.findall(func_pattern, before_code))
    after_funcs  = set(re.findall(func_pattern, after_code))

    added   = after_funcs - before_funcs
    removed = before_funcs - after_funcs
    return list(added), list(removed)


def get_complexity_info(before_code, after_code):
    """Return CC before, after, delta."""
    before_cc = count_decision_points(before_code)
    after_cc  = count_decision_points(after_code)
    return before_cc, after_cc, after_cc - before_cc


def get_change_stats(before_code, after_code):
    """Return added/deleted line counts."""
    before_lines = before_code.splitlines()
    after_lines  = after_code.splitlines()
    diff = list(difflib.ndiff(before_lines, after_lines))
    added   = sum(1 for l in diff if l.startswith('+ '))
    deleted = sum(1 for l in diff if l.startswith('- '))
    return added, deleted


def generate_checklist(before_code, after_code, risk_level):
    """
    Generate a review checklist based on what changed.
    Tailored to the specific type of changes detected.
    """
    checklist = []
    high_lines, _ = get_high_risk_lines(before_code, after_code)
    added_funcs, removed_funcs = get_new_functions(before_code, after_code)
    before_cc, after_cc, delta = get_complexity_info(before_code, after_code)
    added, deleted = get_change_stats(before_code, after_code)

    # Always include
    checklist.append({
        'category': '🔍 General Review',
        'items': [
            "Review all added lines for correctness and edge cases",
            "Ensure the commit does not break existing functionality",
            "Verify the change is consistent with the codebase style",
        ]
    })

    # Complexity-related
    if delta > 0:
        checklist.append({
            'category': '🔀 Control Flow Changes',
            'items': [
                f"Cyclomatic complexity increased by {delta:+d} — verify all new branches are tested",
                "Check all new if/else branches for boundary conditions",
                "Ensure loop termination conditions are correct",
                "Verify no infinite loop risk was introduced",
            ]
        })

    # New functions added
    if added_funcs:
        checklist.append({
            'category': '➕ New Functions Added',
            'items': [
                f"New function(s) detected: {', '.join(added_funcs)}",
                "Ensure new functions have proper input validation",
                "Check return values and error handling",
                "Add unit tests for each new function",
            ]
        })

    # Functions removed
    if removed_funcs:
        checklist.append({
            'category': '➖ Functions Removed',
            'items': [
                f"Removed function(s): {', '.join(removed_funcs)}",
                "Verify no other code depends on the removed functions",
                "Check for dangling references or broken call chains",
            ]
        })

    # Memory-related
    if re.search(r'\b(malloc|free|new|delete)\b', after_code):
        checklist.append({
            'category': '🧠 Memory Management',
            'items': [
                "Check all malloc/new calls have corresponding free/delete",
                "Verify no memory leak was introduced in new code paths",
                "Check pointer validity before dereferencing",
                "Ensure no double-free scenario exists",
            ]
        })

    # HIGH risk level specific
    if risk_level == 'HIGH':
        checklist.append({
            'category': '🚨 High Risk — Priority Review',
            'items': [
                "This commit scores HIGH risk — prioritize for code review",
                "Consider fuzzing the modified function for pathological inputs",
                "Run regression tests before merging",
                "Request senior developer review before approval",
            ]
        })

    # Large change
    if added + deleted > 50:
        checklist.append({
            'category': '📦 Large Change',
            'items': [
                f"{added} lines added, {deleted} lines deleted — consider splitting into smaller commits",
                "Large changes are harder to review — ensure thorough testing",
            ]
        })

    return checklist


def suggest_reviewers(before_code, after_code):
    """Suggest reviewer types based on what changed."""
    suggestions = []

    if re.search(r'\b(malloc|free|new|delete|ptr|pointer)\b', after_code):
        suggestions.append(("Memory Safety Expert",
                            "Changes involve memory allocation/deallocation"))

    if re.search(r'\b(if|for|while|switch)\b',
                 '\n'.join([l for l in difflib.ndiff(
                     before_code.splitlines(),
                     after_code.splitlines()
                 ) if l.startswith('+ ')])):
        suggestions.append(("Algorithm Reviewer",
                            "Control flow logic was modified"))

    _, removed = get_new_functions(before_code, after_code)
    if removed:
        suggestions.append(("API Compatibility Reviewer",
                            "Functions were removed — check for breaking changes"))

    added, _ = get_new_functions(before_code, after_code)
    if added:
        suggestions.append(("Unit Test Reviewer",
                            "New functions added — need test coverage"))

    if not suggestions:
        suggestions.append(("General Reviewer",
                            "Standard code review recommended"))

    return suggestions


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_insights_tab(before_path, after_path,
                        before_label, after_label,
                        results_dir):
    """Main render function called from dashboard.py"""

    st.header("💡 Actionable Insights")
    st.write("Tailored review checklist and recommendations based on detected code changes.")

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
    if 'insights_data' not in st.session_state:
        st.session_state.insights_data = None

    # Analyze button
    if st.button("🚀 Generate Insights", type="primary"):
        if not before_path or not after_path:
            st.error("Please provide both before and after files.")
        else:
            with st.spinner("Analyzing changes..."):
                try:
                    with open(before_path, 'r') as f:
                        before_code = f.read()
                    with open(after_path, 'r') as f:
                        after_code = f.read()

                    # Compute risk level
                    from tabs.tab_riskscore import compute_risk_score
                    metrics    = compute_risk_score(before_code, after_code)
                    risk_level = metrics['risk_level']
                    risk_score = metrics['risk_score']

                    checklist     = generate_checklist(before_code, after_code, risk_level)
                    reviewers     = suggest_reviewers(before_code, after_code)
                    high_lines, _ = get_high_risk_lines(before_code, after_code)
                    added_f, removed_f = get_new_functions(before_code, after_code)
                    before_cc, after_cc, delta = get_complexity_info(before_code, after_code)

                    st.session_state.insights_data = {
                        'checklist':   checklist,
                        'reviewers':   reviewers,
                        'high_lines':  high_lines,
                        'added_f':     added_f,
                        'removed_f':   removed_f,
                        'before_cc':   before_cc,
                        'after_cc':    after_cc,
                        'delta':       delta,
                        'risk_level':  risk_level,
                        'risk_score':  risk_score,
                    }
                    st.success("✅ Insights generated successfully!")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Display results
    if st.session_state.insights_data:
        d = st.session_state.insights_data

        st.divider()

        # Risk summary banner
        color_map = {'LOW': '🟢', 'MEDIUM': '🟠', 'HIGH': '🔴'}
        emoji = color_map.get(d['risk_level'], '⚪')
        st.markdown(
            f"### {emoji} Risk Level: **{d['risk_level']}** "
            f"(Score: `{d['risk_score']}`)"
        )

        st.divider()

        # Two columns: checklist + reviewer suggestions
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("✅ Review Checklist")
            for section in d['checklist']:
                with st.expander(section['category'], expanded=True):
                    for item in section['items']:
                        st.checkbox(item, key=f"chk_{item[:40]}")

        with col2:
            st.subheader("👥 Suggested Reviewers")
            for role, reason in d['reviewers']:
                st.markdown(f"**{role}**")
                st.caption(reason)
                st.divider()

        st.divider()

        # Change summary
        st.subheader("📊 Change Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CC Before",    d['before_cc'])
        c2.metric("CC After",     d['after_cc'])
        c3.metric("CC Delta",     f"{d['delta']:+d}")
        c4.metric("New Functions", len(d['added_f']))

        # High risk lines
        if d['high_lines']:
            st.divider()
            st.subheader("🔴 Lines Requiring Careful Inspection")
            for line in d['high_lines']:
                st.code(line, language='cpp')

        # New / removed functions
        if d['added_f'] or d['removed_f']:
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if d['added_f']:
                    st.subheader("➕ New Functions")
                    for f in d['added_f']:
                        st.markdown(f"- `{f}()`")
            with col2:
                if d['removed_f']:
                    st.subheader("➖ Removed Functions")
                    for f in d['removed_f']:
                        st.markdown(f"- `{f}()`")

    # Info box
    with st.expander("ℹ️ About Actionable Insights"):
        st.markdown("""
        **What are Actionable Insights?**
        Automatically generated review guidance based on what specifically changed in the commit.

        **How checklist is generated:**
        - Detects new/removed functions → adds function-specific checks
        - Detects memory operations → adds memory safety checks
        - Detects control flow changes → adds branch/loop checks
        - Adjusts priority based on overall risk score

        **Suggested reviewers** are based on the type of changes:
        - Memory changes → Memory Safety Expert
        - Control flow changes → Algorithm Reviewer
        - Removed functions → API Compatibility Reviewer
        - New functions → Unit Test Reviewer
        """)