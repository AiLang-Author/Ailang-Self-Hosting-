#include <stdio.h>
#include <stdlib.h>
int main() {
    int size = 10000000;
    long *arr = malloc(size * sizeof(long));
    for (int i = 0; i < size; i++) arr[i] = i;
    long sum = 0;
    for (int pass = 0; pass < 10; pass++) {
        for (int i = 0; i < size; i += 16)
            sum += arr[i];
    }
    printf("Sum: %ld\n", sum);
    free(arr);
    return 0;
}
