#include <stdio.h>

__attribute__((noinline)) int add(int a, int b) {
    return a + b;
}

int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        sum += add(i, 1);
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
