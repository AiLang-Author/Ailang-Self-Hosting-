fn main() {
    let limit = 1000000;
    let mut count = 0;

    for n in 2..limit {
        let mut is_prime = true;
        let mut i = 2;
        while i * i <= n {
            if n % i == 0 {
                is_prime = false;
            }
            i += 1;
        }
        if is_prime {
            count += 1;
        }
    }

    println!("Primes found: {}", count);
}
