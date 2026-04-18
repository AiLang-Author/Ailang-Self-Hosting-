fn add(a: i64, b: i64) -> i64 {
    a + b
}

fn main() {
    let mut sum: i64 = 0;
    for i in 0..100000000_i64 {
        sum += add(i, 1);
    }
    println!("Sum: {}", sum);
}
