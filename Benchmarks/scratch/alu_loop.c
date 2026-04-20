#include <stdio.h>
int main() {
    long a = 1, b = 2, c = 3;
    for (long i = 0; i < 500000000L; i++) {
        a = a + b;
        b = b + c;
        c = c + a;
    }
    printf("Result: %ld\n", a ^ b ^ c);
    return 0;
}
