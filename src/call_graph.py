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
def draw_call_graph(target, outgoing_calls, incoming_calls):
    """Draw a call graph centered on the target function"""
    G = nx.DiGraph()
    
    # Add target node
    G.add_node(target)
    
    # Add outgoing edges (target calls these)
    for callee in outgoing_calls:
        G.add_edge(target, callee)
    
    # Add incoming edges (these call target)
    for caller in incoming_calls:
        G.add_edge(caller, target)
    
    # Color coding
    color_map = []
    for node in G.nodes():
        if node == target:
            color_map.append('orange')      # target function
        elif node in incoming_calls:
            color_map.append('lightblue')   # callers
        else:
            color_map.append('lightgreen')  # callees
    
    # Draw
    plt.figure(figsize=(10, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos,
            node_color=color_map,
            node_size=2000,
            with_labels=True,
            font_size=9,
            arrowstyle='-|>',
            arrowsize=20,
            edge_color='gray')
    
    plt.title(f"Call Graph for {target}()")
    plt.tight_layout()
    plt.savefig("results/call_graph.png", dpi=150)
    plt.show()
    print("Saved to results/call_graph.png")

draw_call_graph(target, calls, callers)
