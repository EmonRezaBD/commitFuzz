#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ─────────────────────────────────────────────
// Data structure
// ─────────────────────────────────────────────
#define MAX_ROWS 100
#define MAX_COLS 10

typedef struct {
    double data[MAX_ROWS][MAX_COLS];
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

// ─────────────────────────────────────────────
// CSV loader
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

    while (fgets(line, sizeof(line), file)) {
        int col = 0;
        char* token = strtok(line, ",");
        while (token != NULL && col < MAX_COLS) {
            dataset->data[dataset->rows][col] = atof(token);
            col++;
            token = strtok(NULL, ",");
        }
        if (dataset->cols == 0) dataset->cols = col;
        dataset->rows++;
        if (dataset->rows >= MAX_ROWS) break;
    }

    fclose(file);
    return 0;
}

// ─────────────────────────────────────────────
// Analysis functions
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

    double min      = computeMin(col, dataset->rows);
    double max      = computeMax(col, dataset->rows);
    double mean     = computeMean(col, dataset->rows);
    double variance = computeVariance(col, dataset->rows);

    printf("Column %d Analysis:\n", colIndex);
    printf("  Min:      %.4f\n", min);
    printf("  Max:      %.4f\n", max);
    printf("  Mean:     %.4f\n", mean);
    printf("  Variance: %.4f\n", variance);
}

void analyzeAllColumns(Dataset* dataset) {
    for (int i = 0; i < dataset->cols; i++) {
        analyzeColumn(dataset, i);
    }
}

// ─────────────────────────────────────────────
// Normalization
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

    if (range == 0.0) return;

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
// Report generator
// ─────────────────────────────────────────────

void printReport(Dataset* dataset) {
    printf("\n===== Dataset Report =====\n");
    printf("Rows: %d, Columns: %d\n", dataset->rows, dataset->cols);
    analyzeAllColumns(dataset);
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
        generateReport("sample.csv"); // default test
        return 0;
    }
    generateReport(argv[1]);
    return 0;
}
