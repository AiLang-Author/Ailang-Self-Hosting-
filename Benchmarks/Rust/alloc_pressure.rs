fn main() {
    let mut sum: i64 = 0;
    for i in 0..1000000_i64 {
        let p = Box::new(i);
        sum += *p;
    }
    println!("Sum: {}", sum);
}
