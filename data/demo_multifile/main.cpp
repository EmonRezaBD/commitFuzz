#include <stdio.h>
#include "math_utils.h"
#include "stats.h"

void runAnalysis(double* data, int size) {
    printf("=== Running Analysis ===\n");
    printStats(data, size);                       // CROSS-FILE → stats.cpp
    double s = computeSum(data, size);            // CROSS-FILE → math_utils.cpp
    printf("Sum: %.2f\n", s);
}

int main() {
    double data[] = {1.5, 2.3, 4.7, 5.1, 3.2, 6.8, 2.9};
    int size = 7;

    runAnalysis(data, size);  // local call

    return 0;
}