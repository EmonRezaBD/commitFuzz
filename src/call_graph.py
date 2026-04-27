import re
import networkx as nx
import matplotlib.pyplot as plt

# Load the C++ file
with open("D:\\SEProject\\Data-Analyzer\\FirstDialog.cpp", "r") as f: # Change the path to your file [rokon add] #data-analyzer
# with open("D:\\SEProject\\qBittorrent\\src\\gui\\rss\\feedlistwidget.cpp", "r") as f: # Change the path to your file [change]
# with open("D:\\SEProject\\FFmpeg\\libavdevice\\jack.c", "r") as f: # Change the path to your file [change]
    code = f.read()

#**Step 2: Extract function bodies**
def extract_function_bodies(code):
    """Extract all function definitions and their bodies"""
    functions = {}
    
    # Match: returnType ClassName::functionName(params) {
    # pattern = r'(\w+)\s+\w+::(\w+)\s*\([^)]*\)\s*\{'
    
    # for match in re.finditer(pattern, code):
    #     func_name = match.group(2)
    #     start = match.end()  # position after opening {
        
    #     # Find matching closing } by counting braces
    #     brace_count = 1
    #     pos = start
    #     while pos < len(code) and brace_count > 0:
    #         if code[pos] == '{':
    #             brace_count += 1
    #         elif code[pos] == '}':
    #             brace_count -= 1
    #         pos += 1
        
    #     body = code[start:pos-1]
    #     functions[func_name] = body

    #Handle c and cpp both functions
     # Match C++ style: returnType ClassName::functionName(params) {
    # Match C style:   returnType functionName(params) {
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

# Test it
functions = extract_function_bodies(code)
print(f"Found {len(functions)} functions:")
for name in functions:
    print(f"  - {name}")

"""
After this step, I check manually with Visual Studio and total 12 functions were found in the file. The output is:
Found 12 functions:
  - DoDataExchange
  - OnInitDialog
  - OnPaint
  - OnContextMenu
  - OnCbnSelchangeCombo1
  - OnCbnSelchangeCombo2
  - generateGraph
  - OnBnClickedExportgraphbtn
  - insertInCombo
  - CopyValues
  - OnExportdataExportgraph
  - OnBnClickedExportPdf
  """

#Step 3: Extract explicit calls from a function body
def extract_calls(body):
    """Extract explicit function calls from a function body"""
    # Match: functionName( or object.functionName( or object->functionName(
    pattern = r'(?:\.|\->)?\s*(\w+)\s*\('
    
    raw_calls = re.findall(pattern, body)
    
    # Filter out C++ keywords (not function calls)
    keywords = {'if', 'for', 'while', 'switch', 'catch', 'return',
                'else', 'auto', 'new', 'delete', 'sizeof', 'typeof'}
    
    calls = [c for c in raw_calls if c not in keywords]
    
    # Return unique calls
    return list(set(calls))

# Test on insertInCombo
# target = "audio_read_header" #FFmpeg
# target = "handleItemAboutToBeRemoved" # Need to change the target manually based on the function we want to analyze #qBittorrent
target = "generateGraph" # Need to change the target manually based on the function we want to analyze [rokon add]#data-analyzer
body = functions[target]
calls = extract_calls(body)
print(f"\n{target} calls: {calls}")

"""
Calls From: Visual Studio:
insertInCombo calls: ['AddString', 'ResetContent']
So, it matches with the output of the code. The output is:
insertInCombo calls: ['AddString', 'ResetContent']
"""

#Step 4: Find who calls the target function (incoming calls)
def find_callers(functions, target_name):
    """Find which functions call the target function"""
    callers = []
    for func_name, body in functions.items():
        if func_name == target_name:
            continue
        # Check if target is called in this function's body
        if re.search(r'\b' + target_name + r'\s*\(', body):
            callers.append(func_name)
    return callers

callers = find_callers(functions, target)
print(f"\nCalled by: {callers}")

""" 
Manually checking with Visual Studio, the output is:
Called by: ['CopyValues']
"""

