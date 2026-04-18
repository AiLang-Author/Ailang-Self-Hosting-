fn main() {
    let mut sum: i64 = 0;
    for i in 0..100000000_i64 {
        if i % 2 == 0 {
            sum += 1;
        } else {
            sum -= 1;
        }
    }
    println!("Sum: {}", sum);
}
