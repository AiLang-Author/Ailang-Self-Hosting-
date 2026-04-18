#include <stdio.h>

int main() {
    int limit = 1000000;
    int count = 0;
    
    for (int n = 2; n < limit; n++) {
        int is_prime = 1;
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) {
                is_prime = 0;
            }
        }
        if (is_prime) count++;
    }
    
    printf("Primes found: %d\n", count);
    return 0;
}