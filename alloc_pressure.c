#include <stdio.h>
#include <stdlib.h>
int main() {
    long sum = 0;
    for (int i = 0; i < 1000000; i++) {
        long *p = malloc(64);
        *p = i;
        sum += *p;
        free(p);
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
