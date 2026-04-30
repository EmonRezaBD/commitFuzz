#!/bin/bash
# run_multifile.sh — Generate call graph for an entire C/C++ project
# Usage: ./run_multifile.sh <project_folder>

PROJECT_DIR=$1

if [ -z "$PROJECT_DIR" ]; then
    echo "Usage: ./run_multifile.sh <project_folder>"
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: '$PROJECT_DIR' is not a directory."
    exit 1
fi

# Resolve absolute path of CallGraph build (script lives in CallGraph/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIB_PATH="$SCRIPT_DIR/build/src/CallGraph/libCallGraph.so"

# Working directory for IR files
WORK_DIR=$(mktemp -d /tmp/commitfuzz_multifile.XXXXXX)
echo "Working directory: $WORK_DIR"

# Step 1: Compile every .cpp/.c/.cc file to LLVM IR
echo "[1/3] Compiling source files to LLVM IR..."
BC_FILES=()
for src in $(find "$PROJECT_DIR" -type f \( -name "*.cpp" -o -name "*.c" -o -name "*.cc" \)); do
    base=$(basename "$src")
    bc_file="$WORK_DIR/${base%.*}.bc"
    echo "  - $src"
    clang -S -emit-llvm -I"$PROJECT_DIR" "$src" -o "$bc_file" 2>/dev/null
    if [ $? -eq 0 ] && [ -f "$bc_file" ]; then
        BC_FILES+=("$bc_file")
    else
        echo "    WARNING: failed to compile $src — skipping"
    fi
done

if [ ${#BC_FILES[@]} -eq 0 ]; then
    echo "Error: No files compiled successfully."
    exit 1
fi

# Step 2: Link all .bc files into one whole-program IR
echo "[2/3] Linking ${#BC_FILES[@]} IR files..."
MERGED_BC="$WORK_DIR/merged.bc"
llvm-link "${BC_FILES[@]}" -o "$MERGED_BC" 2>/dev/null

if [ ! -f "$MERGED_BC" ]; then
    echo "Error: llvm-link failed."
    exit 1
fi

# Step 3: Run the CallGraph pass on merged IR
echo "[3/3] Running CallGraph pass..."
opt -load "$LIB_PATH" -callgraph "$MERGED_BC" -f -enable-new-pm=0 -o /dev/null

echo ""
echo "Done! Output files:"
echo "  - graph.dot   (graphviz format)"
echo "  - graph.text  (raw call relationships)"