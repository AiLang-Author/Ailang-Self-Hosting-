const std = @import("std");

pub fn main() !void {
    const limit: i64 = 1000000;
    var count: i64 = 0;
    var n: i64 = 2;

    while (n < limit) : (n += 1) {
        var is_prime: bool = true;
        var i: i64 = 2;
        while (i * i <= n) : (i += 1) {
            if (@mod(n, i) == 0) {
                is_prime = false;
            }
        }
        if (is_prime) count += 1;
    }

    const stdout = std.io.getStdOut().writer();
    try stdout.print("Primes found: {}\n", .{count});
}
