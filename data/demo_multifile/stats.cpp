#include <stdio.h>
#include <math.h>
#include "stats.h"
#include "math_utils.h"   // cross-file dependency

double computeVariance(double* arr, int size) {
    double mean = computeAverage(arr, size);   // CROSS-FILE call → math_utils.cpp
    double variance = 0.0;
    for (int i = 0; i < size; i++) {
        double diff = arr[i] - mean;
        variance += diff * diff;
    }
    return variance / size;
}

double computeStdDev(double* arr, int size) {
    double var = computeVariance(arr, size);
    return sqrt(var);
}

void printStats(double* arr, int size) {
    double avg = computeAverage(arr, size);    // CROSS-FILE call
    double maxV = computeMaxValue(arr, size);  // CROSS-FILE call
    double minV = computeMinValue(arr, size);  // CROSS-FILE call
    double sd  = computeStdDev(arr, size);

    printf("Average: %.2f\n", avg);
    printf("Max: %.2f\n", maxV);
    printf("Min: %.2f\n", minV);
    printf("StdDev: %.2f\n", sd);
}