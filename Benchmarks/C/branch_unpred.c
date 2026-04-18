#include <stdio.h>
int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        if ((i * 1234567) & 1)
            sum += 1;
        else
            sum -= 1;
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
