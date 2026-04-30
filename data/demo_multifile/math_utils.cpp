#include "math_utils.h"

double computeSum(double* arr, int size) {
    double sum = 0.0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}

double computeAverage(double* arr, int size) {
    double total = computeSum(arr, size);   // calls computeSum
    return total / size;
}

double computeMaxValue(double* arr, int size) {
    double maxVal = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > maxVal) maxVal = arr[i];
    }
    return maxVal;
}

double computeMinValue(double* arr, int size) {
    double minVal = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] < minVal) minVal = arr[i];
    }
    return minVal;
}