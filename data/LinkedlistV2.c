#include <stdio.h>
#include <stdlib.h>

// ─────────────────────────────────────────────
// Simple Linked List - Version 2 (After Commit)
// Changes: added searchNode, reverseList, sortList
// ─────────────────────────────────────────────

typedef struct Node {
    int data;
    struct Node* next;
} Node;

typedef struct {
    Node* head;
    int size;
} LinkedList;

// ─────────────────────────────────────────────
// Core functions
// ─────────────────────────────────────────────

Node* createNode(int data) {
    Node* node = (Node*)malloc(sizeof(Node));
    node->data = data;
    node->next = NULL;
    return node;
}

void insertFront(LinkedList* list, int data) {
    Node* node = createNode(data);
    node->next = list->head;
    list->head = node;
    list->size++;
}

void insertEnd(LinkedList* list, int data) {
    Node* node = createNode(data);
    if (list->head == NULL) {
        list->head = node;
    } else {
        Node* curr = list->head;
        while (curr->next != NULL) {
            curr = curr->next;
        }
        curr->next = node;
    }
    list->size++;
}

void deleteNode(LinkedList* list, int data) {
    Node* curr = list->head;
    Node* prev = NULL;
    while (curr != NULL) {
        if (curr->data == data) {
            if (prev == NULL) {
                list->head = curr->next;
            } else {
                prev->next = curr->next;
            }
            free(curr);
            list->size--;
            return;
        }
        prev = curr;
        curr = curr->next;
    }
}

void printList(LinkedList* list) {
    Node* curr = list->head;
    printf("List: ");
    while (curr != NULL) {
        printf("%d ", curr->data);
        curr = curr->next;
    }
    printf("\n");
}

void freeList(LinkedList* list) {
    Node* curr = list->head;
    while (curr != NULL) {
        Node* next = curr->next;
        free(curr);
        curr = next;
    }
    list->head = NULL;
    list->size = 0;
}

// ─────────────────────────────────────────────
// ADDED: Search function
// ─────────────────────────────────────────────

Node* searchNode(LinkedList* list, int data) {
    Node* curr = list->head;
    while (curr != NULL) {
        if (curr->data == data) {
            return curr;
        }
        curr = curr->next;
    }
    return NULL;
}

// ─────────────────────────────────────────────
// ADDED: Reverse function
// ─────────────────────────────────────────────

void reverseList(LinkedList* list) {
    Node* prev = NULL;
    Node* curr = list->head;
    Node* next = NULL;
    while (curr != NULL) {
        next = curr->next;
        curr->next = prev;
        prev = curr;
        curr = next;
    }
    list->head = prev;
}

// ─────────────────────────────────────────────
// ADDED: Sort function (bubble sort)
// ─────────────────────────────────────────────

void sortList(LinkedList* list) {
    if (list->head == NULL) return;
    int swapped;
    Node* curr;
    Node* last = NULL;
    do {
        swapped = 0;
        curr = list->head;
        while (curr->next != last) {
            if (curr->data > curr->next->data) {
                int temp = curr->data;
                curr->data = curr->next->data;
                curr->next->data = temp;
                swapped = 1;
            }
            curr = curr->next;
        }
        last = curr;
    } while (swapped);
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

int main() {
    LinkedList list;
    list.head = NULL;
    list.size = 0;

    insertEnd(&list, 10);
    insertEnd(&list, 20);
    insertFront(&list, 5);
    printList(&list);
    deleteNode(&list, 20);
    printList(&list);

    // ADDED: test new functions
    insertEnd(&list, 99);
    insertEnd(&list, 3);
    insertEnd(&list, 42);
    sortList(&list);
    printList(&list);
    reverseList(&list);
    printList(&list);

    Node* found = searchNode(&list, 42);
    if (found != NULL) {
        printf("Found: %d\n", found->data);
    } else {
        printf("Not found\n");
    }

    freeList(&list);
    return 0;
}