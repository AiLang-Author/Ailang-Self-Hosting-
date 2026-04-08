const std = @import("std");

fn add(a: i64, b: i64) i64 {
    return a + b;
}

pub fn main() !void {
    var sum: i64 = 0;
    var i: i64 = 0;
    while (i < 100000000) : (i += 1) {
        sum += add(i, 1);
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Sum: {}\n", .{sum});
}
