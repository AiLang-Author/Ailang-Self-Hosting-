const std = @import("std");
pub fn main() !void {
    var sum: i64 = 0;
    var i: i64 = 0;
    while (i < 100000000) : (i += 1) {
        if ((i * 1234567) & 1 == 1)
            sum += 1
        else
            sum -= 1;
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Sum: {}\n", .{sum});
}
