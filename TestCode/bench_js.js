// bench_js.js — Same micro-benchmarks for Node.js/V8 comparison
// Usage: node TestCode/bench_js.js

function bench(label, fn) {
    const start = performance.now();
    fn();
    const elapsed = performance.now() - start;
    console.log(`  ${label}: ${elapsed.toFixed(3)} ms`);
    return elapsed;
}

console.log("========================================");
console.log("  Node.js/V8 — Micro-Benchmarks");
console.log("========================================\n");
console.log("Benchmarks (wall-clock, performance.now):\n");

let total = 0;

// Benchmark 1: Loop counter
total += bench("loop 100k iterations", () => {
    var i = 0; while (i < 100000) { i = i + 1; }
});

// Benchmark 2: Fibonacci recursive
total += bench("fib(20) recursive", () => {
    function fib(n) { if (n < 2) { return n; } return fib(n - 1) + fib(n - 2); }
    fib(20);
});

// Benchmark 3: Arithmetic churn
total += bench("arith 50k iterations", () => {
    var a = 0; var b = 1; var i = 0;
    while (i < 50000) { a = a + b * 3 - 1; b = b + a - 2; i = i + 1; }
});

// Benchmark 4: Object property access
total += bench("obj props 10k iters", () => {
    var obj = {x: 0, y: 0, z: 0}; var i = 0;
    while (i < 10000) { obj.x = obj.x + 1; obj.y = obj.y + obj.x; obj.z = obj.z + obj.y; i = i + 1; }
});

// Benchmark 5: String concat
total += bench("string concat 1k", () => {
    var s = ""; var i = 0;
    while (i < 1000) { s = s + "a"; i = i + 1; }
});

// Benchmark 6: Nested function calls
total += bench("nested calls 10k", () => {
    function c(x){return x+1;} function b(x){return c(x)+1;} function a(x){return b(x)+1;}
    var i=0; var r=0; while(i<10000){r=a(i);i=i+1;}
});

// Benchmark 7: Array push + sum
total += bench("array 5k push+sum", () => {
    var arr = []; var i = 0;
    while (i < 5000) { arr.push(i); i = i + 1; }
    var sum = 0; i = 0;
    while (i < 5000) { sum = sum + arr[i]; i = i + 1; }
});

console.log(`\n========================================`);
console.log(`Total: ${total.toFixed(3)} ms across 7 benchmarks`);
console.log("========================================");
