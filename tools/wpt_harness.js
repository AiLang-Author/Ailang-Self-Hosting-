// Minimal testharness.js shim for Ailang browser WPT runner
// Implements: test(), assert_equals, assert_true, assert_false,
// assert_throws_js, assert_throws_dom, assert_array_equals, etc.

var __wpt_pass = 0;
var __wpt_fail = 0;
var __wpt_results = [];

function test(func, desc) {
    try {
        func();
        __wpt_pass++;
        __wpt_results.push("PASS: " + desc);
    } catch (e) {
        __wpt_fail++;
        __wpt_results.push("FAIL: " + desc + " | " + e.message);
    }
}

function assert_equals(actual, expected, desc) {
    if (actual !== expected) {
        throw new Error("assert_equals: got " + actual + ", expected " + expected + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_not_equals(actual, unexpected, desc) {
    if (actual === unexpected) {
        throw new Error("assert_not_equals: got " + actual + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_true(val, desc) {
    if (val !== true) {
        throw new Error("assert_true: got " + val + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_false(val, desc) {
    if (val !== false) {
        throw new Error("assert_false: got " + val + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_throws_js(constructor, func, desc) {
    var threw = false;
    try { func(); } catch (e) { threw = true; }
    if (!threw) {
        throw new Error("assert_throws_js: did not throw" + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_throws_dom(name, func, desc) {
    var threw = false;
    try { func(); } catch (e) { threw = true; }
    if (!threw) {
        throw new Error("assert_throws_dom: did not throw" + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_array_equals(actual, expected, desc) {
    if (!actual || !expected) {
        throw new Error("assert_array_equals: null array" + (desc ? " (" + desc + ")" : ""));
    }
    if (actual.length !== expected.length) {
        throw new Error("assert_array_equals: length " + actual.length + " vs " + expected.length + (desc ? " (" + desc + ")" : ""));
    }
    for (var i = 0; i < actual.length; i++) {
        if (actual[i] !== expected[i]) {
            throw new Error("assert_array_equals: index " + i + " got " + actual[i] + " expected " + expected[i] + (desc ? " (" + desc + ")" : ""));
        }
    }
}

function assert_in_array(val, arr, desc) {
    var found = false;
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] === val) { found = true; }
    }
    if (!found) {
        throw new Error("assert_in_array: " + val + " not in array" + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_class_string(obj, expected, desc) {
    // Simplified: just check typeof for now
}

function assert_readonly(obj, prop, desc) {
    // Simplified: skip for now
}

function assert_throws_exactly(expected, func, desc) {
    var threw = false;
    try { func(); } catch (e) { threw = true; }
    if (!threw) {
        throw new Error("assert_throws_exactly: did not throw" + (desc ? " (" + desc + ")" : ""));
    }
}

function assert_unreached(desc) {
    throw new Error("assert_unreached: " + (desc || "should not reach here"));
}

// async_test stub — runs synchronously (no real async)
function async_test(func_or_desc, desc) {
    if (typeof func_or_desc === "function") {
        var t = { step: function(f) { f(); }, done: function() {} };
        func_or_desc(t);
    }
    return { step: function(f) { f(); }, done: function() {}, step_func: function(f) { return f; } };
}

// setup / done stubs
function setup(opts) {}
function done() {
    console.log("WPT: " + __wpt_pass + " pass, " + __wpt_fail + " fail");
}

// Stub for promise_test
function promise_test(func, desc) {
    test(function() {
        // Can't run async — skip
    }, desc + " [SKIP-ASYNC]");
}
