package main

import "fmt"

func add(a, b int) int {
    return a + b
}

func main() {
    sum := 0
    for i := 0; i < 100000000; i++ {
        sum += add(i, 1)
    }
    fmt.Printf("Sum: %d\n", sum)
}
