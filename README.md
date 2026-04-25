# CommitFuzz

A commit-level risk scoring and visualization framework for C/C++ projects. Predicts bug introduction risk from code changes using static analysis.

---

## Features

- **Call Graph** — LLVM-based static call graph generation
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