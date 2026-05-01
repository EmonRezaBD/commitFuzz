# CommitLens

A commit-level risk scoring and visualization framework for C/C++ projects. Predicts bug introduction risk from code changes using static analysis.

---

## Features

- **Call Graph** — LLVM-based static call graph (single file + multi-file project)
- **Differential CFG** — Side-by-side control flow graph comparison
- **Risk Heatmap** — Line-by-line risk visualization of code changes
- **Risk Score** — Quantified risk using 3 established metrics
- **Actionable Insights** — Auto-generated review checklist

---

## Requirements

- Ubuntu 20.04+
- Python 3.8+
- LLVM/Clang 13+
- Graphviz

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/EmonRezaBD/commitFuzz.git
cd commitFuzz
```

**2. Install system dependencies**
```bash
sudo apt update
sudo apt install -y clang llvm graphviz python3-dev python3-venv \
                   libgraphviz-dev cmake
```

**3. Build the LLVM CallGraph pass**
```bash
cd CallGraph
mkdir build && cd build
cmake ..
make
cd ../..
chmod +x CallGraph/run.sh CallGraph/run_multifile.sh
```

**4. Set up Python environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pygraphviz
```

---

## Usage

**Run the dashboard**
```bash
source venv/bin/activate
streamlit run src/dashboard.py
```
Opens at `http://localhost:8501`

**Sample files** are included in `data/` — enable "Use sample files" checkbox to test instantly.

---

## Multi-File Call Graph Workflow

For multi-file C/C++ projects, CommitFuzz captures cross-file function calls using LLVM whole-program analysis.

**Pipeline:**
```
Project folder
      │
      ▼
clang -emit-llvm  (per file)
      │
      ▼
.bc files (LLVM IR)
      │
      ▼
llvm-link  → merged.bc
      │
      ▼
opt -load libCallGraph.so
      │
      ▼
graph.dot + graph.text
      │
      ▼
c++filt (demangle) + dot -Tpng
      │
      ▼
callgraph.png
```

**Steps:**
1. Each `.cpp/.c` file in the folder is compiled to LLVM IR (`.bc`)
2. All `.bc` files merged into one whole-program IR via `llvm-link`
3. CallGraph LLVM pass extracts cross-file call relationships
4. C++ mangled names are demangled with `c++filt`
5. Graphviz renders the final PNG

**Try the demo:**
```bash
./CallGraph/run_multifile.sh data/demo_multifile
```
Or enter the path `data/demo_multifile` in the Call Graph tab → Section 3.

> Production projects with complex build systems (e.g. FFmpeg, OpenCV) require `compile_commands.json` integration via Bear — a known prerequisite for all LLVM-based static analyzers including Clang-Tidy.

---

## References

- McCabe (1976) — Cyclomatic Complexity
- Nagappan & Ball (2005) — Code Churn & Defect Density
- Moser et al. (2008) — Change Metrics for Defect Prediction
- LLVM CallGraph pass: [bernardnongpoh/CallGraph](https://github.com/bernardnongpoh/CallGraph)
