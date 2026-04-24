#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// ─────────────────────────────────────────────
// Data structure
// ─────────────────────────────────────────────
#define MAX_ROWS 500   // CHANGED: increased from 100
#define MAX_COLS 20    // CHANGED: increased from 10

typedef struct {
    double data[MAX_ROWS][MAX_COLS];
    char   headers[MAX_COLS][64];  // ADDED: column headers
    int    rows;
    int    cols;
} Dataset;

// ─────────────────────────────────────────────
// Utility functions
// ─────────────────────────────────────────────

double computeMin(double* arr, int size) {
    double min = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] < min) min = arr[i];
    }
    return min;
}

double computeMax(double* arr, int size) {
    double max = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > max) max = arr[i];
    }
    return max;
}

double computeMean(double* arr, int size) {
    double sum = 0.0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum / size;
}

double computeVariance(double* arr, int size) {
    double mean = computeMean(arr, size);
    double variance = 0.0;
    for (int i = 0; i < size; i++) {
        double diff = arr[i] - mean;
        variance += diff * diff;
    }
    return variance / size;
}

// ADDED: new utility function
double computeStdDev(double* arr, int size) {
    return sqrt(computeVariance(arr, size));
}

// ADDED: new utility function
double computeMedian(double* arr, int size) {
    // Simple bubble sort to find median
    double temp[MAX_ROWS];
    for (int i = 0; i < size; i++) temp[i] = arr[i];
    for (int i = 0; i < size - 1; i++) {
        for (int j = 0; j < size - i - 1; j++) {
            if (temp[j] > temp[j+1]) {
                double swap = temp[j];
                temp[j] = temp[j+1];
                temp[j+1] = swap;
            }
        }
    }
    if (size % 2 == 0)
        return (temp[size/2 - 1] + temp[size/2]) / 2.0;
    else
        return temp[size/2];
}

// ─────────────────────────────────────────────
// CSV loader — MODIFIED: now reads headers
// ─────────────────────────────────────────────

int loadCSV(const char* filename, Dataset* dataset) {
    FILE* file = fopen(filename, "r");
    if (!file) {
        printf("Error: Cannot open file %s\n", filename);
        return -1;
    }

    char line[1024];
    dataset->rows = 0;
    dataset->cols = 0;

    // ADDED: read header row first
    if (fgets(line, sizeof(line), file)) {
        int col = 0;
        char* token = strtok(line, ",\n");
        while (token != NULL && col < MAX_COLS) {
            strncpy(dataset->headers[col], token, 63);
            col++;
            token = strtok(NULL, ",\n");
        }
        dataset->cols = col;
    }

    while (fgets(line, sizeof(line), file)) {
        int col = 0;
        char* token = strtok(line, ",");
        while (token != NULL && col < MAX_COLS) {
            dataset->data[dataset->rows][col] = atof(token);
            col++;
            token = strtok(NULL, ",");
        }
        dataset->rows++;
        if (dataset->rows >= MAX_ROWS) break;
    }

    fclose(file);
    return 0;
}

// ─────────────────────────────────────────────
// Analysis functions — MODIFIED: added stddev + median
// ─────────────────────────────────────────────

void analyzeColumn(Dataset* dataset, int colIndex) {
    if (colIndex >= dataset->cols) {
        printf("Error: Column index out of range\n");
        return;
    }

    double col[MAX_ROWS];
    for (int i = 0; i < dataset->rows; i++) {
        col[i] = dataset->data[i][colIndex];
    }

    double min    = computeMin(col, dataset->rows);
    double max    = computeMax(col, dataset->rows);
    double mean   = computeMean(col, dataset->rows);
    double variance = computeVariance(col, dataset->rows);
    double stddev = computeStdDev(col, dataset->rows);   // ADDED
    double median = computeMedian(col, dataset->rows);   // ADDED

    // MODIFIED: print header name if available
    if (strlen(dataset->headers[colIndex]) > 0)
        printf("Column '%s' Analysis:\n", dataset->headers[colIndex]);
    else
        printf("Column %d Analysis:\n", colIndex);

    printf("  Min:      %.4f\n", min);
    printf("  Max:      %.4f\n", max);
    printf("  Mean:     %.4f\n", mean);
    printf("  Median:   %.4f\n", median);   // ADDED
    printf("  Variance: %.4f\n", variance);
    printf("  StdDev:   %.4f\n", stddev);   // ADDED
}

void analyzeAllColumns(Dataset* dataset) {
    for (int i = 0; i < dataset->cols; i++) {
        analyzeColumn(dataset, i);
    }
}

// ─────────────────────────────────────────────
// Normalization — MODIFIED: added validation
// ─────────────────────────────────────────────

void normalizeColumn(Dataset* dataset, int colIndex) {
    if (colIndex >= dataset->cols) return;

    double col[MAX_ROWS];
    for (int i = 0; i < dataset->rows; i++) {
        col[i] = dataset->data[i][colIndex];
    }

    double min = computeMin(col, dataset->rows);
    double max = computeMax(col, dataset->rows);
    double range = max - min;

    if (range == 0.0) {
        printf("Warning: Column %d has zero range, skipping normalization\n", colIndex); // ADDED
        return;
    }

    for (int i = 0; i < dataset->rows; i++) {
        dataset->data[i][colIndex] = (dataset->data[i][colIndex] - min) / range;
    }
}

void normalizeDataset(Dataset* dataset) {
    for (int i = 0; i < dataset->cols; i++) {
        normalizeColumn(dataset, i);
    }
}

// ─────────────────────────────────────────────
// ADDED: Outlier detection
// ─────────────────────────────────────────────

void detectOutliers(Dataset* dataset, int colIndex) {
    if (colIndex >= dataset->cols) return;

    double col[MAX_ROWS];
    for (int i = 0; i < dataset->rows; i++) {
        col[i] = dataset->data[i][colIndex];
    }

    double mean   = computeMean(col, dataset->rows);
    double stddev = computeStdDev(col, dataset->rows);
    double threshold = 2.0 * stddev;

    printf("Outliers in column %d (beyond 2 stddev):\n", colIndex);
    int found = 0;
    for (int i = 0; i < dataset->rows; i++) {
        if (fabs(col[i] - mean) > threshold) {
            printf("  Row %d: %.4f\n", i, col[i]);
            found++;
        }
    }
    if (!found) printf("  None found\n");
}

// ─────────────────────────────────────────────
// Report generator — MODIFIED: added outlier section
// ─────────────────────────────────────────────

void printReport(Dataset* dataset) {
    printf("\n===== Dataset Report =====\n");
    printf("Rows: %d, Columns: %d\n", dataset->rows, dataset->cols);
    analyzeAllColumns(dataset);

    // ADDED: outlier detection for all columns
    printf("\n===== Outlier Report =====\n");
    for (int i = 0; i < dataset->cols; i++) {
        detectOutliers(dataset, i);
    }

    printf("==========================\n");
}

void generateReport(const char* filename) {
    Dataset dataset;
    int status = loadCSV(filename, &dataset);
    if (status != 0) {
        printf("Failed to load dataset\n");
        return;
    }
    normalizeDataset(&dataset);
    printReport(&dataset);
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <csv_file>\n", argv[0]);
        generateReport("sample.csv");
        return 0;
    }
    generateReport(argv[1]);
    return 0;
}