package main
import "fmt"
func main() {
    sum := 0
    for i := 0; i < 1000000; i++ {
        p := new(int)
        *p = i
        sum += *p
    }
    fmt.Printf("Sum: %d\n", sum)
}
