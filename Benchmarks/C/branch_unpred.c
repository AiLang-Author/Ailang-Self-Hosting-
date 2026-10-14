#include <stdio.h>
int main() {
    long sum = 0;
    /* 64-bit multiply. A 32-bit i overflows and gcc -O3 deletes the loop. */
    for (long i = 0; i < 100000000L; i++) {
        if ((i * 1234567L) & 1)
            sum += 1;
        else
            sum -= 1;
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