#Step 5: Visualize with networkx
def render_callgraph_tab(cpp_path, file_label, project_root, results_dir):

    st.header("Call Graph Analysis")
    st.write("Static call graph generated from source file analysis.")

    if file_label:
        st.info(f"Selected file: `{file_label}`")
    else:
        st.warning("Upload a C/C++ file in the sidebar or enable sample files.")

    if 'callgraph_fig' not in st.session_state:
        st.session_state.callgraph_fig = None
    if 'callgraph_df' not in st.session_state:
        st.session_state.callgraph_df = None

    if st.button("Generate Call Graph", type="primary"):
        if cpp_path is None:
            st.error("No file selected.")
        else:
            with open(cpp_path, 'r', errors='ignore') as f:
                code = f.read()

            functions = extract_function_bodies(code)

            if not functions:
                st.error("No functions found in this file.")
            else:
                # Build full graph across all functions
                G = nx.DiGraph()
                for func_name, body in functions.items():
                    G.add_node(func_name)
                    calls = extract_calls(body)
                    for callee in calls:
                        if callee in functions:
                            G.add_edge(func_name, callee)

                # Store graph stats
                rows = []
                for node in G.nodes():
                    rows.append({
                        "Function": node,
                        "Fan-Out": G.out_degree(node),
                        "Fan-In":  G.in_degree(node),
                        "Calls": ", ".join(list(G.successors(node))) or "none"
                    })
                df = pd.DataFrame(rows).sort_values("Fan-Out", ascending=False).reset_index(drop=True)

                threshold_fanout = df["Fan-Out"].quantile(0.75)
                threshold_fanin  = df["Fan-In"].quantile(0.75)

                def flag_risk(row):
                    if row["Fan-Out"] >= threshold_fanout and row["Fan-Out"] > 0:
                        return "High complexity"
                    if row["Fan-In"] >= threshold_fanin and row["Fan-In"] > 0:
                        return "High impact"
                    return ""

                df["Note"] = df.apply(flag_risk, axis=1)
                st.session_state.callgraph_df = df

                # Draw graph
                color_map = []
                for node in G.nodes():
                    out_d = G.out_degree(node)
                    in_d  = G.in_degree(node)
                    if out_d >= threshold_fanout and out_d > 0:
                        color_map.append('#ff9900')
                    elif in_d >= threshold_fanin and in_d > 0:
                        color_map.append('#4488ff')
                    else:
                        color_map.append('#aaddaa')

                fig, ax = plt.subplots(figsize=(12, 7))
                pos = nx.spring_layout(G, seed=42)
                nx.draw(G, pos, ax=ax,
                        node_color=color_map,
                        node_size=2000,
                        with_labels=True,
                        font_size=8,
                        arrowstyle='-|>',
                        arrowsize=20,
                        edge_color='gray')

                import matplotlib.patches as mpatches
                legend = [
                    mpatches.Patch(color='#ff9900', label='High fan-out (complex)'),
                    mpatches.Patch(color='#4488ff', label='High fan-in (critical)'),
                    mpatches.Patch(color='#aaddaa', label='Normal'),
                ]
                fig.legend(handles=legend, loc='lower center', ncol=3,
                           fontsize=9, bbox_to_anchor=(0.5, -0.02))
                plt.tight_layout()
                st.session_state.callgraph_fig = fig
                st.success("Call graph generated.")

    if st.session_state.callgraph_fig is not None:
        st.pyplot(st.session_state.callgraph_fig)

        df = st.session_state.callgraph_df
        if df is not None:
            st.divider()
            st.subheader("Function Call Summary")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Functions",  len(df))
            m2.metric("Total Call Edges", int(df["Fan-Out"].sum()))
            m3.metric("Max Fan-Out",      int(df["Fan-Out"].max()))
            m4.metric("Max Fan-In",       int(df["Fan-In"].max()))

            st.divider()
            st.dataframe(
                df[["Function", "Fan-Out", "Fan-In", "Calls", "Note"]],
                use_container_width=True,
                hide_index=True
            )

    st.divider()
    with st.expander("About this analysis"):
        st.markdown("""
**What is a call graph?**
A directed graph where each node is a function and each edge represents a function call.

**Fan-Out:** Number of functions this function calls. High fan-out means complex logic, harder to test in isolation.

**Fan-In:** Number of functions that call this function. High fan-in means a bug here affects many callers.

**Color coding:**
- Orange: high fan-out, complex functions
- Blue: high fan-in, critical functions  
- Green: normal functions
        """)