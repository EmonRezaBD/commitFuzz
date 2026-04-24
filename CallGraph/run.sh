#!/bin/bash
clang -S -emit-llvm $1 -o /home/rokon/commitFuzz/temp.bc
opt -load /home/rokon/commitFuzz/CallGraph/build/src/CallGraph/libCallGraph.so -callgraph /home/rokon/commitFuzz/temp.bc -f -enable-new-pm=0 -o /dev/null
