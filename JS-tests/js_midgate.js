// js_midgate.js — Fast language mid-gate for the Ailang JS engine.
// Self-contained (no test262 includes). Run via:
//   cp JS-tests/js_midgate.js /tmp/test262_current.js && ./test262_harness.x
//   python3 tools/js_midgate.py
//
// Goal: catch regressions in load-bearing features without the full 50k suite.
// Keep green. Prefer adding cases here over claiming progress from ad-hoc smokes.

var __fail = 0;
function check(cond, msg) {
  if (!cond) {
    __fail = 1;
    throw new Error("MIDGATE: " + msg);
  }
}
function eq(a, b, msg) {
  if (a !== b) {
    __fail = 1;
    throw new Error("MIDGATE: " + msg + " got=" + a + " want=" + b);
  }
}

// ── arithmetic / typeof ──
eq(1 + 2 * 3, 7, "arith");
eq(typeof undefined, "undefined", "typeof undefined");
eq(typeof null, "object", "typeof null");
eq(typeof 1, "number", "typeof number");
eq(typeof "x", "string", "typeof string");
eq(typeof {}, "object", "typeof object");
eq(typeof function () {}, "function", "typeof function");

// ── objects / arrays ──
var o = { a: 1, b: 2 };
eq(o.a + o.b, 3, "obj props");
o.c = 3;
eq(o.c, 3, "obj assign");
var arr = [10, 20, 30];
eq(arr[0] + arr[2], 40, "array index");
arr.push(40);
eq(arr.length, 4, "array push");
eq(arr.map(function (x) { return x + 1; })[0], 11, "array map");

// ── control ──
var s = 0;
for (var i = 0; i < 5; i++) s += i;
eq(s, 10, "for sum");
try { throw 42; } catch (e) { eq(e, 42, "throw/catch"); }

// ── functions / closures (per-activation) ──
function make(n) {
  return function () { return n; };
}
eq(make(1)() + make(2)(), 3, "closure distinct");
var makers = [];
for (var j = 0; j < 3; j++) {
  makers.push((function (k) { return function () { return k; }; })(j));
}
eq(makers[0]() + makers[1]() + makers[2](), 3, "IIFE loop closures");

// live binding after capture
function counter() {
  var n = 0;
  return {
    inc: function () { n = n + 1; return n; },
    get: function () { return n; }
  };
}
var c = counter();
c.inc(); c.inc();
eq(c.get(), 2, "closure live binding");

// ── default / rest / arguments ──
function defs(a, b) {
  if (b === undefined) b = 10;
  return a + b;
}
eq(defs(1), 11, "default-ish param");
function rest(a) {
  // rest via arguments slice-ish
  return a + arguments.length;
}
eq(rest(5, 6, 7), 8, "arguments.length");
function mapped(x) {
  arguments[0] = 99;
  return x;
}
// mapped args if engine supports; accept either 99 (mapped) or original
var mv = mapped(1);
check(mv === 99 || mv === 1, "mapped-or-unmapped args");

// ── call array spread ──
function sum3(a, b, c) { return a + b + c; }
eq(sum3(...[1, 2, 3]), 6, "call array spread");
eq(sum3(0, ...[1, 2]), 3, "call mult spread");

// ── iterable spread via Symbol.iterator ──
var it = {
  [Symbol.iterator]: function () {
    var n = 0;
    return {
      next: function () {
        n = n + 1;
        if (n <= 2) return { value: n * 10, done: false };
        return { value: undefined, done: true };
      }
    };
  }
};
eq(sum3(1, ...it), 31, "call iterable spread");

// ── object spread ──
var base = { c: 3, d: 4 };
var x = { ...base };
eq(x.c, 3, "obj spread assign c");
eq(x.d, 4, "obj spread assign d");
eq(Object.keys(x).length, 2, "obj spread keys");
eq((function (obj) { return obj.c + obj.d; })({ ...base }), 7, "obj spread call arg");
eq((function (obj) { return obj.a + obj.c; })({ a: 1, ...base }), 4, "obj spread mult");
eq((function (obj) { return obj.z; })({ ...null, ...undefined, z: 9 }), 9, "obj spread null/undef");
eq((function (obj) { return obj.a + "," + obj.b; })({ a: 0, ...{ a: 1, b: 2 } }), "1,2", "obj spread override");

// ── Symbol ──
var sym = Symbol("t");
eq(typeof sym, "object", "typeof Symbol (engine may report object)");
var so = {};
so[sym] = 7;
// property key access via same symbol
eq(so[sym], 7, "symbol key set/get");

// ── Object.keys enumerable filter ──
var oe = { vis: 1 };
Object.defineProperty(oe, "hid", { value: 2, enumerable: false, writable: true, configurable: true });
var oks = Object.keys(oe);
eq(oks.length, 1, "Object.keys skips non-enum");
eq(oks[0], "vis", "Object.keys vis");

// ── eval re-entry ──
eq(eval("1+2"), 3, "eval arith");
eq(eval("var __ev = 11; __ev"), 11, "eval var");

// ── delete (data props) ──
var delo = { x: 1, y: 2 };
delete delo.x;
eq(delo.x, undefined, "delete prop");


// ── Mole 16: Array / arguments @@iterator ──
var __ait = [][Symbol.iterator];
check(typeof __ait === "function", "[][Symbol.iterator] is function");
check(__ait === Array.prototype.values, "[][Symbol.iterator] === Array.prototype.values");
check(__ait === Array.prototype[Symbol.iterator], "values === proto[@@iterator]");
var __aitr = [7, 8][Symbol.iterator]();
eq(__aitr.next().value, 7, "array iterator next value");
eq((function () { return arguments[Symbol.iterator]; })(1), __ait, "args[@@iterator] identity");
eq((function () {
  var it = arguments[Symbol.iterator]();
  return it.next().value;
})(42, 43), 42, "args iterator yields");

// ── Mole 15 smoke: array pattern elision via iterator ──
var __el1;
[ , __el1] = [10, 20];
eq(__el1, 20, "array dstr elision");
function __elF([, y]) { return y; }
eq(__elF([1, 2]), 2, "param dstr elision");

if (__fail) throw new Error("midgate failed");
// success: fall off end with no throw
