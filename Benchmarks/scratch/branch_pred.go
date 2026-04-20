package main
import "fmt"
func main() {
    sum := 0
    for i := 0; i < 100000000; i++ {
        if i%2 == 0 {
            sum += 1
        } else {
            sum -= 1
        }
    }
    fmt.Printf("Sum: %d\n", sum)
}
