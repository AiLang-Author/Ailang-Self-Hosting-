package main

import "fmt"

func main() {
    limit := 1000000
    count := 0

    for n := 2; n < limit; n++ {
        isPrime := true
        for i := 2; i*i <= n; i++ {
            if n%i == 0 {
                isPrime = false
            }
        }
        if isPrime {
            count++
        }
    }

    fmt.Printf("Primes found: %d\n", count)
}
