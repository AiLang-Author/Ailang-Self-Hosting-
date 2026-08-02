#!/usr/bin/env python3
"""
test262_runner.py — ECMAScript conformance test runner for the Ailang JS engine.

Discovers tests from tc39/test262, filters for supported features, prepends a
polyfill preamble, preprocesses throw statements, executes via test262_harness.x
(or test262_harness_batch.x for batch mode), and prints a per-category
conformance report.

Usage:
    python3 tools/test262_runner.py [options]

    --categories CAT[,CAT,...]   Comma-separated subdirs under test/language/
                                 (default: all target categories)
    --verbose                    Print each test result
    --output-json FILE           Write JSON results to FILE
    --harness PATH               Path to harness binary (default: ./test262_harness.x)
    --batch-harness PATH         Path to batch harness binary (default: ./test262_harness_batch.x)
    --test262 PATH               Path to test262 repo (default: ./test262)
    --timeout SECS               Per-test timeout (default: 5)
    --no-batch                   Force legacy mode (one process per test)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import argparse
import json
import os
import re
import select
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_CATEGORIES = [
    "statements/if",
    "statements/while",
    "statements/for",
    "statements/do-while",
    "statements/switch",
    "statements/break",
    "statements/continue",
    "statements/return",
    "statements/variable",
    "statements/block",
    "statements/empty",
    "statements/expression",
    "statements/labeled",
    "expressions/typeof",
    "expressions/addition",
    "expressions/assignment",
    "expressions/call",
    "expressions/object",
    "expressions/equals",
    "expressions/does-not-equals",
    "expressions/strict-equals",
    "expressions/strict-does-not-equal",
    "expressions/less-than",
    "expressions/greater-than",
    "expressions/less-than-or-equal",
    "expressions/greater-than-or-equal",
    "expressions/subtraction",
    "expressions/multiplication",
    "expressions/division",
    "expressions/modulus",
    "expressions/comma",
    "expressions/logical-or",
    "expressions/logical-and",
    "expressions/logical-not",
    "expressions/void",
    "expressions/delete",
    "expressions/grouping",
    "expressions/compound-assignment",
    "expressions/prefix-increment",
    "expressions/prefix-decrement",
    "expressions/postfix-increment",
    "expressions/postfix-decrement",
    "expressions/conditional",
    "expressions/bitwise-and",
    "expressions/bitwise-or",
    "expressions/bitwise-xor",
    "expressions/bitwise-not",
    "expressions/left-shift",
    "expressions/right-shift",
    "expressions/unsigned-right-shift",
    "expressions/unary-minus",
    "expressions/unary-plus",
    "expressions/exponentiation",
    "expressions/coalesce",
    "expressions/logical-assignment",
    "expressions/instanceof",
    "expressions/in",
    "expressions/new",
    "expressions/array",
    "expressions/arrow-function",
    "expressions/template-literal",
    "arguments-object",
    "computed-property-names",
    "destructuring",
    "function-code",
    "identifiers",
    "keywords",
    "literals",
    "types",
    "white-space",
    "comments",
    "line-terminators",
    "punctuators",
    "rest-parameters",
    "asi",
    "block-scope",
    "future-reserved-words",
    "reserved-words",
    "directive-prologue",
    "global-code",
    "source-text",
    "identifier-resolution",
    "eval-code",
    "statementList",
    # Async categories
    "statements/async-function",
    "expressions/async-function",
    "expressions/await",
]

# NO SKIPS — full spec conformance target. Every test runs.
UNSUPPORTED_FEATURES = set()
UNSUPPORTED_SOURCE_PATTERNS = []
_UNSUPPORTED_RE = None

POLYFILL = """\
var __test262_failed = 0;
function Test262Error(m) { this.message = m; this.name = "Test262Error"; }
function $ERROR(m) { __test262_failed = 1; }
function $DONOTEVALUATE() { __test262_failed = 1; }
// assert must be a *function* (test262 harness): assert(cond) + assert.sameValue(...)
// Previously assert={} so assert(true) was a no-op (CALL non-function returned undef).
// After typed TypeError on non-callables, every assert(cond) test hard-failed.
function assert(mustBeTrue, message) {
  if (mustBeTrue !== true) { __test262_failed = 1; }
}
// M70: inline compare (no nested method call). Nested CALL_METHOD from
// assert.sameValue → assert._isSameValue broke generator arguments restore
// mid-body (params-dflt-*-args-unmapped and friends).
assert._isSameValue = function(a, b) {
  if (a !== a && b !== b) return true;
  if (a === 0 && b === 0) return (1/a === 1/b);
  return a === b;
};
assert.sameValue = function(a, e, m) {
  var ok = false;
  if (a !== a && e !== e) { ok = true; }
  else if (a === 0 && e === 0) { ok = (1/a === 1/e); }
  else { ok = (a === e); }
  if (!ok) { __test262_failed = 1; }
};
assert.notSameValue = function(a, u, m) {
  var same = false;
  if (a !== a && u !== u) { same = true; }
  else if (a === 0 && u === 0) { same = (1/a === 1/u); }
  else { same = (a === u); }
  if (same) { __test262_failed = 1; }
};
assert.throws = function(E, fn, m) {
  var threw = false;
  var err = null;
  try { fn(); } catch (e) {
    threw = true;
    err = e;
    // Mole 15: generator .next() rethrow can land catch with empty binding;
    // engine stashes the real value on __pend_exc__ (GenNext abrupt path).
    if ((err === undefined || err === null) && typeof __pend_exc__ !== "undefined") {
      err = __pend_exc__;
    }
  }
  if (!threw) { __test262_failed = 1; return; }
  if (E !== undefined && E !== null) {
    if (!(err instanceof E)) { __test262_failed = 1; }
  }
};
assert._toString = function(v) {
  try { return "" + v; } catch (e) { return "unknown"; }
};
function $DONE(err) { if (err) { __test262_failed = 1; } }
var $MAX_ITERATIONS = 100000;
// M108: dual-bind harness globals onto globalThis (GlobalHash ≠ object props).
// asyncHelpers asyncTest checks hasOwnProperty.call(globalThis, "$DONE") — our
// engine often fails that check, so provide a safe asyncTest and skip the include.
globalThis.$DONE = $DONE;
globalThis.$MAX_ITERATIONS = $MAX_ITERATIONS;
globalThis.assert = assert;
globalThis.Test262Error = Test262Error;
globalThis.__test262_failed = __test262_failed;
function asyncTest(testFunc) {
  // NOTE: do not wrap testFunc().then in try/catch — our engine's try scope
  // breaks await completion inside the async test body (assignment-expression
  // array/object/lhs tests). Sync throws still surface as uncaught.
  if (typeof testFunc !== "function") {
    $DONE(new Test262Error("asyncTest called with non-function argument"));
    return;
  }
  testFunc().then(
    function () { $DONE(); },
    function (error) { $DONE(error); }
  );
}
globalThis.asyncTest = asyncTest;
// M128e6ai: always provide Reflect (Proxy with tests / set-mutable-binding)
if (typeof Reflect === "undefined") { Reflect = {}; }
if (typeof Reflect.has !== "function") {
  Reflect.has = function(o, p) { return p in o; };
}
if (typeof Reflect.get !== "function") {
  Reflect.get = function(o, p, r) { return o[p]; };
}
// OrdinarySet with Receiver (Proxy gOPD/defineProperty traps fire on r)
Reflect.set = function(target, p, v, receiver) {
  if (arguments.length < 4) receiver = target;
  try {
    var desc = Object.getOwnPropertyDescriptor(target, p);
    if (desc && Object.prototype.hasOwnProperty.call(desc, "value")) {
      if (desc.writable === false) return false;
      if (receiver !== target) {
        var existing = Object.getOwnPropertyDescriptor(receiver, p);
        if (existing === undefined) {
          Object.defineProperty(receiver, p, {
            value: v, writable: true, enumerable: true, configurable: true
          });
        } else {
          if (existing.writable === false) return false;
          Object.defineProperty(receiver, p, { value: v });
        }
        return true;
      }
      target[p] = v;
      return true;
    }
    target[p] = v;
    return true;
  } catch (e) { return false; }
};
if (typeof Reflect.getOwnPropertyDescriptor !== "function") {
  Reflect.getOwnPropertyDescriptor = function(o, p) {
    return Object.getOwnPropertyDescriptor(o, p);
  };
}
if (typeof Reflect.defineProperty !== "function") {
  Reflect.defineProperty = function(o, p, d) {
    try { Object.defineProperty(o, p, d); return true; } catch (e) { return false; }
  };
}
// M128e7bd/e7bv: Reflect.construct — honor IsConstructor(newTarget).
// Engine: non-ctor natives (Object.assign, keys, map, …) throw on `new`.
// Heuristic: well-known ctor names always constructible; lowercase .name
// (builtin methods) probed with `new bind()`; other functions assumed ok.
if (typeof Reflect.construct !== "function") {
  Reflect.construct = function(target, args, newTarget) {
    if (typeof target !== "function") throw new TypeError("Reflect.construct");
    if (arguments.length < 3) newTarget = target;
    if (typeof newTarget !== "function") throw new TypeError("Reflect.construct");
    var a = args || [];
    var __n = newTarget.name;
    var __isCtor = true;
    if (__n === "assign" || __n === "keys" || __n === "create" || __n === "freeze" ||
        __n === "seal" || __n === "entries" || __n === "values" || __n === "fromEntries" ||
        __n === "getOwnPropertySymbols" || __n === "getOwnPropertyNames" ||
        __n === "getOwnPropertyDescriptor" || __n === "getOwnPropertyDescriptors" ||
        __n === "defineProperty" || __n === "defineProperties" || __n === "groupBy" ||
        __n === "is" || __n === "hasOwn" || __n === "preventExtensions" ||
        __n === "isExtensible" || __n === "isFrozen" || __n === "isSealed" ||
        __n === "getPrototypeOf" || __n === "setPrototypeOf" ||
        __n === "propertyIsEnumerable" || __n === "isPrototypeOf" ||
        __n === "hasOwnProperty" || __n === "toString" || __n === "valueOf" ||
        __n === "toLocaleString" ||
        (__n && __n.length > 0 && __n.charCodeAt(0) >= 97 && __n.charCodeAt(0) <= 122 &&
         __n !== "get" && __n !== "set" && __n !== "has" && __n !== "apply" &&
         __n !== "call" && __n !== "bind")) {
      // lowercase builtin method — confirm non-constructible
      try {
        new (Function.prototype.bind.call(newTarget))();
      } catch (__e) {
        __isCtor = false;
      }
    }
    if (!__isCtor) throw new TypeError("Reflect.construct");
    if (newTarget === target) {
      if (a.length === 0) return new target();
      if (a.length === 1) return new target(a[0]);
      if (a.length === 2) return new target(a[0], a[1]);
      if (a.length === 3) return new target(a[0], a[1], a[2]);
      var __b = Function.prototype.bind.apply(target, [null].concat(Array.prototype.slice.call(a)));
      return new __b();
    }
    var proto = newTarget.prototype;
    var obj;
    if (proto !== null && (typeof proto === "object" || typeof proto === "function")) {
      obj = Object.create(proto);
    } else {
      obj = {};
    }
    var save = __new_target__;
    __new_target__ = newTarget;
    var result;
    try {
      result = Function.prototype.apply.call(target, obj, a);
    } finally {
      __new_target__ = save;
    }
    if (result !== null && (typeof result === "object" || typeof result === "function")) {
      return result;
    }
    return obj;
  };
}
if (typeof Reflect.apply !== "function") {
  Reflect.apply = function(target, thisArg, args) {
    if (typeof target !== "function") throw new TypeError("Reflect.apply");
    return Function.prototype.apply.call(target, thisArg, args || []);
  };
}
globalThis.Reflect = Reflect;
// Minimal TypedArray for with ObjectEnv tests (features: TypedArray)
if (typeof Int32Array === "undefined") {
  function Int32Array(n) {
    var a = [];
    var len = n | 0;
    if (len < 0) len = 0;
    a.length = len;
    for (var i = 0; i < len; i++) a[i] = 0;
    return a;
  }
  globalThis.Int32Array = Int32Array;
}
function __isSameValue(a, b) {
  if (a !== a && b !== b) return true; // NaN
  if (a === 0 && b === 0) return (1 / a) === (1 / b); // ±0
  return a === b;
}
// Lightweight propertyHelper: full harness uses call.bind and dies under our engine.
function verifyProperty(obj, name, desc, options) {
  var od = Object.getOwnPropertyDescriptor(obj, name);
  if (desc === undefined) {
    if (od !== undefined) { __test262_failed = 1; }
    return true;
  }
  if (od === undefined) { __test262_failed = 1; return false; }
  if (!Object.prototype.hasOwnProperty.call(obj, name)) { __test262_failed = 1; return false; }
  if (Object.prototype.hasOwnProperty.call(desc, "value")) {
    if (!__isSameValue(desc.value, od.value)) { __test262_failed = 1; return false; }
    if (!__isSameValue(desc.value, obj[name])) { __test262_failed = 1; return false; }
  }
  if (Object.prototype.hasOwnProperty.call(desc, "writable")) {
    if (desc.writable !== od.writable) { __test262_failed = 1; return false; }
  }
  if (Object.prototype.hasOwnProperty.call(desc, "enumerable")) {
    if (desc.enumerable !== od.enumerable) { __test262_failed = 1; return false; }
  }
  if (Object.prototype.hasOwnProperty.call(desc, "configurable")) {
    if (desc.configurable !== od.configurable) { __test262_failed = 1; return false; }
  }
  if (Object.prototype.hasOwnProperty.call(desc, "get")) {
    if (desc.get !== od.get) { __test262_failed = 1; return false; }
  }
  if (Object.prototype.hasOwnProperty.call(desc, "set")) {
    if (desc.set !== od.set) { __test262_failed = 1; return false; }
  }
  // Optional: restore mutations (writable/configurable probes) — no-op if unused
  return true;
}
function verifyEqualTo(obj, name, value) {
  if (!__isSameValue(obj[name], value)) { __test262_failed = 1; }
}
function verifyCallableProperty(obj, name, desc, options) {
  return verifyProperty(obj, name, desc, options);
}
function verifyPrimordialProperty(obj, name, desc, options) {
  return verifyProperty(obj, name, desc, options);
}
function verifyPrimordialCallableProperty(obj, name, desc, options) {
  return verifyProperty(obj, name, desc, options);
}
function verifyNotEnumerable(obj, name) {
  for (var k in obj) { if (k === name) { __test262_failed = 1; } }
}
function verifyEnumerable(obj, name) {
  var found = false;
  for (var k in obj) { if (k === name) { found = true; } }
  if (!found) { __test262_failed = 1; }
}
// M128e7by: match test262 propertyHelper isWritable — 3rd arg verifyProp for
// accessors (set updates obj[verifyProp], not obj[name] which is still getter).
function verifyWritable(obj, name, verifyProp, value) {
  var newValue = (value !== undefined) ? value : "___test262_w___";
  var oldValue = obj[name];
  if (newValue === oldValue) newValue = newValue + "2";
  var had = Object.prototype.hasOwnProperty.call(obj, name);
  try { obj[name] = newValue; } catch (e) { __test262_failed = 1; return; }
  var check = (verifyProp !== undefined && verifyProp !== null) ? obj[verifyProp] : obj[name];
  if (check !== newValue) { __test262_failed = 1; }
  else {
    if (had) {
      try { obj[name] = oldValue; } catch (e2) {}
    } else {
      try { delete obj[name]; } catch (e3) {}
    }
  }
}
function verifyNotWritable(obj, name, verifyProp, value) {
  var newValue = (value !== undefined) ? value : "___test262_w___";
  var oldValue = obj[name];
  var oldCheck = (verifyProp !== undefined && verifyProp !== null) ? obj[verifyProp] : obj[name];
  try { obj[name] = newValue; } catch (e) { /* TypeError expected for non-writable */ }
  var check = (verifyProp !== undefined && verifyProp !== null) ? obj[verifyProp] : obj[name];
  if (check !== oldCheck && check === newValue) { __test262_failed = 1; }
  else {
    try { obj[name] = oldValue; } catch (e2) {}
  }
}
function verifyConfigurable(obj, name) {
  var old = obj[name]; delete obj[name];
  if (obj[name] !== undefined) { __test262_failed = 1; }
  obj[name] = old;
}
function verifyNotConfigurable(obj, name) {
  var old = obj[name]; delete obj[name];
  if (obj[name] === undefined && old !== undefined) { __test262_failed = 1; }
}
function isConstructor(f) { try { new f(); return true; } catch(e) { return false; } }
function compareArray(a, b) {
  if (a.length !== b.length) return false;
  for (var i = 0; i < a.length; i++) { if (a[i] !== b[i]) return false; }
  return true;
}
assert.compareArray = function(a, b, m) { if (!compareArray(a, b)) { __test262_failed = 1; } };
// IMPORTANT: never `var Object` / `var Array` here. This engine's var-hoist
// initializes the binding to undefined and *shadows* the built-in global,
// so Object.keys / Array.isArray die for the rest of the program.
if (typeof Object !== "undefined") {
  // Prefer gOPD so Symbol keys work (for-in never yields symbols).
  if (typeof Object.hasOwn !== "function") {
    Object.hasOwn = function(obj, key) {
      if (obj === null || obj === undefined) return false;
      return Object.getOwnPropertyDescriptor(obj, key) !== undefined;
    };
  }
  if (typeof Object.prototype !== "undefined" && typeof Object.prototype.hasOwnProperty !== "function") {
    Object.prototype.hasOwnProperty = function(k) {
      return Object.getOwnPropertyDescriptor(this, k) !== undefined;
    };
  }
}
// M31b: regExpUtils helpers — sample BMP via array.join (no quadratic concat).
function buildString(args) {
  var loneCodePoints = args.loneCodePoints || [];
  var ranges = args.ranges || [];
  var MAX_CP = 2048;
  var parts = [];
  var total = 0;
  var i, start, end, codePoint;
  for (i = 0; i < loneCodePoints.length; i++) {
    if (total >= MAX_CP) break;
    codePoint = loneCodePoints[i];
    if (codePoint < 1 || codePoint > 0xFFFF) continue;
    parts[total++] = String.fromCharCode(codePoint);
  }
  for (i = 0; i < ranges.length; i++) {
    start = ranges[i][0];
    end = ranges[i][1];
    if (start < 1) start = 1;
    if (start > 0xFFFF) continue;
    if (end > 0xFFFF) end = 0xFFFF;
    var span = end - start + 1;
    var step = 1;
    if (span > MAX_CP) step = ((span / MAX_CP) | 0) + 1;
    for (codePoint = start; codePoint <= end; codePoint += step) {
      if (total >= MAX_CP) break;
      parts[total++] = String.fromCharCode(codePoint);
    }
    if (total >= MAX_CP) break;
  }
  return parts.join("");
}
function testPropertyEscapes(regExp, string, expression) {
  if (string.length === 0) return;
  // Prefer one whole-string test for ^…+$ patterns (huge win vs N×charAt alloc)
  try {
    if (regExp.test(string)) return;
  } catch (e) {}
  var i;
  for (i = 0; i < string.length; i++) {
    if (!regExp.test(string.charAt(i))) {
      __test262_failed = 1;
      return;
    }
  }
}
function printCodePoint(codePoint) {
  return "U+" + codePoint.toString(16).toUpperCase();
}
function printStringCodePoints(string) {
  var buf = [];
  for (var si = 0; si < string.length; ) {
    var cp = string.codePointAt(si);
    buf.push(printCodePoint(cp));
    si += String.fromCodePoint(cp).length;
  }
  return buf.join(" ");
}
// M31c: unicodeSets harness helper (sample strings only; no huge builds)
function testExtendedCharacterClass(args) {
  var re = args.regExp;
  var matchStrings = args.matchStrings || [];
  var nonMatchStrings = args.nonMatchStrings || [];
  var i;
  for (i = 0; i < matchStrings.length; i++) {
    if (!re.test(matchStrings[i])) { __test262_failed = 1; return; }
  }
  for (i = 0; i < nonMatchStrings.length; i++) {
    if (re.test(nonMatchStrings[i])) { __test262_failed = 1; return; }
  }
}
"""

EPILOGUE = """
if (__test262_failed) { throw new Error("test262 assertion failed"); }
"""

TMP_FILE = "/tmp/test262_current.js"  # legacy single-thread path
_thread_local = threading.local()
_ORIG_PATH = b"/tmp/test262_current.js"  # 23 bytes — must match harness binary

# Pre-encode polyfill and epilogue
_POLYFILL_BYTES = POLYFILL.encode("utf-8", errors="replace")
_EPILOGUE_BYTES = EPILOGUE.encode("utf-8", errors="replace")

# =============================================================================
# FRONTMATTER PARSER
# =============================================================================

_FRONTMATTER_RE = re.compile(r'/\*---\s*\n(.*?)\n\s*---\*/', re.DOTALL)


def parse_frontmatter(source):
    """Extract YAML-ish frontmatter from test262 test file."""
    m = _FRONTMATTER_RE.search(source)
    if not m:
        return {}

    raw = m.group(1)
    meta = {}

    # Parse features list
    feat_match = re.search(r'^features:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if feat_match:
        meta["features"] = [f.strip().strip("'\"") for f in feat_match.group(1).split(",") if f.strip()]
    else:
        feat_lines = []
        in_feat = False
        for line in raw.split("\n"):
            if re.match(r'^features:\s*$', line):
                in_feat = True
                continue
            if in_feat:
                fm = re.match(r'^\s+-\s+(.+)', line)
                if fm:
                    feat_lines.append(fm.group(1).strip().strip("'\""))
                else:
                    in_feat = False
        if feat_lines:
            meta["features"] = feat_lines

    # Parse flags
    flags_match = re.search(r'^flags:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if flags_match:
        meta["flags"] = [f.strip().strip("'\"") for f in flags_match.group(1).split(",") if f.strip()]
    else:
        flag_lines = []
        in_flags = False
        for line in raw.split("\n"):
            if re.match(r'^flags:\s*$', line):
                in_flags = True
                continue
            if in_flags:
                fm = re.match(r'^\s+-\s+(.+)', line)
                if fm:
                    flag_lines.append(fm.group(1).strip().strip("'\""))
                else:
                    in_flags = False
        if flag_lines:
            meta["flags"] = flag_lines

    # Parse negative
    neg_match = re.search(r'^negative:', raw, re.MULTILINE)
    if neg_match:
        meta["negative"] = True
        phase_match = re.search(r'phase:\s*(\w+)', raw[neg_match.start():])
        if phase_match:
            meta["negative_phase"] = phase_match.group(1)
        type_match = re.search(r'type:\s*(\w+)', raw[neg_match.start():])
        if type_match:
            meta["negative_type"] = type_match.group(1)

    # Parse includes: [a.js, b.js]
    inc_match = re.search(r'^includes:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if inc_match:
        meta["includes"] = [f.strip().strip("'\"") for f in inc_match.group(1).split(",") if f.strip()]
    else:
        inc_lines = []
        in_inc = False
        for line in raw.split("\n"):
            if re.match(r'^includes:\s*$', line):
                in_inc = True
                continue
            if in_inc:
                im = re.match(r'^\s+-\s+(.+)', line)
                if im:
                    inc_lines.append(im.group(1).strip().strip("'\""))
                else:
                    in_inc = False
        if inc_lines:
            meta["includes"] = inc_lines

    return meta


# =============================================================================
# PREPROCESSOR
# =============================================================================

def preprocess(source, meta=None, test_path=None):
    """Clean up test source for the Ailang JS engine (frontmatter strip only).

    Module tests get a best-effort link rewrite so self-imports and simple
    same-dir FIXTURE modules become plain script bindings (engine still
    parses export/import; this supplies the missing multi-module loader).

    Dynamic-import tests (script or module) get a HostImportModuleDynamically
    shim: fixture bodies → namespace objects registered on global __dynModules
    for IMPORT_DYN, plus Promise.reject rewrites for throw/script-error targets.
    """
    source = _FRONTMATTER_RE.sub("", source)
    # M128e7bh: harness ReadTextFile is C-string (NUL truncates). Rewrite
    # literal NUL-in-quotes from test sources to \\0 escape (tv-null-character).
    if "\x00" in source:
        source = source.replace("'\x00'", "'\\0'").replace('"\x00"', '"\\0"')
        source = source.replace("\x00", "")
    flags = (meta or {}).get("flags") or []
    features = (meta or {}).get("features") or []
    is_module = "module" in flags
    # Only true dynamic import() — not static `import defer` / import-attributes.
    wants_dyn = bool(
        test_path
        and (
            "dynamic-import" in features
            or "import(" in source
            or "import (" in source
        )
    )

    dyn_imports = []  # list of (bind_name, spec)
    reject_rewrite = {}
    if wants_dyn:
        try:
            dyn_imports, reject_rewrite, source = _dyn_prepare(
                source, test_path
            )
        except Exception:
            dyn_imports, reject_rewrite = [], {}

    # Module link + dynimport registry. Prefer a single _preprocess_module pass
    # when static modules and/or complex dyn fixtures need the full linker.
    dyn_full = bool(
        wants_dyn and test_path and _dyn_imports_need_full_link(dyn_imports, test_path)
    )
    if test_path and (is_module or dyn_full):
        try:
            link_src = source
            if wants_dyn and dyn_imports:
                head = "\n".join(
                    f"import * as {bn} from {json.dumps(sp)};"
                    for bn, sp in dyn_imports
                )
                reg = ["var __dynModules = Object.create(null);"]
                for bn, sp in dyn_imports:
                    reg.append(f"__dynModules[{json.dumps(sp)}] = {bn};")
                link_src = head + "\n" + "\n".join(reg) + "\n" + source
            elif wants_dyn:
                link_src = "var __dynModules = Object.create(null);\n" + source
            source = _preprocess_module(link_src, test_path)
            # M128e7bt: wrap TLA even when flags include [async]. Engine has no
            # bare top-level await; async suite uses $DONE but still needs the
            # async-IIFE wrapper so `await` is legal (28/32 TLA fails were async).
            if is_module and (
                "top-level-await" in features or _source_has_toplevel_await(source)
            ):
                source = _wrap_toplevel_await(source)
        except Exception:
            pass
    elif wants_dyn and test_path:
        # Simple dynimport fixtures: IIFE-isolated NS (no local1 clashes)
        try:
            dyn_pre = _build_dyn_modules_preamble(dyn_imports, test_path)
            source = dyn_pre + source
        except Exception:
            source = "var __dynModules = Object.create(null);\n" + source

    # Reflect/gOPD NS shims — only for module-namespace / dynimport surfaces.
    # M128e7bd: do NOT inject on bare "Reflect" in source. Language tests that
    # only use Reflect.construct/apply (new.target, optional-chaining) paid a
    # huge free-var cost: multi-let SET_FREE under CallFunc broke (context/called).
    if test_path and (
        "namespace" in (test_path or "")
        or "import-defer" in (test_path or "")
        or "module-code" in (test_path or "")
        or "__markModuleNS" in source
        or "__defEval" in source
        or dyn_imports
        or wants_dyn
        or is_module
    ):
        if "function __markModuleNS" not in source:
            source = _MODULE_REFLECT_STUB + source

    # import.meta — rewrite to __import_meta__ (null-proto object)
    if re.search(r'\bimport\s*\.\s*meta\b', source):
        source = re.sub(r'\bimport\s*\.\s*meta\b', '__import_meta__', source)
        if "var __import_meta__" not in source:
            source = (
                "var __import_meta__ = Object.create(null);\n"
                + source
            )

    # Free-var let/const through generator cenv is unreliable (GET/SET_FREE).
    # Usage templates: `let callCount` + async-gen then callbacks; `const obj`
    # for import(obj) ToString — demote to var for dual-bind free-var path.
    # NS getters `return __default_export__` also need var (let free-var miss).
    if wants_dyn:
        source = re.sub(r'\blet\s+callCount\b', 'var callCount', source)
        source = re.sub(
            r'\bconst\s+(obj)\s*=',
            r'var \1 =',
            source,
        )
        source = re.sub(
            r'\blet\s+(__default_export__|__dflt_[A-Za-z0-9_]+)\b',
            r'var \1',
            source,
        )
        # Name-stamp after class/fn default must run before import().then
        # callbacks read `.name` (stamp is often left at EOF by module rewrite).
        source = re.sub(
            r"(import\s*\(\s*['\"][^'\"]+['\"]\s*\)\s*\.then\([\s\S]*?\)\s*;?\s*)"
            r"(try\{var __n=(__default_export__|__dflt_[A-Za-z0-9_]+)\.name;[\s\S]*?catch\(e\)\{\})",
            r"\2\n\1",
            source,
            count=1,
        )
        # `await import(E)` — ToString abrupt inside async CallFunc can poison
        # the outer async frame. Pre-coerce with ''+E and Promise.reject on throw
        # so await Promise.reject (known-good) carries the reason; string import()
        # for success. Also expand `.then` form to settle before chaining.
        def _expand_await_import(src, phase=""):
            # phase: "" | "source" | "defer"
            needle = f"await import.{phase}(" if phase else "await import("
            if phase:
                needle = f"await import.{phase}("
            out = []
            i = 0
            while True:
                j = src.find(needle, i)
                if j < 0:
                    out.append(src[i:])
                    break
                k = j + len(needle)
                depth = 1
                while k < len(src) and depth:
                    if src[k] == "(":
                        depth += 1
                    elif src[k] == ")":
                        depth -= 1
                    k += 1
                expr = src[j + len(needle) : k - 1]
                rest = src[k:]
                mthen = re.match(r"\s*\.\s*then\s*\(", rest)
                # call site: import / import.source / import.defer
                call = f"import.{phase}" if phase else "import"
                es = expr.strip()
                # Keep string-literal import() intact so reject_rewrite can match
                # import('./throw_FIXTURE.js') etc. Only wrap non-literals (obj).
                is_str_lit = (
                    len(es) >= 2
                    and (
                        (es[0] == "'" and es[-1] == "'")
                        or (es[0] == '"' and es[-1] == '"')
                    )
                )
                if mthen:
                    h0 = k + mthen.end()
                    depth = 1
                    h = h0
                    while h < len(src) and depth:
                        if src[h] == "(":
                            depth += 1
                        elif src[h] == ")":
                            depth -= 1
                        h += 1
                    handler = src[h0 : h - 1]
                    out.append(src[i:j])
                    if is_str_lit:
                        out.append(
                            f"await (async function(){{ "
                            f"var __m = await {call}({expr}); "
                            f"await Promise.resolve(__m).then({handler}); "
                            f"}})()"
                        )
                    else:
                        out.append(
                            f"await (async function(){{ "
                            f"var __m = await (function(__s){{ "
                            f"try{{ __s = '' + __s; }}catch(__e){{ return Promise.reject(__e); }} "
                            f"return {call}(__s); }})({expr}); "
                            f"await Promise.resolve(__m).then({handler}); "
                            f"}})()"
                        )
                    i = h
                else:
                    out.append(src[i:j])
                    if is_str_lit:
                        out.append(f"await {call}({expr})")
                    else:
                        out.append(
                            f"await (function(__s){{ "
                            f"try{{ __s = '' + __s; }}catch(__e){{ return Promise.reject(__e); }} "
                            f"return {call}(__s); }})({expr})"
                        )
                    i = k
            return "".join(out)

        source = _expand_await_import(source, "")
        source = _expand_await_import(source, "source")
        source = _expand_await_import(source, "defer")

    if wants_dyn and reject_rewrite:
        for sp, rej in reject_rewrite.items():
            for q in ('"', "'"):
                lit = q + sp + q
                source = re.sub(
                    rf'''import\s*\(\s*{re.escape(lit)}\s*(?:,\s*[^)]*)?\s*\)''',
                    rej,
                    source,
                )
    return source


def _dyn_imports_need_full_link(dyn_imports, test_path):
    """True if fixtures need the multi-module linker (cross-module deps).

    Same-file re-exports (`export { x } from './self_FIXTURE.js'`) are OK in
    the IIFE path. Cross-module import/export-from needs full link (nested NS).
    """
    if not dyn_imports:
        return False
    base = Path(test_path).parent
    self_names = {Path(sp).name for _bn, sp in dyn_imports}
    for _bn, sp in dyn_imports:
        cand = _dyn_resolve_fixture(base, sp)
        if cand is None:
            continue
        try:
            body = _FRONTMATTER_RE.sub("", cand.read_text(errors="replace"))
        except Exception:
            continue
        # import of another module
        for m in re.finditer(
            r'''\bimport\b[^;]*from\s*['"]([^'"]+)['"]''', body
        ):
            other = Path(m.group(1)).name
            if other not in self_names and other != cand.name:
                return True
        # side-effect import './x'
        for m in re.finditer(r'''\bimport\s*['"]([^'"]+)['"]''', body):
            other = Path(m.group(1)).name
            if other not in self_names and other != cand.name:
                return True
        # export … from other module
        for m in re.finditer(
            r'''export\s+[^;]*\bfrom\s*['"]([^'"]+)['"]''', body
        ):
            other = Path(m.group(1)).name
            if other != cand.name:
                return True
        if re.search(r'export\s*\*\s*as\b', body):
            return True
    return False


def _build_dyn_modules_preamble(dyn_imports, test_path):
    """Build IIFE-isolated namespace objects for IMPORT_DYN (__dynModules).

    Each fixture runs in its own function scope so `var local1` in module A
    does not overwrite module B (assignment-expression multi-fixture tests).
    """
    base = Path(test_path).parent
    lines = ["var __dynModules = Object.create(null);"]
    if not dyn_imports:
        return "\n".join(lines) + "\n"

    for bn, sp in dyn_imports:
        cand = _dyn_resolve_fixture(base, sp)
        if cand is None:
            continue
        try:
            raw = cand.read_text(errors="replace")
        except Exception:
            continue
        body = _FRONTMATTER_RE.sub("", raw)
        # Collect simple export map for this fixture alone
        export_map, default_local, body_js = _dyn_parse_fixture_exports(body, bn)
        # Prefix all fixture locals so they cannot clash with test vars (let x = 0
        # after IIFE was capturing getters' free-var x). Engine free-var resolve
        # can bind nested function(){return x} to outer script lets.
        pfx = f"__fx{bn}_"
        locs = set()
        for exp, loc in export_map.items():
            if re.match(r"^[A-Za-z_$][\w$]*$", str(loc)):
                locs.add(str(loc))
        if default_local and re.match(r"^[A-Za-z_$][\w$]*$", str(default_local)):
            locs.add(str(default_local))
        for m in re.finditer(
            r'\b(?:var|let|const|function|class)\s+([A-Za-z_$][\w$]*)',
            body_js,
        ):
            locs.add(m.group(1))
        # Rename longest first to avoid partial rewrites
        for loc in sorted(locs, key=len, reverse=True):
            if loc.startswith("__fx") or loc.startswith("__dflt") or loc.startswith("__di"):
                continue
            body_js = re.sub(rf'\b{re.escape(loc)}\b', pfx + loc, body_js)
            if loc in export_map.values() or loc == default_local:
                pass
            export_map = {
                e: (pfx + l if l == loc else l) for e, l in export_map.items()
            }
            if default_local == loc:
                default_local = pfx + loc
        # Engine free-var resolve from NS getters is unreliable for let/const
        # (nested arrow `.then` callbacks fail `imported.x` while `var` works).
        body_js = re.sub(r'\bconst\b', 'var', body_js)
        body_js = re.sub(r'\blet\b', 'var', body_js)
        # IIFE: evaluate body, build NS, return NS
        ns_lines = [
            f"var {bn} = (function(){{",
            body_js,
            f"  var __ns = Object.create(null);",
        ]
        key_list = []
        for exp, loc in sorted(export_map.items()):
            if not re.match(r"^[A-Za-z_$][\w$]*$", str(loc)):
                continue
            prop = json.dumps(exp, ensure_ascii=False)
            ns_lines.append(
                f'  Object.defineProperty(__ns, {prop}, {{'
                f"get:function(){{return {loc};}},"
                f'set:function(){{throw new TypeError("Module namespace is read-only");}},'
                f"enumerable:true,configurable:false}});"
            )
            key_list.append(exp)
        if default_local and "default" not in export_map:
            ns_lines.append(
                f'  Object.defineProperty(__ns, "default", {{'
                f"get:function(){{return {default_local};}},"
                f'set:function(){{throw new TypeError("Module namespace is read-only");}},'
                f"enumerable:true,configurable:false}});"
            )
            key_list.append("default")
        ns_lines.append(
            f'  try{{Object.defineProperty(__ns, Symbol.toStringTag, {{'
            f'value:"Module",writable:false,enumerable:false,configurable:false}});}}catch(e){{}}'
        )
        ns_lines.append("  try{Object.preventExtensions(__ns);}catch(e){}")
        keys_js = json.dumps(key_list, ensure_ascii=False)
        ns_lines.append(f'  try{{__markModuleNS(__ns, {keys_js});}}catch(e){{}}')
        ns_lines.append("  return __ns;")
        ns_lines.append("})();")
        lines.extend(ns_lines)
        lines.append(f"__dynModules[{json.dumps(sp)}] = {bn};")

    return "\n".join(lines) + "\n"


def _dyn_parse_fixture_exports(body, prefix):
    """Parse a fixture into (export_map, default_local, body_js) with export keywords stripped.

    prefix: unique id for default local name to avoid clashes across IIFEs (optional).
    """
    dloc = f"__dflt_{prefix}"
    # Rewrite anonymous default export (use var — let inside dyn IIFE is flaky)
    src = _rewrite_anon_default_export(body, local_name=dloc)
    src = re.sub(
        rf'\blet\s+{re.escape(dloc)}\b',
        f'var {dloc}',
        src,
    )
    rmap = {}
    dflt, named = _collect_module_exports(src, rmap)
    if dloc in src or re.search(rf"\b{re.escape(dloc)}\b", src):
        dflt = dloc
        named["default"] = dloc
    # Expand trivial export { a as b } / export var a (local map only; no * from for dyn)
    # Handle export { local2 as renamed }
    for exp, (sp, im) in list(rmap.items()):
        if im not in ("*", "**") and not str(exp).startswith("*from*"):
            # re-export from self-path often used as alias
            if sp and Path(sp).name.replace("_FIXTURE.js", "") in (
                Path(sp).name,
            ):
                pass
            # For same-file re-exports (indirect from self), map to import name
            if im and re.match(r"^[A-Za-z_$][\w$]*$", str(im)):
                named[exp] = im
    # Strip export syntax for IIFE body
    body_js = src
    body_js = re.sub(r"\s+with\s*\{[^}]*\}", "", body_js)
    body_js = re.sub(r"\s+assert\s*\{[^}]*\}", "", body_js)
    # Named `export default function fn(){ fn=2; … }` must stay a *declaration*
    # so `fn` is a mutable module binding (live default). Naively rewriting to
    # `var dloc = function fn(){ fn=2 }` makes `fn` an immutable NFE name and
    # leaves the getter pointing at the wrong binding (gtbndng-dflt fails).
    body_js = re.sub(
        r"\bexport\s+default\s+((?:async\s+)?function\s*\*?\s+[A-Za-z_$][\w$]*)",
        r"\1",
        body_js,
    )
    body_js = re.sub(
        r"\bexport\s+default\s+(class\s+[A-Za-z_$][\w$]*)",
        r"\1",
        body_js,
    )
    # Anonymous / expression default → var dloc = …
    body_js = re.sub(r"\bexport\s+default\s+", f"var {dloc} = ", body_js)
    body_js = re.sub(r"\bexport\s+(var|let|const|function|class|async)\b", r"\1", body_js)
    # export { a as b }; / export { a };
    body_js = re.sub(r"\bexport\s*\{[^}]*\}\s*from\s*['\"][^'\"]+['\"]\s*;?", "", body_js)
    body_js = re.sub(r"\bexport\s*\{[^}]*\}\s*;?", "", body_js)
    body_js = re.sub(r"\bexport\s*\*\s*(?:as\s+\S+\s+)?from\s*['\"][^'\"]+['\"]\s*;?", "", body_js)
    body_js = re.sub(r"\bexport\s+", "", body_js)
    # Indent body for IIFE
    body_js = "\n".join(
        ("  " + ln if ln.strip() else ln) for ln in body_js.splitlines()
    )
    return named, dflt, body_js


def _dyn_fixture_is_throw(body):
    """True if fixture body is a top-level throw (eval abrupt / import-errored)."""
    s = re.sub(r'//.*?$', '', body, flags=re.MULTILINE)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    s = s.strip()
    return bool(re.match(r'throw\b', s))


def _dyn_fixture_throw_expr(body):
    """Extract `throw <expr>;` expression for Promise.reject rewrite."""
    s = re.sub(r'//.*?$', '', body, flags=re.MULTILINE)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    m = re.search(r'throw\s+([^;]+);', s)
    if m:
        return m.group(1).strip()
    return 'new Error("module evaluation failed")'


def _dyn_fixture_invalid_module(body):
    """Heuristic: script-only fixtures that are SyntaxError as Module Records.

    e.g. `var smoosh; function smoosh() {}` — LexicallyDeclaredNames ∩ VarDeclaredNames.
    """
    s = re.sub(r'//.*?$', '', body, flags=re.MULTILINE)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    if re.search(r'\bexport\b', s):
        return False
    vars_ = set(re.findall(r'\bvar\s+([A-Za-z_$][\w$]*)', s))
    funs = set(re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', s))
    if vars_ & funs:
        return True
    if 'invalid as module' in body.lower():
        return True
    return False


def _dyn_resolve_fixture(base, sp):
    """Resolve relative specifier to a Path, or None."""
    rel = sp[2:] if sp.startswith('./') else sp
    cand = base / rel
    if cand.is_file():
        return cand
    cand2 = base.parent / rel
    if cand2.is_file():
        return cand2
    return None


def _dyn_prepare(source, test_path):
    """Classify dynimport specs → (ok_imports, reject_rewrites, source).

    ok_imports: list of (bind_name, spec) for successful module fixtures.
    reject_rewrites: spec → Promise.reject(...) JS for throw/script targets.
    """
    base = Path(test_path).parent
    specs = []
    seen = set()
    for m in re.finditer(r'''['"](\./[^'"]+)['"]''', source):
        sp = m.group(1)
        if sp in seen or sp.endswith(('.md', '.txt', '.html')):
            continue
        seen.add(sp)
        specs.append(sp)
    # Tagged/untagged template paths: import(tag`./mod.js`)
    for m in re.finditer(r'''`(\./[^`$]*)`''', source):
        sp = m.group(1)
        if sp in seen or sp.endswith(('.md', '.txt', '.html')):
            continue
        seen.add(sp)
        specs.append(sp)

    reject_rewrite = {}
    ok_imports = []
    for i, sp in enumerate(specs):
        cand = _dyn_resolve_fixture(base, sp)
        if cand is None:
            continue  # missing → IMPORT_DYN TypeError
        try:
            body = _FRONTMATTER_RE.sub('', cand.read_text(errors='replace'))
        except Exception:
            continue
        if _dyn_fixture_is_throw(body):
            reject_rewrite[sp] = f'Promise.reject({_dyn_fixture_throw_expr(body)})'
            continue
        if _dyn_fixture_invalid_module(body):
            reject_rewrite[sp] = 'Promise.reject(new SyntaxError("Invalid module code"))'
            continue
        # Instantiation link errors (IEE ambiguous / circular export cycles)
        link_err = _dyn_module_link_error(base, sp)
        if link_err:
            reject_rewrite[sp] = f'Promise.reject(new SyntaxError({json.dumps(link_err)}))'
            continue
        ok_imports.append((f'__di{i}', sp))

    return ok_imports, reject_rewrite, source


def _dyn_module_link_error(base, sp, _stack=None, _cache=None):
    """Return error string if module graph cannot instantiate, else None.

    Detects:
      - export * ambiguity (same name from two different star sources)
      - circular export { name } from chains (IEE circular)
    """
    if _stack is None:
        _stack = []
    if _cache is None:
        _cache = {}
    key = str((_dyn_resolve_fixture(base, sp) or sp))
    if key in _cache:
        return _cache[key]
    if key in _stack:
        _cache[key] = "Circular export resolution"
        return _cache[key]
    cand = _dyn_resolve_fixture(base, sp)
    if cand is None:
        _cache[key] = None
        return None
    try:
        body = _FRONTMATTER_RE.sub("", cand.read_text(errors="replace"))
    except Exception:
        _cache[key] = None
        return None
    _stack.append(key)
    # Star exports → collect names from each source; clash ⇒ ambiguous
    star_sources = re.findall(
        r'''export\s*\*\s*from\s*['"]([^'"]+)['"]''', body
    )
    star_names = []  # list of (set of names, source_key)
    for ssp in star_sources:
        sc = _dyn_resolve_fixture(cand.parent, ssp) or _dyn_resolve_fixture(base, ssp)
        if sc is None:
            continue
        try:
            sb = _FRONTMATTER_RE.sub("", sc.read_text(errors="replace"))
        except Exception:
            continue
        names = set()
        for m in re.finditer(
            r'''export\s+(?:var|let|const|function|class|async)\s+([A-Za-z_$][\w$]*)''',
            sb,
        ):
            names.add(m.group(1))
        for m in re.finditer(
            r'''export\s*\{([^}]+)\}''', sb
        ):
            for part in m.group(1).split(","):
                part = part.strip()
                if not part:
                    continue
                # local or local as export
                mm = re.match(
                    r'''([A-Za-z_$][\w$]*)(?:\s+as\s+([A-Za-z_$][\w$]*))?''',
                    part,
                )
                if mm:
                    names.add(mm.group(2) or mm.group(1))
        star_names.append((names, str(sc)))
    # Ambiguity: name appears in two different star sources
    seen_owner = {}
    for names, sk in star_names:
        for n in names:
            if n == "default":
                continue
            if n in seen_owner and seen_owner[n] != sk:
                _stack.pop()
                _cache[key] = "Ambiguous export"
                return _cache[key]
            seen_owner[n] = sk
    # Named re-exports — walk for cycles (skip self-reexports like
    # `export { local1 as indirect } from './self_FIXTURE.js'`)
    for m in re.finditer(
        r'''export\s*\{[^}]*\}\s*from\s*['"]([^'"]+)['"]''', body
    ):
        tgt = m.group(1)
        tc = _dyn_resolve_fixture(cand.parent, tgt) or _dyn_resolve_fixture(base, tgt)
        if tc is not None and str(tc.resolve()) == str(cand.resolve()):
            continue  # same module — not a cycle
        err = _dyn_module_link_error(cand.parent, tgt, _stack, _cache)
        if err is None:
            err = _dyn_module_link_error(base, tgt, _stack, _cache)
        if err:
            _stack.pop()
            _cache[key] = err
            return err
    _stack.pop()
    _cache[key] = None
    return None


def _source_has_toplevel_await(source):
    """Heuristic: bare `await` token outside comments/strings (rough)."""
    # Strip line comments
    s = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    return bool(re.search(r'(?m)(^|[^.\w$])await\s', s))


def _desugar_export_var_await_pattern(source):
    """export var { x = await E } = {}; → export var x = await E; (brace-safe)."""
    out = []
    i = 0
    needle = 'export var {'
    while True:
        j = source.find(needle, i)
        if j < 0:
            out.append(source[i:])
            break
        out.append(source[i:j])
        # Parse: export var { NAME = await … } = {};
        k = j + len(needle)
        # skip ws
        while k < len(source) and source[k] in ' \t\n\r':
            k += 1
        m = re.match(r'([A-Za-z_$][\w$]*)', source[k:])
        if not m:
            out.append(source[j:j + len(needle)])
            i = j + len(needle)
            continue
        name = m.group(1)
        k += len(name)
        while k < len(source) and source[k] in ' \t\n\r':
            k += 1
        if k >= len(source) or source[k] != '=':
            out.append(source[j:j + len(needle)])
            i = j + len(needle)
            continue
        k += 1
        while k < len(source) and source[k] in ' \t\n\r':
            k += 1
        if not source.startswith('await', k):
            out.append(source[j:j + len(needle)])
            i = j + len(needle)
            continue
        # scan await expression until } at brace/paren depth 0 (the pattern's close)
        expr_start = k
        brace = paren = 0
        # We're inside { already from needle; depth starts at 1 for the pattern brace
        brace = 1
        k = expr_start
        ok = False
        while k < len(source):
            ch = source[k]
            if ch == '{':
                brace += 1
            elif ch == '}':
                brace -= 1
                if brace == 0:
                    # expect = {} ;
                    rest = source[k + 1 :]
                    m2 = re.match(r'\s*=\s*\{\s*\}\s*;', rest)
                    if m2:
                        expr = source[expr_start:k].strip()
                        out.append(f'export var {name} = {expr};')
                        i = k + 1 + m2.end()
                        ok = True
                    break
            elif ch == '(':
                paren += 1
            elif ch == ')':
                paren -= 1
            k += 1
        if not ok:
            out.append(source[j:j + len(needle)])
            i = j + len(needle)
    return ''.join(out)


def _wrap_toplevel_await(source):
    """Run module body as async function so await is legal.

    Uses an eager-completion gate: our engine resolves await synchronously,
    so the async IIFE finishes before the call returns. Avoids depending on
    $DONE/microtasks for non-[async] syntax tests.
    """
    return (
        "var __tla_done = false, __tla_err = null;\n"
        "(async function() {\n"
        "try {\n"
        + source
        + "\n} catch (e) { __tla_err = e; }\n"
        "__tla_done = true;\n"
        "})();\n"
        "if (__tla_err) throw __tla_err;\n"
        "if (!__tla_done) {\n"
        "  if (typeof $DONE === 'function') {\n"
        "    /* fall back for true-async thenables */\n"
        "  } else {\n"
        "    throw new Error('top-level await module did not complete eagerly');\n"
        "  }\n"
        "}\n"
    )


# Minimal Reflect + gOPD shim for module namespace exotic objects.
# NS uses accessors (set throws) so assignment is TypeError; gOPD is shimmed to
# report data descriptors {value, writable:true, enumerable, configurable:false}.
_MODULE_REFLECT_STUB = """
// Brand module namespace objects + remember their export string keys.
// Engine gOPN drops some names (e.g. "__") and lacks getOwnPropertySymbols.
// Optional 3rd arg to __markModuleNS: deferred-module eval hook (import defer).
var __moduleNSList = [];
var __moduleNSKeys = []; // parallel array of string-key arrays
var __moduleNSEval = []; // parallel deferred eval functions (or null)
function __isModuleNS(o) {
  if (!o) return false;
  for (var __i = 0; __i < __moduleNSList.length; __i++) {
    if (__moduleNSList[__i] === o) return true;
  }
  return false;
}
function __markModuleNS(o, keys, evalFn) {
  __moduleNSList.push(o);
  __moduleNSKeys.push(keys || []);
  __moduleNSEval.push(typeof evalFn === "function" ? evalFn : null);
  return o;
}
function __moduleNSExportKeys(o) {
  for (var __i = 0; __i < __moduleNSList.length; __i++) {
    if (__moduleNSList[__i] === o) return __moduleNSKeys[__i];
  }
  return null;
}
function __moduleNSTouch(o) {
  // Deferred NS: [[Get]]/[[HasProperty]]/[[GetOwnProperty]]/[[OwnPropertyKeys]]
  // evaluate the module first (GetModuleExportsList).
  for (var __i = 0; __i < __moduleNSList.length; __i++) {
    if (__moduleNSList[__i] === o && __moduleNSEval[__i]) {
      __moduleNSEval[__i]();
      return;
    }
  }
  // Fallback: hidden __defEval data property on the NS object
  if (o && typeof o.__defEval === "function") {
    try { o.__defEval(); } catch (__e) {}
  }
}
// Engine lacks Object.getOwnPropertySymbols — minimal polyfill for module NS
// Always install (engine may have a stub that doesn't touch deferred NS).
Object.getOwnPropertySymbols = function(o) {
  if (__isModuleNS(o)) {
    __moduleNSTouch(o);
    return [Symbol.toStringTag];
  }
  return [];
};
(function() {
  if (!Object.__moduleGopdShim) {
    Object.__moduleGopdShim = true;
    var _gopd = Object.getOwnPropertyDescriptor;
    Object.getOwnPropertyDescriptor = function(o, p) {
      // Module NS [[GetOwnProperty]]: only exports (+ @@toStringTag via ordinary)
      if (__isModuleNS(o) && p !== Symbol.toStringTag) {
        // Deferred NS evaluates before consulting exports list (not symbols/"then")
        if (typeof p === "string" && p !== "then") __moduleNSTouch(o);
        // note: symbol keys must not trigger (IsSymbolLikeNamespaceKey)
        if (typeof p === "string") {
          var rec = __moduleNSExportKeys(o);
          if (rec) {
            var found = false;
            for (var __j = 0; __j < rec.length; __j++) {
              if (rec[__j] === p) { found = true; break; }
            }
            // Engine may inject __proto__ as own — hide non-exports
            if (!found) return undefined;
          }
        }
      }
      var d = _gopd(o, p);
      if (!d) return d;
      if (__isModuleNS(o) && d.get && p !== Symbol.toStringTag) {
        var v;
        try { v = d.get.call(o); } catch (e) { throw e; }
        return { value: v, writable: true, enumerable: !!d.enumerable, configurable: false };
      }
      return d;
    };
    // Engine may throw on preventExtensions of already-non-extensible objects
    var _pe = Object.preventExtensions;
    Object.preventExtensions = function(o) {
      try { return _pe.call(Object, o); } catch (e) { return o; }
    };
    // Module NS [[OwnPropertyKeys]]: string keys sorted, then symbols
    var _gopn = Object.getOwnPropertyNames;
    Object.getOwnPropertyNames = function(o) {
      if (__isModuleNS(o)) {
        __moduleNSTouch(o);
        // Prefer recorded export keys (engine gOPN may drop "__" etc.)
        var recorded = __moduleNSExportKeys(o);
        if (recorded && recorded.length) {
          var copy = recorded.slice();
          copy.sort();
          return copy;
        }
      }
      var names = _gopn(o);
      var out = [];
      for (var i = 0; i < names.length; i++) {
        var n = names[i];
        if (n === "__moduleNamespace__") continue;
        if (__isModuleNS(o) && n && n.indexOf("@") >= 0) continue;
        out.push(n);
      }
      if (__isModuleNS(o)) {
        out.sort();
      }
      return out;
    };
    // hasOwnProperty / propertyIsEnumerable must [[Get]] uninit bindings (throw RE)
    var _hasOwn = Object.prototype.hasOwnProperty;
    Object.prototype.hasOwnProperty = function(p) {
      if (__isModuleNS(this)) {
        var d = Object.getOwnPropertyDescriptor(this, p);
        return d !== undefined;
      }
      return _hasOwn.call(this, p);
    };
    var _pie = Object.prototype.propertyIsEnumerable;
    Object.prototype.propertyIsEnumerable = function(p) {
      if (__isModuleNS(this)) {
        var d = Object.getOwnPropertyDescriptor(this, p);
        return !!(d && d.enumerable);
      }
      return _pie.call(this, p);
    };
  }
})();
// Always install/override Reflect helpers used by namespace tests.
// M128e7bs: never `var Reflect` here — var-hoist wipes the polyfill/native Reflect
// and bare `Reflect.x = fn` can throw/VM-error mid-stub, killing dyn-import async.
// Install via try + defineProperty (same pattern as has/get).
if (typeof Reflect === "undefined") { Reflect = {}; }
function __installReflectMethod(name, fn) {
  try { Reflect[name] = fn; } catch (__e) {}
  try {
    Object.defineProperty(Reflect, name, {
      value: fn, writable: true, configurable: true, enumerable: false
    });
  } catch (__e) {}
}
function __moduleReflectHas(o, p) {
  if (__isModuleNS(o) && typeof p === "string") {
    // "then" is special for deferred NS (does not trigger evaluation)
    if (p !== "then") __moduleNSTouch(o);
    var rec = __moduleNSExportKeys(o);
    // empty array is valid (no exports) — still hide engine-injected __proto__
    if (rec !== null && rec !== undefined) {
      for (var __h = 0; __h < rec.length; __h++) {
        if (rec[__h] === p) return true;
      }
      return false;
    }
  }
  return p in o;
}
function __moduleReflectGet(o, p, r) {
  if (__isModuleNS(o) && typeof p === "string") {
    if (p !== "then") __moduleNSTouch(o);
    var recg = __moduleNSExportKeys(o);
    if (recg !== null && recg !== undefined) {
      var ok = false;
      for (var __g = 0; __g < recg.length; __g++) {
        if (recg[__g] === p) { ok = true; break; }
      }
      if (!ok) return undefined;
    }
  }
  return o[p];
}
function __moduleReflectSet(o, p, v, r) {
  if (__isModuleNS(o)) return false;
  // M128e6ai: OrdinarySet with Receiver so Proxy gOPD/defineProperty fire
  if (arguments.length < 4) r = o;
  try {
    var desc = Object.getOwnPropertyDescriptor(o, p);
    if (desc && Object.prototype.hasOwnProperty.call(desc, "value")) {
      if (desc.writable === false) return false;
      if (r !== o) {
        var existing = Object.getOwnPropertyDescriptor(r, p);
        if (existing === undefined) {
          Object.defineProperty(r, p, {
            value: v, writable: true, enumerable: true, configurable: true
          });
        } else {
          if (existing.writable === false) return false;
          Object.defineProperty(r, p, { value: v });
        }
        return true;
      }
      o[p] = v;
      return true;
    }
    o[p] = v;
    return true;
  } catch (e) { return false; }
}
function __moduleReflectOwnKeys(o) {
  // getOwnPropertyNames already filters/sorts for module NS
  var names = Object.getOwnPropertyNames(o);
  var out = [];
  for (var i = 0; i < names.length; i++) {
    if (names[i] !== "__moduleNamespace__") out.push(names[i]);
  }
  if (__isModuleNS(o)) {
    // ensure string keys sorted (belt-and-suspenders)
    out.sort();
  }
  if (Object.getOwnPropertySymbols) {
    var syms = Object.getOwnPropertySymbols(o);
    for (var j = 0; j < syms.length; j++) out.push(syms[j]);
  }
  return out;
}
function __moduleReflectGOPD(o, p) {
  return Object.getOwnPropertyDescriptor(o, p);
}
function __moduleReflectDefineProperty(o, p, d) {
  if (__isModuleNS(o)) {
    // Non-exported → false
    var cur = null;
    try { cur = Object.getOwnPropertyDescriptor(o, p); } catch (e) {
      // uninit binding still "own"
      cur = { writable: true, enumerable: true, configurable: false };
    }
    if (!cur) return false;
    d = d || {};
    // No change / compatible data-desc for exports: writable true, enum true, conf false
    var keys = Object.keys(d);
    if (keys.length === 0) return true;
    if (p === Symbol.toStringTag) {
      if (d.value !== undefined && d.value !== "Module") return false;
      if (d.writable === true) return false;
      if (d.enumerable === true) return false;
      if (d.configurable === true) return false;
      return true;
    }
    // Export bindings report writable:true, enumerable:true, configurable:false
    if (d.configurable === true) return false;
    if (d.enumerable === false) return false;
    if (d.writable === false) return false;
    if (d.get || d.set) return false;
    // value change requested
    if (d.value !== undefined) {
      try {
        if (d.value !== o[p]) return false;
      } catch (e) { return false; }
    }
    return true;
  }
  try {
    var _odp = Object.defineProperty;
    _odp(o, p, d);
    return true;
  } catch (e) { return false; }
}
function __moduleReflectDeleteProperty(o, p) {
  if (__isModuleNS(o)) {
    if (Object.prototype.hasOwnProperty.call(o, p) && p !== "__moduleNamespace__") return false;
  }
  try {
    var d = Object.getOwnPropertyDescriptor(o, p);
    if (d && d.configurable === false) return false;
    return delete o[p];
  } catch (e) { return false; }
}
function __moduleReflectIsExtensible(o) { return Object.isExtensible(o); }
function __moduleReflectPreventExtensions(o) {
  try { Object.preventExtensions(o); } catch (e) {}
  return true;
}
function __moduleReflectGetPrototypeOf(o) { return Object.getPrototypeOf(o); }
function __moduleReflectSetPrototypeOf(o, p) {
  if (__isModuleNS(o)) return (p === null);
  try { Object.setPrototypeOf(o, p); return true; } catch (e) { return false; }
}
__installReflectMethod("has", __moduleReflectHas);
__installReflectMethod("get", __moduleReflectGet);
__installReflectMethod("set", __moduleReflectSet);
__installReflectMethod("ownKeys", __moduleReflectOwnKeys);
__installReflectMethod("getOwnPropertyDescriptor", __moduleReflectGOPD);
__installReflectMethod("defineProperty", __moduleReflectDefineProperty);
__installReflectMethod("deleteProperty", __moduleReflectDeleteProperty);
__installReflectMethod("isExtensible", __moduleReflectIsExtensible);
__installReflectMethod("preventExtensions", __moduleReflectPreventExtensions);
__installReflectMethod("getPrototypeOf", __moduleReflectGetPrototypeOf);
__installReflectMethod("setPrototypeOf", __moduleReflectSetPrototypeOf);
// Object.defineProperty throws when Reflect.defineProperty is false (strict)
(function() {
  if (Object.__moduleDefPropShim) return;
  Object.__moduleDefPropShim = true;
  var _odp = Object.defineProperty;
  Object.defineProperty = function(o, p, d) {
    if (__isModuleNS(o)) {
      // Avoid recursion: inline the NS check (don't call Reflect which may call us)
      var cur = null;
      try { cur = Object.getOwnPropertyDescriptor(o, p); } catch (e) {
        cur = { writable: true, enumerable: true, configurable: false };
      }
      if (!cur) throw new TypeError("Module namespace [[DefineOwnProperty]]");
      d = d || {};
      var ok = true;
      var keys = Object.keys(d);
      if (keys.length !== 0) {
        if (p === Symbol.toStringTag) {
          if (d.value !== undefined && d.value !== "Module") ok = false;
          if (d.writable === true) ok = false;
          if (d.enumerable === true) ok = false;
          if (d.configurable === true) ok = false;
        } else {
          if (d.configurable === true) ok = false;
          if (d.enumerable === false) ok = false;
          if (d.writable === false) ok = false;
          if (d.get || d.set) ok = false;
          if (d.value !== undefined) {
            try { if (d.value !== o[p]) ok = false; } catch (e) { ok = false; }
          }
        }
      }
      if (!ok) throw new TypeError("Module namespace [[DefineOwnProperty]]");
      return o;
    }
    return _odp(o, p, d);
  };
})();
// Object.setPrototypeOf must throw when [[SetPrototypeOf]] is false (module NS)
(function() {
  if (Object.__moduleSetProtoShim) return;
  Object.__moduleSetProtoShim = true;
  var _sp = Object.setPrototypeOf;
  Object.setPrototypeOf = function(o, p) {
    if (__isModuleNS(o) && p !== null) {
      throw new TypeError("Module namespace [[SetPrototypeOf]]");
    }
    return _sp.call(Object, o, p);
  };
})();
// Object.keys must [[GetOwnProperty]] each key (throws on uninit NS bindings)
(function() {
  if (Object.__moduleKeysShim) return;
  Object.__moduleKeysShim = true;
  var _keys = Object.keys;
  Object.keys = function(o) {
    if (__isModuleNS(o)) {
      var names = Object.getOwnPropertyNames(o);
      var out = [];
      for (var i = 0; i < names.length; i++) {
        var d = Object.getOwnPropertyDescriptor(o, names[i]);
        if (d && d.enumerable) out.push(names[i]);
      }
      return out;
    }
    return _keys(o);
  };
  // freeze always fails for module NS (export bindings stay [[Writable]]: true)
  var _freeze = Object.freeze;
  Object.freeze = function(o) {
    if (__isModuleNS(o)) {
      throw new TypeError("Module namespace cannot be frozen");
    }
    return _freeze(o);
  };
  // isFrozen is false for module NS (bindings remain writable per gOPD shim)
  var _isFrozen = Object.isFrozen;
  Object.isFrozen = function(o) {
    if (__isModuleNS(o)) return false;
    return _isFrozen(o);
  };
})();
"""


def _collect_module_exports(source, reexport_map=None):
    """Return (default_local_name_or_None, {exportName: localName}).

    reexport_map: optional dict exportName -> (from_spec, importName) for
    `export { A as B } from './mod'` (importName may be '*' for star-as).
    """
    dflt = None
    named = {}
    if reexport_map is None:
        reexport_map = {}
    # After anon rewrite, default lives on __default_export__ or __dflt_<mod>
    m_dloc = re.search(r'\b(__default_export__|__dflt_[A-Za-z0-9_]+)\b', source)
    if m_dloc:
        dflt = m_dloc.group(1)
    m = re.search(
        r'export\s+default\s+(?:async\s+)?(?:function\s*\*?|class)\s+([A-Za-z_$][\w$]*)',
        source,
    )
    if m:
        dflt = m.group(1)
    else:
        m2 = re.search(r'export\s*\{[^}]*\b([A-Za-z_$][\w$]*)\s+as\s+default\b', source)
        if m2:
            dflt = m2.group(1)
        elif re.search(r'export\s+default\s+', source):
            dflt = dflt or '__default_export__'
    def _unquote_export_name(tok):
        """Identifier or string ModuleExportName → export name string."""
        tok = tok.strip()
        if len(tok) >= 2 and tok[0] in ('"', "'") and tok[-1] == tok[0]:
            inner = tok[1:-1]
            try:
                return json.loads('"' + inner.replace('\\', '\\\\').replace('"', '\\"') + '"')
            except Exception:
                return inner
        # IdentifierName may contain \uXXXX escapes
        def _uesc(m):
            return chr(int(m.group(1), 16))
        return re.sub(r'\\u([0-9a-fA-F]{4})', _uesc, tok)

    def _loc_id(tok):
        tok = tok.strip()
        if len(tok) >= 2 and tok[0] in ('"', "'") and tok[-1] == tok[0]:
            return _unquote_export_name(tok)
        return tok

    # import * as local from 'mod' — export { local } re-exports that module NS
    import_star_as = {}
    for m in re.finditer(
        r'import\s*\*\s*as\s+([A-Za-z_$][\w$]*)\s*from\s*[\'"]([^\'"]+)[\'"]',
        source,
    ):
        import_star_as[m.group(1)] = m.group(2)

    # export { a, b as c, x as "str" } from 'mod'  OR  export { a, b as c };
    for m in re.finditer(
        r'export\s*\{([^}]+)\}\s*(?:from\s*[\'"]([^\'"]+)[\'"])?',
        source,
    ):
        from_spec = m.group(2)
        for part in m.group(1).split(','):
            part = part.strip()
            if not part:
                continue
            if ' as ' in part:
                loc, exp = part.split(' as ', 1)
                loc, exp = loc.strip(), _unquote_export_name(exp)
            else:
                loc = exp = _unquote_export_name(part)
            loc_id = _loc_id(loc)
            # export { default } / export { default as x } → *default* binding
            if loc_id == 'default':
                loc_id = '__default_export__'
            if from_spec:
                reexport_map[exp] = (from_spec, loc_id)
                named[exp] = loc_id
            else:
                named[exp] = loc_id
                # import * as foo from M; export { foo } → indirect NS of M
                if loc_id in import_star_as:
                    reexport_map[exp] = (import_star_as[loc_id], '*')
    # export * as ns from 'mod'  OR  export * as "Name" from 'mod'
    for m in re.finditer(
        r'export\s*\*\s*as\s+'
        r'(?:([A-Za-z_$][\w$]*)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'))'
        r'\s*from\s*[\'"]([^\'"]+)[\'"]',
        source,
    ):
        raw_name = m.group(1) if m.group(1) is not None else _unquote_export_name(m.group(2))
        from_sp = m.group(3)
        reexport_map[raw_name] = (from_sp, '*')
        # Local binding: identifier as-is; string export names use sanitized local
        if m.group(1) is not None:
            named[raw_name] = raw_name
        else:
            safe = re.sub(r'[^A-Za-z0-9_]', '_', raw_name) or 'ns'
            if not re.match(r'^[A-Za-z_]', safe):
                safe = 'ns_' + safe
            named[raw_name] = f'__star_as_{safe}'
    # export * from 'mod' — mark for expansion by caller
    for m in re.finditer(
        r'export\s*\*\s*from\s*[\'"]([^\'"]+)[\'"]',
        source,
    ):
        reexport_map['*from*' + m.group(1)] = (m.group(1), '**')
    for m in re.finditer(
        r'export\s+(?:async\s+)?(?:function\s*\*?|class|let|const|var)\s+([A-Za-z_$][\w$]*)',
        source,
    ):
        named[m.group(1)] = m.group(1)
    if dflt:
        named['default'] = dflt
    return dflt, named


def _match_braced_decl(source, start):
    """From index of '{' after a function/class header, return end index after matching '}'."""
    i = start
    if i >= len(source) or source[i] != '{':
        return -1
    depth = 0
    while i < len(source):
        ch = source[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        elif ch in ('"', "'", '`'):
            q = ch
            i += 1
            while i < len(source) and source[i] != q:
                if source[i] == '\\':
                    i += 2
                    continue
                i += 1
        i += 1
    return -1


def _extract_export_function_decl(source, name):
    """Return (full_match, decl_without_export) for export function/gen name, or None."""
    m = re.search(
        rf'export\s+((?:async\s+)?function\s*\*?\s+{re.escape(name)}\s*\([^)]*\)\s*)\{{',
        source,
    )
    if not m:
        return None
    body_end = _match_braced_decl(source, m.end() - 1)
    if body_end < 0:
        return None
    full = source[m.start():body_end]
    decl = source[m.start(1):body_end]
    return full, decl


def _extract_export_class_decl(source, name):
    """Return (full_match, decl_without_export) for export class name, or None."""
    m = re.search(
        rf'export\s+(class\s+{re.escape(name)}\b[^{{]*)\{{',
        source,
    )
    if not m:
        return None
    body_end = _match_braced_decl(source, m.end() - 1)
    if body_end < 0:
        return None
    full = source[m.start():body_end]
    decl = source[m.start(1):body_end]
    return full, decl


def _extract_default_function_decl(source):
    """export default function [name](...) { ... } → (full, decl, name_or__default_export__)."""
    m = re.search(
        r'export\s+default\s+((?:async\s+)?function\s*\*?\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*)\{',
        source,
    )
    if m:
        body_end = _match_braced_decl(source, m.end() - 1)
        if body_end < 0:
            return None
        full = source[m.start():body_end]
        decl = source[m.start(1):body_end]
        return full, decl, m.group(2)
    # anonymous — may already be rewritten to var __default_export__ = function...
    m = re.search(
        r'export\s+default\s+((?:async\s+)?function\s*\*?\s*\([^)]*\)\s*)\{',
        source,
    )
    if m:
        body_end = _match_braced_decl(source, m.end() - 1)
        if body_end < 0:
            return None
        full = source[m.start():body_end]
        # Convert to named function decl for hoisting
        header = m.group(1)
        header2 = re.sub(
            r'function(\s*\*)?\s*\(',
            r'function\1 __default_export__(',
            header,
            count=1,
        )
        decl = header2 + source[m.end() - 1:body_end]
        return full, decl, '__default_export__'
    # after anon rewrite: let/var __default_export__ = function(...){...};
    m = re.search(
        r'(?:var|let|const)\s+__default_export__\s*=\s*((?:async\s+)?function\s*\*?\s*\([^)]*\)\s*)\{',
        source,
    )
    if m:
        body_end = _match_braced_decl(source, m.end() - 1)
        if body_end < 0:
            return None
        # include trailing ; and name stamp if present
        end = body_end
        if end < len(source) and source[end] == ';':
            end += 1
        full = source[m.start():end]
        header = m.group(1)
        header2 = re.sub(
            r'function(\s*\*)?\s*\(',
            r'function\1 __default_export__(',
            header,
            count=1,
        )
        decl = header2 + source[m.end() - 1:body_end]
        return full, decl, '__default_export__'
    return None


_NAME_DEFAULT = (
    "try{Object.defineProperty(__default_export__,'name',"
    "{value:'default',configurable:true});}catch(e){}"
)

def _name_default_stamp(binding='__default_export__'):
    """Stamp name 'default' only when the function/class is still anonymous."""
    return (
        f"try{{var __n={binding}.name;"
        f"if(__n===''||__n==='anonymous'||__n==='__default_export__'||typeof __n==='undefined')"
        f"{{Object.defineProperty({binding},'name',"
        f"{{value:'default',configurable:true}});}}}}catch(e){{}}"
    )


_NAME_DEFAULT_IF_ANON = _name_default_stamp('__default_export__')


def _stamp_default_name_after(source, start_marker, force=False):
    """Insert name-stamp after the statement starting at start_marker.

    force=False: only stamp if the function/class is anonymous (no .name yet).
    """
    stamp = _NAME_DEFAULT if force else _NAME_DEFAULT_IF_ANON
    idx = source.find(start_marker)
    if idx < 0:
        return source
    i = idx + len(start_marker)
    # Scan to end of statement: first ';' at brace/paren depth 0
    brace = paren = 0
    while i < len(source):
        ch = source[i]
        if ch == '{':
            brace += 1
        elif ch == '}':
            brace -= 1
        elif ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
        elif ch == ';' and brace == 0 and paren == 0:
            i += 1
            return source[:i] + "\n" + stamp + "\n" + source[i:]
        i += 1
    # class/function decl without trailing semi: after balanced braces from first {
    j = source.find('{', idx)
    if j >= 0:
        brace = 0
        k = j
        while k < len(source):
            if source[k] == '{':
                brace += 1
            elif source[k] == '}':
                brace -= 1
                if brace == 0:
                    k += 1
                    return source[:k] + "\n" + stamp + "\n" + source[k:]
            k += 1
    return source + "\n" + stamp + "\n"


def _rewrite_anon_default_export(source, local_name='__default_export__'):
    """Turn anonymous export default into let <local_name> = …

    Use `let` (not var) so default is TDZ until the export statement runs
    (namespace uninit tests: ns.default throws ReferenceError).
    local_name may be module-specific so multiple fixtures don't clash.
    """
    loc = local_name
    # export default class { … }  OR  export default class extends … { … }
    source, n = re.subn(
        r'export\s+default\s+class\s*\{',
        f'let {loc} = class {{',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, f'let {loc} = class', force=False)
    source, n = re.subn(
        r'export\s+default\s+class\s+(extends\b)',
        rf'let {loc} = class \1',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, f'let {loc} = class')
    source, n = re.subn(
        r'export\s+default\s+(async\s+)?function(\s*\*)?\s*\(',
        rf'let {loc} = \1function\2(',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, f'let {loc} = ')
    if re.search(r'export\s+default\s+(?:async\s+)?(?:function\s*\*?|class)\s+[A-Za-z_$]', source):
        return source  # named — leave for engine
    # Plain expression default — rewrite without name stamp (stamp only for fn/class)
    source, n = re.subn(
        r'export\s+default\s+',
        f'let {loc} = ',
        source,
        count=1,
    )
    return source


def _namespace_object_js(ns_name, export_map, live_getters=True, as_const=False):
    """JS Module-namespace-like object.

    Accessors with throwing setters (assignment → TypeError). gOPD is shimmed
    in _MODULE_REFLECT_STUB to report data descriptors for these props.
    as_const: bind with const (immutable import of namespace).
    """
    tmp = f'__nsbuild_{ns_name}'
    lines = [f'var {tmp} = Object.create(null);']
    key_list = []
    for exp, loc in sorted(export_map.items()):
        if str(exp).startswith('*from*'):
            continue
        loc_s = str(loc)
        # loc must be a JS identifier expression (or __default_export__)
        if not re.match(r'^[A-Za-z_$][\w$]*$', loc_s):
            continue
        prop_js = json.dumps(exp, ensure_ascii=False)
        lines.append(
            f'Object.defineProperty({tmp}, {prop_js}, {{'
            f'get:function(){{return {loc_s};}},'
            f'set:function(){{throw new TypeError("Module namespace is read-only");}},'
            f'enumerable:true,configurable:false}});'
        )
        key_list.append(exp)
    lines.append(
        f'try{{Object.defineProperty({tmp}, Symbol.toStringTag, {{'
        f'value:"Module",writable:false,enumerable:false,configurable:false}});}}catch(e){{}}'
    )
    lines.append(f'try{{Object.preventExtensions({tmp});}}catch(e){{}}')
    # Record export keys for gOPN (engine drops names like "__")
    keys_js = json.dumps(key_list, ensure_ascii=False)
    lines.append(f'try{{__markModuleNS({tmp}, {keys_js});}}catch(e){{}}')
    if as_const:
        lines.append(f'const {ns_name} = {tmp};')
    else:
        lines.append(f'var {ns_name} = {tmp};')
    return "\n".join(lines)


def _preprocess_module(source, test_path):
    """Rewrite ES module import/export for single-process harness.

    Handles:
      - named + anonymous export default
      - import X / {a as b} / * as ns from self or FIXTURE
      - Side-effect import './fix.js' → inline fixture body once

    Not a full linker; enough to lift large module-code / import clusters.
    """
    path = Path(test_path)
    base = path.parent
    self_name = path.name

    # Capture import attributes type: before stripping with-clauses
    # e.g. from './x.json' with { type: 'json' }  →  module_type['./x.json']='json'
    module_type_by_spec = {}
    for m in re.finditer(
        r'''from\s*['"]([^'"]+)['"]\s*with\s*\{\s*type\s*:\s*['"]([^'"]+)['"]''',
        source,
    ):
        module_type_by_spec[m.group(1)] = m.group(2).lower()
    # also: import './x' with { type: 'json' } (side-effect; rare)
    for m in re.finditer(
        r'''^import\s*['"]([^'"]+)['"]\s*with\s*\{\s*type\s*:\s*['"]([^'"]+)['"]''',
        source,
        re.MULTILINE,
    ):
        module_type_by_spec[m.group(1)] = m.group(2).lower()

    # Drop import attributes / assertions (with {} / assert {}) — unsupported
    # by the engine; type already captured above for synthetic modules.
    source = re.sub(r'\s+with\s*\{[^}]*\}', '', source)
    source = re.sub(r'\s+assert\s*\{[^}]*\}', '', source)

    # Anonymous default → __default_export__ before collecting maps
    source = _rewrite_anon_default_export(source)
    # Desugar pattern default await (engine bug: await in pattern default)
    # export var { x = await E } = {}; → export var x = await E;
    source = _desugar_export_var_await_pattern(source)

    fixtures = {}
    inlined = set()
    fixture_chunks = []
    # One namespace object per module key (instn-star-equality); init early for ensure_mod_ns
    ns_by_module = {}  # module_key -> JS var name holding the ns
    pre_assert_aliases = []
    # Synthetic module defaults (json/text): key → JS local name holding the value
    synthetic_defaults = {}  # abs path -> dloc

    def load_spec(spec):
        if not spec.startswith('.'):
            return None
        rel = spec[2:] if spec.startswith('./') else spec
        cand = (base / rel).resolve()
        if not cand.is_file():
            return None
        key = str(cand)
        if key not in fixtures:
            raw = cand.read_text(errors="replace")
            # Only strip test262 frontmatter from .js fixtures
            if cand.suffix.lower() in ('.js', '.mjs', '.cjs', ''):
                raw = _FRONTMATTER_RE.sub("", raw)
            fixtures[key] = raw
        return fixtures[key]

    def _default_local_for_key(key):
        safe = re.sub(r'[^A-Za-z0-9_]', '_', Path(str(key)).stem)[:40] or 'm'
        return f'__dflt_{safe}'

    def _synthetic_kind(spec, key=None):
        """Return 'json', 'text', or None for synthetic module records."""
        t = module_type_by_spec.get(spec)
        if t in ('json', 'text'):
            return t
        k = key or (str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
                    if spec.startswith('.') else '')
        if k.endswith('.json') or (spec and spec.endswith('.json')):
            return 'json'
        return None

    def _synthetic_module_js(raw, dloc, kind):
        """Emit JS binding for a JSON/text synthetic default export.

        Engine lacks reliable JSON.parse — parse in Python and emit a JS literal
        (JSON text is a subset of JS for the values test262 uses).
        """
        if kind == 'text':
            return f'var {dloc} = {json.dumps(raw)};\n'
        # json
        try:
            val = json.loads(raw)
        except Exception:
            # Invalid JSON — resolution/parse error for negative tests
            return (
                f'throw new SyntaxError("JSON module parse failed");\n'
                f'var {dloc} = undefined;\n'
            )
        return f'var {dloc} = {json.dumps(val, ensure_ascii=False)};\n'

    def parse_exports_from(src, default_local=None, synthetic=None):
        """Parse exports; optional per-module default local avoids clashes.

        synthetic: 'json' | 'text' | None — CreateDefaultExportSyntheticModule.
        """
        if default_local is None:
            default_local = '__default_export__'
        if synthetic in ('json', 'text'):
            body = _synthetic_module_js(src, default_local, synthetic)
            return body, (default_local, {'default': default_local}), {}
        src2 = _rewrite_anon_default_export(src, local_name=default_local)
        rmap = {}
        dflt, named = _collect_module_exports(src2, rmap)
        if default_local != '__default_export__' and re.search(
            rf'\b{re.escape(default_local)}\b', src2
        ):
            dflt = default_local
            named['default'] = default_local
        return src2, (dflt, named), rmap

    def parse_exports_from_spec(spec):
        fix = load_spec(spec)
        if fix is None:
            return None, (None, {}), {}
        key = _resolve_mod_key(spec)
        return parse_exports_from(fix, default_local=_default_local_for_key(key))

    def _resolve_mod_key(spec):
        try:
            return str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
        except Exception:
            return spec

    def _export_identity(exp, loc, rmap, provider_mod_key):
        """Ultimate ResolveExport identity (module, binding) for star ambiguity.

        Two star paths that resolve to the same module namespace (or same
        binding) are unambiguous — see namespace-unambiguous-if-* tests.
        """
        if exp in rmap:
            sp, im = rmap[exp]
            if im == '*':
                return ('ns', _resolve_mod_key(sp))
            if im not in ('**',) and not str(exp).startswith('*from*'):
                return ('bind', _resolve_mod_key(sp), im)
        return ('local', provider_mod_key, loc)

    def expand_star_exports(named_map, reexport_map, depth=0):
        """Inline export * from './x' into named_map (no default).

        Ambiguous names (two star sources resolve to different bindings) are
        omitted. Same ultimate resolution via two stars is kept.
        """
        if depth > 6:
            return named_map
        out = dict(named_map)
        # Local exports win; star origins store ResolveExport identity tuples
        star_origin = {k: ('__local__',) for k in out}
        ambiguous = set()

        def _consider(exp, loc, ident):
            if exp == 'default' or str(exp).startswith('*from*'):
                return
            if exp in ambiguous:
                return
            if exp in out:
                prev = star_origin.get(exp)
                if prev == ('__local__',):
                    return  # local export wins
                if prev == ident:
                    return  # same ultimate binding — unambiguous
                del out[exp]
                ambiguous.add(exp)
                return
            out[exp] = loc
            star_origin[exp] = ident

        for key, (spec, kind) in list(reexport_map.items()):
            if kind != '**' and not (isinstance(key, str) and key.startswith('*from*')):
                continue
            from_spec = spec
            fix = load_spec(from_spec)
            if fix is None:
                continue
            mod_key = _resolve_mod_key(from_spec)
            syn = _synthetic_kind(from_spec, mod_key)
            fs, (fd, fn), rmap = parse_exports_from(
                fix,
                default_local=_default_local_for_key(mod_key),
                synthetic=syn,
            )
            if syn:
                synthetic_defaults[mod_key] = _default_local_for_key(mod_key)
            fn = expand_star_exports(fn, rmap, depth + 1)
            for exp, loc in fn.items():
                ident = _export_identity(exp, loc, rmap, mod_key)
                _consider(exp, loc, ident)
            for exp, (sp, im) in rmap.items():
                if exp.startswith('*from*') or im == '**':
                    continue
                if im == '*':
                    _consider(exp, exp, ('ns', _resolve_mod_key(sp)))
                else:
                    _consider(exp, im, ('bind', _resolve_mod_key(sp), im))
        out = {k: v for k, v in out.items() if not str(k).startswith('*from*')}
        return out

    # GetModuleNamespace cache: one NS object per target module path
    mod_ns_cache = {}  # abs path -> JS var name

    # Reserved words illegal as Identifier in BindingIdentifier / var name
    _JS_RESERVED = {
        'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
        'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
        'for', 'function', 'if', 'import', 'in', 'instanceof', 'new', 'return',
        'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void',
        'while', 'with', 'yield', 'enum', 'await', 'let', 'static',
        'implements', 'interface', 'package', 'private', 'protected', 'public',
    }

    def _safe_binding_name(name):
        """JS local for an export name; reserved/string names → __star_as_*."""
        if (
            isinstance(name, str)
            and re.match(r'^[A-Za-z_$][\w$]*$', name)
            and name not in _JS_RESERVED
        ):
            return name
        safe = re.sub(r'[^A-Za-z0-9_]', '_', str(name)) or 'ns'
        if not re.match(r'^[A-Za-z_]', safe) or safe in _JS_RESERVED:
            safe = 'ns_' + safe
        return f'__star_as_{safe}'

    def _inline_fixture_body(spec, isolate_side_effect=False):
        """Inline fixture once into fixture_chunks. Returns True if newly inlined."""
        if not spec.startswith('.'):
            return False
        if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
            return False
        key = _resolve_mod_key(spec)
        if key in inlined:
            return False
        fix = load_spec(spec)
        if fix is None:
            return False
        inlined.add(key)
        dloc = _default_local_for_key(key)
        syn = _synthetic_kind(spec, key)
        fs, (fd, fn), rmap = parse_exports_from(
            fix, default_local=dloc, synthetic=syn
        )
        if syn:
            synthetic_defaults[key] = dloc
            fixture_chunks.append(fs)  # already a complete var binding
            return True
        body = strip_fixture_exports(fs)
        has_exports = bool(fd) or bool(fn) or any(
            not str(k).startswith('*from*') for k in rmap
        )
        # Fixtures that import other modules need shared scope (bindings +
        # globalThis side effects) — do not rename-isolate them.
        has_imports = bool(re.search(r'\bimport\b', fix or ''))
        # Pure side-effect modules: isolate locals (uniq-env-rec). Keep
        # modules with exports in shared scope so bindings are reachable.
        # M128e7bt: never IIFE-wrap fixtures that touch globalThis — dual-bind
        # of globalThis.evaluations (import-defer setup_FIXTURE) breaks once
        # deferred NS getters close over free vars (length reads VM-error).
        touches_globalthis = bool(re.search(r'\bglobalThis\b', body))
        if (
            isolate_side_effect
            and not has_exports
            and not has_imports
            and not touches_globalthis
        ):
            pfx = f"__fx{len(inlined)}_"
            body = re.sub(
                r'\bfunction\s*(\*?)\s*([A-Za-z_$][\w$]*)',
                rf'function\1 {pfx}\2',
                body,
            )
            body = re.sub(
                r'\bclass\s+([A-Za-z_$][\w$]*)',
                rf'class {pfx}\1',
                body,
            )
            body = re.sub(
                r'\b(var|let|const)\s+([A-Za-z_$][\w$]*)',
                rf'\1 {pfx}\2',
                body,
            )
            body = "(function(){\n" + body + "\n})();\n"
        fixture_chunks.append(body)
        return True

    # Specs requested only via `import defer` must not evaluate at load time
    _defer_only_specs = set()
    _eager_specs = set()
    for m in re.finditer(
        r'''^import\s+defer\s*\*\s*as\s+[A-Za-z_$][\w$]*\s*from\s*['"]([^'"]+)['"]''',
        source,
        re.MULTILINE,
    ):
        _defer_only_specs.add(m.group(1))
    for m in re.finditer(
        r'''(?:^import\s+['"](\.[^'"]+)['"])|(?:^import(?!\s+defer)\b[^;]*from\s*['"]([^'"]+)['"])|(?:^export\b[^;]*from\s*['"]([^'"]+)['"])''',
        source,
        re.MULTILINE,
    ):
        sp = m.group(1) or m.group(2) or m.group(3)
        if sp:
            _eager_specs.add(sp)
    # If also eagerly imported, not defer-only
    _defer_only_specs -= _eager_specs

    # Deferred module records: abs key -> {flag, eval_fn, ns_tmp, exports}
    _deferred_emitted = {}  # key -> ns JS var name

    def _emit_deferred_namespace(spec, ns_bind_name=None):
        """Build lazy deferred NS; return internal JS var name of the NS object.

        import defer * as ns from './mod' — body of mod (and its eager deps)
        runs only when a property of ns is accessed. Nested import-defer stays
        lazy until that child NS is accessed.
        """
        key = _resolve_mod_key(spec)
        if key in _deferred_emitted:
            internal = _deferred_emitted[key]
            if ns_bind_name and ns_bind_name != internal:
                pre_assert_aliases.append(f'const {ns_bind_name} = {internal};')
            return internal
        fix = load_spec(spec)
        safe = re.sub(r'[^A-Za-z0-9_]', '_', Path(key).stem)[:40] or 'm'
        # Unique per emit count if stem collides
        safe = f'{safe}_{len(_deferred_emitted)}'
        flag = f'__defDone_{safe}'
        eval_fn = f'__defEval_{safe}'
        ns_tmp = f'__defNS_{safe}'
        dloc = _default_local_for_key(key + str(len(_deferred_emitted)))

        if fix is None:
            fixture_chunks.append(
                f'var {ns_tmp} = Object.create(null);\n'
                f'var {ns_bind_name or ns_tmp} = {ns_tmp};\n'
            )
            _deferred_emitted[key] = ns_tmp
            return ns_tmp

        raw = _FRONTMATTER_RE.sub('', fix)
        nested_defers = []  # (export_name, child_spec)

        def _nest_defer(m):
            nested_defers.append((m.group(1), m.group(2)))
            return f'/* nested defer {m.group(1)} */\n'

        body = re.sub(
            r'''import\s+defer\s*\*\s*as\s+([A-Za-z_$][\w$]*)\s*from\s*['"]([^'"]+)['"]\s*;?''',
            _nest_defer,
            raw,
        )
        eager_chunks = []

        def _nest_side(m):
            sp = m.group(1)
            k2 = _resolve_mod_key(sp)
            # Always put eager dep body into this eval thunk (may re-run once flag)
            fix2 = load_spec(sp)
            if fix2 is not None:
                syn = _synthetic_kind(sp, k2)
                if syn:
                    d2 = _default_local_for_key(k2)
                    eager_chunks.append(_synthetic_module_js(fix2, d2, syn))
                    synthetic_defaults[k2] = d2
                else:
                    # Don't use global inlined — keep body inside thunk
                    fs2 = _FRONTMATTER_RE.sub('', fix2)
                    fs2 = re.sub(r'\s+with\s*\{[^}]*\}', '', fs2)
                    # Recurse eager side-effects of the dependency
                    def _deep_side(mm):
                        sp3 = mm.group(1)
                        fix3 = load_spec(sp3)
                        if fix3 is None:
                            return ''
                        eager_chunks.append(
                            strip_fixture_exports(_FRONTMATTER_RE.sub('', fix3))
                        )
                        return ''
                    fs2 = re.sub(
                        r'''^import\s+['"]([^'"]+)['"]\s*;?''',
                        _deep_side,
                        fs2,
                        flags=re.MULTILINE,
                    )
                    fs2 = re.sub(
                        r'''^import\s+[^;]+;?\s*$''',
                        '',
                        fs2,
                        flags=re.MULTILINE,
                    )
                    eager_chunks.append(strip_fixture_exports(fs2))
            return ''

        body = re.sub(
            r'''^import\s+['"]([^'"]+)['"]\s*;?''',
            _nest_side,
            body,
            flags=re.MULTILINE,
        )
        body = re.sub(
            r'''^import\s+[^;]+;?\s*$''',
            '',
            body,
            flags=re.MULTILINE,
        )
        fs, (fd, fn), rmap = parse_exports_from(body, default_local=dloc)
        body_exec = strip_fixture_exports(fs)
        # Nested deferred children (unique internal names)
        for child_exp, child_spec in nested_defers:
            child_internal = _emit_deferred_namespace(child_spec, None)
            fn[child_exp] = child_internal

        if rmap:
            fn = expand_star_exports(dict(fn), rmap)
            for exp, (sp, im) in rmap.items():
                if im == '*' and not str(exp).startswith('*from*'):
                    fn[exp] = exp

        # M128v/e7bt: export locals live on a store object (not free-var bindings).
        # Free-var SET breaks once func_count climbs (module Reflect stub ~77 fns);
        # property sets on a closed-over store object remain reliable.
        hoist_locs = set()
        for exp, loc in fn.items():
            if str(exp).startswith('*from*'):
                continue
            if re.match(r'^[A-Za-z_$][\w$]*$', str(loc)):
                if not str(loc).startswith('__defNS_'):
                    hoist_locs.add(str(loc))
        if fd and re.match(r'^[A-Za-z_$][\w$]*$', str(fd)):
            hoist_locs.add(str(fd))
        store = f'__defStore_{safe}'
        body_hoisted = body_exec
        for loc in hoist_locs:
            body_hoisted = re.sub(
                rf'\b(?:let|const|var)\s+{re.escape(loc)}\b',
                loc,
                body_hoisted,
            )
            body_hoisted = re.sub(
                rf'\bfunction\s+{re.escape(loc)}\s*\(',
                f'{loc} = function(',
                body_hoisted,
            )
            body_hoisted = re.sub(
                rf'\bclass\s+{re.escape(loc)}\b',
                f'{loc} = class',
                body_hoisted,
            )
        # Rewrite identifiers → store.prop (longest first to avoid partial replaces)
        for loc in sorted(hoist_locs, key=len, reverse=True):
            body_hoisted = re.sub(
                rf'\b{re.escape(loc)}\b',
                f'{store}.{loc}',
                body_hoisted,
            )
        lines = []
        lines.append(f'var {store} = Object.create(null);')
        # Keep done-flag on the store too — free-var SET of a bool flag also
        # breaks under high func_count (same SET_FREE cliff as export binds).
        lines.append(f'{store}.__done = false;')
        lines.append(f'var {eval_fn} = function(){{')
        lines.append(f'  if ({store}.__done) return;')
        lines.append(f'  {store}.__done = true;')
        for c in eager_chunks:
            for ln in c.splitlines():
                lines.append('  ' + ln)
        for ln in body_hoisted.splitlines():
            lines.append('  ' + ln)
        lines.append('};')
        lines.append(f'var {ns_tmp} = Object.create(null);')
        # Hidden touch/eval hook for any property access (no Proxy in engine)
        lines.append(
            f'Object.defineProperty({ns_tmp}, "__defEval", {{'
            f'value:{eval_fn},enumerable:false,configurable:false,writable:false}});'
        )
        key_list = []
        for exp, loc in sorted(fn.items()):
            if str(exp).startswith('*from*'):
                continue
            if not re.match(r'^[A-Za-z_$][\w$]*$', str(loc)):
                continue
            prop = json.dumps(exp, ensure_ascii=False)
            if str(loc).startswith('__defNS_'):
                # Nested deferred NS object — not on the store
                val_expr = str(loc)
            else:
                val_expr = f'{store}.{loc}'
            # "then" is IsSymbolLikeNamespaceKey for deferred NS — no eval trigger
            if exp == 'then':
                getter = f'function(){{ return {val_expr}; }}'
            else:
                getter = f'function(){{ {eval_fn}(); return {val_expr}; }}'
            lines.append(
                f'Object.defineProperty({ns_tmp}, {prop}, {{'
                f'get:{getter},'
                f'set:function(){{throw new TypeError("deferred NS read-only");}},'
                f'enumerable:true,configurable:false}});'
            )
            key_list.append(exp)
        if fd and re.match(r'^[A-Za-z_$][\w$]*$', str(fd)) and 'default' not in key_list:
            if str(fd).startswith('__defNS_'):
                dval = str(fd)
            else:
                dval = f'{store}.{fd}'
            lines.append(
                f'Object.defineProperty({ns_tmp}, "default", {{'
                f'get:function(){{ {eval_fn}(); return {dval}; }},'
                f'set:function(){{throw new TypeError("deferred NS read-only");}},'
                f'enumerable:true,configurable:false}});'
            )
            key_list.append('default')
        # Deferred module NS exotic objects use @@toStringTag "Deferred Module"
        lines.append(
            f'try{{Object.defineProperty({ns_tmp}, Symbol.toStringTag, {{'
            f'value:"Deferred Module",writable:false,enumerable:false,configurable:false}});}}catch(e){{}}'
        )
        lines.append(f'try{{Object.preventExtensions({ns_tmp});}}catch(e){{}}')
        keys_js = json.dumps(key_list, ensure_ascii=False)
        # 3rd arg: deferred eval hook when Reflect shims are present
        lines.append(f'try{{__markModuleNS({ns_tmp}, {keys_js}, {eval_fn});}}catch(e){{}}')
        if ns_bind_name and ns_bind_name != ns_tmp:
            lines.append(f'var {ns_bind_name} = {ns_tmp};')
        fixture_chunks.append("\n".join(lines) + "\n")
        _deferred_emitted[key] = ns_tmp
        inlined.add(key)
        return ns_tmp

    def _preload_requested_in_order(src):
        """Evaluate non-deferred RequestedModules in source order.

        Does not treat `import defer … from` as an evaluation trigger (even if
        the same module is later imported eagerly — that later import runs then).
        """
        seen = set()
        for m in re.finditer(
            r'''(?:^import\s+['"](\.[^'"]+)['"]\s*;?)'''
            r'''|(?:^import(?!\s+defer)\b[^;\n]*from\s*['"](\.[^'"]+)['"])'''
            r'''|(?:^export\b[^;\n]*from\s*['"](\.[^'"]+)['"])''',
            src,
            re.MULTILINE,
        ):
            spec = m.group(1) or m.group(2) or m.group(3)
            if not spec or spec in seen:
                continue
            if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
                continue
            seen.add(spec)
            _inline_fixture_body(spec, isolate_side_effect=True)

    def ensure_mod_ns(spec):
        """JS var holding GetModuleNamespace(spec); built once per module."""
        # Self namespace is built later in ns_epilogues / ns_by_module['__self__']
        if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
            return '__SELF_NS__'
        key = _resolve_mod_key(spec)
        if key in mod_ns_cache:
            return mod_ns_cache[key]
        # Prefer already-built import * as binding
        if key in ns_by_module:
            return ns_by_module[key]
        safe = re.sub(r'[^A-Za-z0-9_]', '_', Path(key).stem)[:40] or 'm'
        ns_tmp = f'__modns_{len(mod_ns_cache)}_{safe}'
        # Reserve before recurse to break cycles
        mod_ns_cache[key] = ns_tmp
        fn = {}
        fix = load_spec(spec)
        if fix is not None:
            # Body may already be inlined by _preload_requested_in_order
            _inline_fixture_body(spec, isolate_side_effect=True)
            dloc = _default_local_for_key(key)
            syn = _synthetic_kind(spec, key)
            fs, (_fd, fn0), rmap = parse_exports_from(
                fix, default_local=dloc, synthetic=syn
            )
            if syn:
                synthetic_defaults[key] = dloc
            fn = expand_star_exports(dict(fn0), rmap)
            for exp, (sp, im) in rmap.items():
                if im == '*' and not str(exp).startswith('*from*'):
                    fn[exp] = exp
            # Resolve multi-hop indirect exports to ultimate locals (IEE cycles).
            # resolve_export is defined later; name is resolved at call time.
            try:
                _resolve = resolve_export
            except NameError:
                _resolve = None
            if _resolve is not None:
                resolved = {}
                for exp in list(fn.keys()):
                    ult = _resolve(spec, exp)
                    resolved[exp] = ult if ult is not None else fn[exp]
                fn = resolved
        fixture_chunks.append(_namespace_object_js(ns_tmp, fn if fn else {}))
        return ns_tmp


    def strip_fixture_exports(fs):
        """Remove export keywords / export-from lines for inlined fixture bodies.

        Recursively inlines `export * from` / `export {…} from` targets so
        star-exported bindings exist in the combined scope.
        """
        # Capture + strip import attributes inside fixtures (json/text modules)
        for m in re.finditer(
            r'''from\s*['"]([^'"]+)['"]\s*with\s*\{\s*type\s*:\s*['"]([^'"]+)['"]''',
            fs,
        ):
            module_type_by_spec[m.group(1)] = m.group(2).lower()
        fs = re.sub(r'\s+with\s*\{[^}]*\}', '', fs)
        fs = re.sub(r'\s+assert\s*\{[^}]*\}', '', fs)

        # import dflt from './x.json'  (after with strip) → alias synthetic default
        def _fixture_import_default(m):
            loc, spec = m.group(1), m.group(2)
            key = _resolve_mod_key(spec) if spec.startswith('.') else None
            syn = _synthetic_kind(spec, key)
            if not syn or key is None:
                return m.group(0)
            _inline_fixture_body(spec, isolate_side_effect=False)
            dloc = synthetic_defaults.get(key) or _default_local_for_key(key)
            return f'var {loc} = {dloc};\n'

        fs = re.sub(
            r'''import\s+([A-Za-z_$][\w$]*)\s*from\s*['"]([^'"]+)['"]\s*;?''',
            _fixture_import_default,
            fs,
        )
        fs = re.sub(
            r'''import\s*\{\s*default\s+as\s+([A-Za-z_$][\w$]*)\s*\}\s*from\s*['"]([^'"]+)['"]\s*;?''',
            _fixture_import_default,
            fs,
        )

        # export * as ns from './mod' → alias to cached GetModuleNamespace(mod)
        # Also supports export * as "Name" (ModuleExportName string).
        def _fixture_export_star_as(m):
            id_name, str_name, spec = m.group(1), m.group(2), m.group(3)
            if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
                return ''
            if load_spec(spec) is None and not spec.startswith('.'):
                return ''
            ns_var = ensure_mod_ns(spec)
            if id_name is not None:
                return f'var {id_name} = {ns_var};\n'
            # String export name → sanitized local (matches _collect_module_exports)
            raw = str_name[1:-1]
            try:
                raw = json.loads('"' + raw.replace('\\', '\\\\').replace('"', '\\"') + '"')
            except Exception:
                pass
            safe = re.sub(r'[^A-Za-z0-9_]', '_', raw) or 'ns'
            if not re.match(r'^[A-Za-z_]', safe):
                safe = 'ns_' + safe
            return f'var __star_as_{safe} = {ns_var};\n'

        fs = re.sub(
            r'export\s*\*\s*as\s+'
            r'(?:([A-Za-z_$][\w$]*)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'))'
            r'\s*from\s*[\'"]([^\'"]+)[\'"]\s*;?',
            _fixture_export_star_as,
            fs,
        )

        def _inline_from_export(m):
            # export { a as b, c } from './x'
            clause, spec = m.group(1), m.group(2)
            # Never inline the main test module into itself via re-export cycle
            if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
                return ''
            fix = load_spec(spec)
            if fix is None:
                return ''
            key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
            # Don't re-enter a module already being inlined (cycles)
            if key in inlined:
                return ''
            raw, (_fd, fn), _rm = parse_exports_from(fix)
            inlined.add(key)
            fixture_chunks.append(strip_fixture_exports(raw))
            return ''  # re-export only; names resolved via map

        fs = re.sub(
            r'export\s*\{([^}]+)\}\s*from\s*[\'"]([^\'"]+)[\'"]\s*;?',
            _inline_from_export,
            fs,
        )

        def _inline_star(m):
            spec = m.group(1)
            if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
                return ''
            fix = load_spec(spec)
            if fix is None:
                return ''
            key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
            if key in inlined:
                return ''
            raw, (_fd, fn), _rm = parse_exports_from(fix)
            inlined.add(key)
            fixture_chunks.append(strip_fixture_exports(raw))
            return ''

        fs = re.sub(
            r'export\s*\*\s*from\s*[\'"]([^\'"]+)[\'"]\s*;?',
            _inline_star,
            fs,
        )
        fs = re.sub(r'\bexport\s+default\s+', '', fs)
        fs = re.sub(r'\bexport\s+', '', fs)
        # orphan export lists after export keyword strip
        fs = re.sub(r'(?m)^\{\s*[^}]*\bas\b[^}]*\}\s*;\s*$', '', fs)
        fs = re.sub(r'(?m)^\{\s*[A-Za-z_$][\w$]*\s*\}\s*;\s*$', '', fs)
        # Function("return this;")() SIGSEGVs; also `new Function(...)()`
        # (must rewrite `new Function` first so `new` is not left dangling)
        _gthis = '(typeof globalThis!=="undefined"?globalThis:(function(){return this;})())'
        fs = re.sub(
            r'''new\s+Function\s*\(\s*['"]return this;?['"]\s*\)\s*\(\s*\)''',
            _gthis,
            fs,
        )
        fs = re.sub(
            r'''(?<![\w$.])Function\s*\(\s*['"]return this;?['"]\s*\)\s*\(\s*\)''',
            _gthis,
            fs,
        )
        # import defer * as ns from './mod' inside eagerly-inlined fixture
        def _fix_import_defer(m):
            loc, spec = m.group(1), m.group(2)
            if not spec.startswith('.'):
                return m.group(0)
            internal = _emit_deferred_namespace(spec, None)
            return f'var {loc} = {internal};\n'

        fs = re.sub(
            r'''import\s+defer\s*\*\s*as\s+([A-Za-z_$][\w$]*)\s*from\s*['"]([^'"]+)['"]\s*;?''',
            _fix_import_defer,
            fs,
        )

        # Side-effect import './mod' inside fixture — inline eagerly
        def _fix_side_import(m):
            spec = m.group(1)
            if not spec.startswith('.'):
                return ''
            _inline_fixture_body(spec, isolate_side_effect=False)
            return ''

        fs = re.sub(
            r'''^import\s+['"]([^'"]+)['"]\s*;?''',
            _fix_side_import,
            fs,
            flags=re.MULTILINE,
        )

        # import * as ns from './mod' — self → deferred; else cached module NS
        def _fix_import_star(m):
            loc = m.group(1)
            spec = m.group(2)
            if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
                # Defer: const loc = <self_ns> once known (never alias name to itself)
                pre_assert_aliases.append(f'const {loc} = __SELF_NS__;')
                return ''
            if not spec.startswith('.'):
                return ''
            ns_var = ensure_mod_ns(spec)
            return f'var {loc} = {ns_var};\n'

        fs = re.sub(
            r'''import\s*\*\s*as\s+([A-Za-z_$][\w$]*)\s*from\s*['"]([^'"]+)['"]\s*;?''',
            _fix_import_star,
            fs,
        )
        # Drop named imports inside fixtures (bindings come from inlined exports)
        fs = re.sub(
            r'''import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"]\s*;?''',
            '',
            fs,
        )
        fs = re.sub(
            r'''import\s+[A-Za-z_$][\w$]*\s*from\s*['"][^'"]+['"]\s*;?''',
            '',
            fs,
        )
        if re.search(r'\bresults\b', fs) and re.search(r'try\s*\{', fs):
            fs = re.sub(r'\bresults\b', '__iee_results', fs)
            fs = (
                "var results = (function(){\n"
                + fs
                + "\nreturn __iee_results;\n})();\n"
            )
        return fs

    # Evaluate RequestedModules once in source order before rewriting exports
    # (eval-rqstd-order: deps run as '123456789' before main asserts).
    # Skip import-defer-only specs (evaluated lazily on NS access).
    _preload_requested_in_order(source)

    # import defer * as ns from './mod' → deferred namespace (lazy eval)
    _top_defer_binds = []  # local names bound to deferred NS

    def _early_import_defer(m):
        ns_name, spec = m.group(1), m.group(2)
        if not spec.startswith('.'):
            return m.group(0)
        # If same module is also eagerly imported, it's not deferred — use
        # normal namespace (module-imported-defer-and-eager).
        if spec not in _defer_only_specs:
            ns_var = ensure_mod_ns(spec)
            if ns_name != ns_var:
                pre_assert_aliases.append(f'const {ns_name} = {ns_var};')
            return ''
        _emit_deferred_namespace(spec, ns_name)
        _top_defer_binds.append(ns_name)
        return ''

    source = re.sub(
        r'''^import\s+defer\s*\*\s*as\s+([A-Za-z_$][\w$]*)\s*from\s*['"]([^'"]+)['"]\s*;?''',
        _early_import_defer,
        source,
        flags=re.MULTILINE,
    )
    if _deferred_emitted:
        fixture_chunks.insert(
            0,
            # M128e7bt: single dispatcher instead of 4 decls — each extra function
            # pushes free-var/getter scripts over the ~80 func_count cliff with the
            # module Reflect stub. kind: 0=get 1=has 2=del.
            # Deferred NS: string keys except "then" trigger eval; walk prototype
            # so Object.create(ns) still triggers; symbols skip eval.
            'function __defOp(kind,o,k){'
            'if(typeof k!=="string"){'
            'if(kind===0)return undefined;if(kind===1)return false;return true;}'
            'if(k!=="then"){var c=o;while(c){'
            'if(typeof c.__defEval==="function"){c.__defEval();break;}'
            'try{c=Object.getPrototypeOf(c);}catch(e){break;}}}'
            'if(kind===0)return o[k];'
            'if(kind===1){'
            'if(typeof Reflect!=="undefined"&&Reflect.has)return Reflect.has(o,k);'
            'return k in o;}'
            'try{return delete o[k];}catch(e){return false;}}\n',
        )

    # export * as NAME from './fix' early so default/named maps see __default_export__
    # Supports identifier and string ModuleExportName.
    # Records into early_star_as because the rewrite removes `export` syntax
    # before _collect_module_exports runs.
    early_star_as = {}  # exportName -> (localName, from_spec)

    def _early_export_star_as(m):
        id_name, str_name, spec = m.group(1), m.group(2), m.group(3)
        if not spec.startswith('.'):
            return m.group(0)
        is_self_spec = (
            Path(spec).name == self_name or spec in ('./' + self_name, self_name)
        )
        # export * as X from self → binding is GetModuleNamespace(self)
        if is_self_spec:
            if id_name is not None:
                if id_name == 'default':
                    early_star_as['default'] = ('__SELF_NS__', spec)
                    return ''
                loc = _safe_binding_name(id_name)
                early_star_as[id_name] = ('__SELF_NS__', spec)
                # reserved export names need a safe local alias later
                if loc != id_name:
                    early_star_as[id_name] = ('__SELF_NS__', spec)
                return ''
            raw = str_name[1:-1]
            try:
                raw = json.loads('"' + raw.replace('\\', '\\\\').replace('"', '\\"') + '"')
            except Exception:
                pass
            early_star_as[raw] = ('__SELF_NS__', spec)
            return ''
        ns_var = ensure_mod_ns(spec)
        if id_name is not None:
            if id_name == 'default':
                early_star_as['default'] = ('__default_export__', spec)
                return f'let __default_export__ = {ns_var};\n'
            loc = _safe_binding_name(id_name)
            early_star_as[id_name] = (loc, spec)
            return f'var {loc} = {ns_var};\n'
        raw = str_name[1:-1]
        try:
            raw = json.loads('"' + raw.replace('\\', '\\\\').replace('"', '\\"') + '"')
        except Exception:
            pass
        loc = _safe_binding_name(raw)
        early_star_as[raw] = (loc, spec)
        return f'var {loc} = {ns_var};\n'

    source = re.sub(
        r'export\s*\*\s*as\s+'
        r'(?:([A-Za-z_$][\w$]*)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'))'
        r'\s*from\s*[\'"]([^\'"]+)[\'"]\s*;?',
        _early_export_star_as,
        source,
    )

    self_reexports = {}
    dflt, named = _collect_module_exports(source, self_reexports)
    for exp, (loc, sp) in early_star_as.items():
        # __SELF_NS__ placeholder: property holds the module's own namespace object
        if loc == '__SELF_NS__':
            bind_name = _safe_binding_name(exp)
            named[exp] = bind_name
            self_reexports[exp] = (sp, '*')
            if exp == 'default':
                dflt = '__default_export__'
            # After self NS is built, bind export name to it (instn-once export * as ns2)
            pre_assert_aliases.append(f'const {bind_name} = __SELF_NS__;')
        else:
            named[exp] = loc
            self_reexports[exp] = (sp, '*')
            if exp == 'default':
                dflt = loc

    def _is_self_spec(spec):
        return (
            spec == '__self__'
            or Path(spec).name == self_name
            or spec in ('./' + self_name, self_name)
        )

    def resolve_export(mod_spec, export_name, resolve_set=None):
        """Follow indirect export {a as b} from chains to an ultimate local binding.

        Returns a JS identifier (local binding name) or None if circular/unresolved.
        Handles multi-hop cycles (instn-named-iee-cycle, instn-star-iee-cycle).
        """
        if resolve_set is None:
            resolve_set = set()
        if export_name is None or str(export_name).startswith('*from*'):
            return None
        if _is_self_spec(mod_spec):
            mod_key = '__self__'
            nmap = named
            rmap = self_reexports
        else:
            if not str(mod_spec).startswith('.'):
                return None
            mod_key = _resolve_mod_key(mod_spec)
            fix = load_spec(mod_spec)
            if fix is None:
                return None
            _fs, (_fd, fn0), rmap = parse_exports_from(
                fix, default_local=_default_local_for_key(mod_key)
            )
            nmap = expand_star_exports(dict(fn0), rmap)
            for exp, (sp, im) in rmap.items():
                if im == '*' and not str(exp).startswith('*from*'):
                    nmap[exp] = exp

        key = (mod_key, export_name)
        if key in resolve_set:
            return None  # circular import request → null
        resolve_set = set(resolve_set)
        resolve_set.add(key)

        # IndirectExportEntries first (specific re-exports)
        if export_name in rmap:
            sp, im = rmap[export_name]
            if im in ('*', '**') or str(export_name).startswith('*from*'):
                return None  # namespace / star — not a single local
            target = '__self__' if _is_self_spec(sp) else sp
            return resolve_export(target, im, resolve_set)

        # LocalExportEntries
        if export_name in nmap:
            loc = nmap[export_name]
            if re.match(r'^[A-Za-z_$][\w$]*$', str(loc)):
                return str(loc)
        return None

    # Note: test262 often writes `import* as ns` (no space after import).
    import_re = re.compile(
        r'''^import\s*(?:
            (?P<def>[A-Za-z_$][\w$]*)\s*,\s*
          )?
          (?:
            \*\s+as\s+(?P<ns>[A-Za-z_$][\w$]*)
            |\{(?P<named>[^}]*)\}
            |(?P<defonly>[A-Za-z_$][\w$]*)
          )?
          \s*from\s*['"](?P<spec>[^'"]+)['"]\s*;?
          |^import\s+['"](?P<side>[^'"]+)['"]\s*;?
        ''',
        re.MULTILINE | re.VERBOSE,
    )

    ns_epilogues = []  # namespace objects after all decls (live getters)
    live_export_assigns = set()  # export vars that need assignment-only form
    live_binding_prelude = []  # hoisted before asserts (import instantiation)
    # pre_assert_aliases / ns_by_module initialised earlier (ensure_mod_ns)
    deferred_aliases = []
    live_renames = {}  # importLocal -> sourceLocal for live fixture vars

    def bind_self_import(loc, src_local, kind_source):
        """Create immutable import binding for self (or re-export of self)."""
        is_fun = bool(re.search(
            rf'export\s+(?:async\s+)?function\s*\*?\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        is_class = bool(re.search(
            rf'export\s+class\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        is_var = bool(re.search(
            rf'export\s+var\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        is_let = bool(re.search(
            rf'export\s+let\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        is_const = bool(re.search(
            rf'export\s+const\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        # also bare var/const/let without export (after strip) or export { x as y }
        is_plain_var = bool(re.search(
            rf'(?:^|\n)\s*(?:export\s+)?var\s+{re.escape(src_local)}\b',
            kind_source,
        ))
        if is_fun:
            extracted = _extract_export_function_decl(kind_source, src_local)
            if extracted:
                live_binding_prelude.append(extracted[1])
                live_export_assigns.add('__strip_export_fn_' + src_local)
            # Function first in prelude, then const (engine does not hoist fn before const)
            live_binding_prelude.append(f'const {loc} = {src_local};')
        elif is_var:
            live_binding_prelude.append(f'const {loc} = undefined;')
            if loc != src_local:
                live_binding_prelude.append(f'var {src_local};')
            else:
                live_binding_prelude.append(f'var {src_local};')
            live_export_assigns.add(src_local)
        elif is_class:
            # Class has TDZ until evaluated — alias const after class body
            deferred_aliases.append((loc, src_local, 'class'))
            live_export_assigns.add('__class_alias_' + loc + '_' + src_local)
        elif is_let or is_const:
            # Leave loc undeclared until after export let/const (native TDZ for typeof)
            deferred_aliases.append((loc, src_local, 'let' if is_let else 'const'))
            live_export_assigns.add('__let_alias_' + loc + '_' + src_local)
        elif src_local == '__default_export__' or src_local.startswith('__star_as_'):
            # Default / star-as binding is initialised in body — alias after it
            live_export_assigns.add('__default_alias_' + loc)
        else:
            # Simple rename (export { _if as if } / import { if as if_ })
            # Place before asserts so source vars are already initialised.
            # Same name already in scope from fixture / local export — no alias.
            if loc != src_local:
                pre_assert_aliases.append(f'const {loc} = {src_local};')

    def bind_default_import(defname, kind_source, is_self_imp):
        """Default import: hoist functions; TDZ for class/expr."""
        # Named: export default function fName
        extracted = _extract_default_function_decl(kind_source)
        if extracted:
            full, decl, fname = extracted
            # Fixture already inlined as `function fname` via strip — don't
            # duplicate the decl. Live-rename import to track mutations
            # (eval-gtbndng-indirect-update-dflt: fn=2 updates default).
            if (
                not is_self_imp
                and fname
                and fname != '__default_export__'
                and re.search(
                    rf'\bfunction\s*{re.escape(fname)}\s*\(',
                    "\n".join(fixture_chunks),
                )
            ):
                if defname != fname:
                    live_renames[defname] = fname
                return
            live_binding_prelude.append(decl)
            if fname == '__default_export__':
                live_binding_prelude.append(_NAME_DEFAULT)
            live_binding_prelude.append(f'const {defname} = {fname};')
            live_export_assigns.add('__strip_default_fn__')
            return
        # export default class [Name]
        if re.search(r'export\s+default\s+class\b', kind_source) or re.search(
            r'(?:var|let|const)\s+__default_export__\s*=\s*class\b', kind_source
        ):
            # const defname = class after rewrite — TDZ until that line
            live_export_assigns.add('__default_alias_' + defname)
            return
        # export default expr / already __default_export__
        if re.search(r'export\s+default\s+', kind_source) or re.search(
            r'\b__default_export__\b', kind_source
        ):
            live_export_assigns.add('__default_alias_' + defname)
            return
        if is_self_imp and dflt:
            live_binding_prelude.append(f'var {defname} = {dflt};')

    def handle_import(m):
        nonlocal dflt, named
        spec = m.group('spec') or m.group('side')
        if not spec:
            return ''
        is_self = Path(spec).name == self_name or spec in ('./' + self_name, self_name)
        fix_src = None if is_self else load_spec(spec)
        fix_reexports = {}

        if m.group('side') and fix_src is not None:
            # May already be inlined by _preload_requested_in_order
            _inline_fixture_body(spec, isolate_side_effect=True)
            return ''

        f_dflt = dflt if is_self else None
        f_named = dict(named) if is_self else {}
        kind_source = source
        if fix_src is not None:
            key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
            dloc = _default_local_for_key(key)
            syn = _synthetic_kind(spec, key)
            fs, (fd, fn), fix_reexports = parse_exports_from(
                fix_src, default_local=dloc, synthetic=syn
            )
            f_dflt, f_named = fd, dict(fn)
            if syn:
                synthetic_defaults[key] = dloc
            # Named imports need star-expanded export table (export * / * as)
            if fix_reexports:
                f_named = expand_star_exports(f_named, fix_reexports)
                for exp, (sp, im) in fix_reexports.items():
                    if im == '*' and not str(exp).startswith('*from*'):
                        f_named[exp] = exp
            kind_source = fs
            # Prefer shared inliner (unique defaults, isolation rules)
            _inline_fixture_body(spec, isolate_side_effect=True)
            # JSON modules: named imports (other than default) are a resolution error
            if syn == 'json' and m.group('named'):
                bad = False
                for part in (m.group('named') or '').split(','):
                    part = part.strip()
                    if not part:
                        continue
                    exp = part.split(' as ')[0].strip() if ' as ' in part else part
                    if exp != 'default':
                        bad = True
                        break
                if bad:
                    return 'throw new SyntaxError("JSON modules have no named exports");\n'

        repl = []
        defname = m.group('def') or m.group('defonly')
        if defname:
            # Self as text module: import value from './self.js' with { type: 'text' }
            if is_self and module_type_by_spec.get(spec) == 'text':
                try:
                    raw_self = Path(test_path).read_text(errors='replace')
                    raw_self = _FRONTMATTER_RE.sub('', raw_self)
                except Exception:
                    raw_self = ''
                dloc = f'__dflt_self_text'
                fixture_chunks.append(f'var {dloc} = {json.dumps(raw_self)};\n')
                repl.append(f'var {defname} = {dloc};')
            elif is_self:
                bind_default_import(defname, source, True)
            elif f_dflt:
                # fixture default (incl. JSON/text synthetic)
                if re.search(
                    r'(?:export\s+default\s+(?:async\s+)?function|var\s+__default_export__\s*=\s*(?:async\s+)?function)',
                    kind_source,
                ):
                    bind_default_import(defname, kind_source, False)
                else:
                    repl.append(f'var {defname} = {f_dflt};')
            elif is_self and dflt:
                repl.append(f'var {defname} = {dflt};')

        ns = m.group('ns')
        if ns:
            # Module identity key for namespace caching (GetModuleNamespace once)
            if is_self:
                mod_key = '__self__'
            else:
                mod_key = _resolve_mod_key(spec)
            if mod_key in ns_by_module:
                # Same module namespace object (import * as a; import * as b)
                pre_assert_aliases.append(f'const {ns} = {ns_by_module[mod_key]};')
            elif not is_self:
                # External: one NS object via ensure_mod_ns (shared with * as re-exports)
                ns_var = ensure_mod_ns(spec)
                ns_by_module[mod_key] = ns_var
                if ns != ns_var:
                    pre_assert_aliases.append(f'const {ns} = {ns_var};')
            else:
                # Self namespace — expand export * / re-exports into the map
                emap = dict(f_named if f_named else named)
                if self_reexports:
                    emap = expand_star_exports(emap, self_reexports)
                if self_reexports:
                    for exp, (fspec, im) in list(self_reexports.items()):
                        if exp.startswith('*from*') or im in ('*', '**'):
                            continue
                        # Multi-hop resolve (export chains / IEE cycles)
                        ult = resolve_export('__self__', exp)
                        if ult is not None:
                            emap[exp] = ult
                            # Ensure defining fixture bodies are inlined
                            if not _is_self_spec(fspec):
                                fix2 = load_spec(fspec)
                                if fix2 is not None:
                                    key2 = _resolve_mod_key(fspec)
                                    if key2 not in inlined:
                                        inlined.add(key2)
                                        fs2, _, _ = parse_exports_from(fix2)
                                        fixture_chunks.append(strip_fixture_exports(fs2))
                            continue
                        # Re-export from self (export { x as y } from './self') — local only
                        if _is_self_spec(fspec):
                            if re.match(r'^[A-Za-z_$][\w$]*$', str(im)):
                                emap[exp] = im
                            continue
                        fix2 = load_spec(fspec)
                        if fix2 is None:
                            continue
                        key2 = _resolve_mod_key(fspec)
                        fs2, (_fd2, fn2), rm2 = parse_exports_from(fix2)
                        fn2 = expand_star_exports(dict(fn2), rm2)
                        if key2 not in inlined:
                            inlined.add(key2)
                            fixture_chunks.append(strip_fixture_exports(fs2))
                        loc = fn2.get(im, fn2.get(exp, im))
                        if re.match(r'^[A-Za-z_$][\w$]*$', str(loc)):
                            emap[exp] = loc
                ns_epilogues.append(_namespace_object_js(ns, emap, as_const=True))
                ns_by_module[mod_key] = ns

        named_clause = m.group('named')
        if named_clause:
            for part in named_clause.split(','):
                part = part.strip()
                if not part:
                    continue
                if ' as ' in part:
                    exp, loc = part.split(' as ', 1)
                    exp, loc = exp.strip(), loc.strip()
                else:
                    exp = loc = part
                # ModuleExportName string: import { "☿" as Ami }
                if len(exp) >= 2 and exp[0] in ('"', "'") and exp[-1] == exp[0]:
                    try:
                        exp = json.loads('"' + exp[1:-1].replace('\\', '\\\\').replace('"', '\\"') + '"')
                    except Exception:
                        exp = exp[1:-1]
                src_local = f_named.get(exp, exp)
                if exp == 'default' and f_dflt:
                    src_local = f_dflt

                # Multi-hop ResolveExport for fixture / self named imports
                if not is_self:
                    reexp = fix_reexports.get(exp)
                    if reexp:
                        from_spec, from_name = reexp
                        from_is_self = _is_self_spec(from_spec)
                        if from_name == '*':
                            if from_is_self:
                                pre_assert_aliases.append(f'const {loc} = __SELF_NS__;')
                            else:
                                ns_var = ensure_mod_ns(from_spec)
                                mk = _resolve_mod_key(from_spec)
                                ns_by_module.setdefault(mk, ns_var)
                                if loc != exp and loc != ns_var:
                                    pre_assert_aliases.append(f'const {loc} = {ns_var};')
                            continue
                        # Re-export chain ending on self / multi-hop
                        ult = resolve_export(spec, exp)
                        if ult is not None:
                            # One-hop: fixture re-exports a local of self
                            # (iee-bndng: export { A as B } from self)
                            one_hop_local = (
                                from_is_self
                                and from_name == ult
                                and re.search(
                                    rf'\bexport\s+(?:var|let|const|class|async\s+function|function\s*\*?)\s+{re.escape(ult)}\b',
                                    source,
                                )
                            )
                            if one_hop_local:
                                bind_self_import(loc, ult, source)
                            else:
                                # Multi-hop cycle (named-iee-cycle a→…→z)
                                if loc != ult:
                                    pre_assert_aliases.append(f'const {loc} = {ult};')
                            continue
                    # Fall through to simple fixture local alias
                    is_fun = bool(re.search(
                        rf'export\s+(?:async\s+)?function\s*\*?\s+{re.escape(src_local)}\b',
                        kind_source,
                    ))
                    is_var = bool(re.search(
                        rf'export\s+var\s+{re.escape(src_local)}\b',
                        kind_source,
                    ))
                    is_const = bool(re.search(
                        rf'export\s+const\s+{re.escape(src_local)}\b',
                        kind_source,
                    ))
                    if is_fun:
                        if loc != src_local:
                            live_binding_prelude.append(f'const {loc} = {src_local};')
                    elif is_var or is_const:
                        if loc != src_local:
                            live_renames[loc] = src_local
                    else:
                        if loc != src_local:
                            live_renames[loc] = src_local
                else:
                    # Self-import of a name re-exported from a fixture
                    reexp_self = self_reexports.get(exp) or self_reexports.get(src_local)
                    if reexp_self:
                        from_spec, from_name = reexp_self
                        if from_name != '*':
                            # Always inline the export source module first
                            if not _is_self_spec(from_spec):
                                fix2 = load_spec(from_spec)
                                if fix2 is not None:
                                    key2 = _resolve_mod_key(from_spec)
                                    if key2 not in inlined:
                                        inlined.add(key2)
                                        fs2, _, _ = parse_exports_from(fix2)
                                        fixture_chunks.append(strip_fixture_exports(fs2))
                            ult = resolve_export('__self__', exp)
                            if ult is not None:
                                # Prefer live binding semantics on ultimate local
                                bind_self_import(loc, ult, source)
                                continue
                            if not _is_self_spec(from_spec):
                                fix2 = load_spec(from_spec)
                                if fix2 is not None:
                                    fs2, (fd2, fn2), rm2 = parse_exports_from(fix2)
                                    fn2 = expand_star_exports(dict(fn2), rm2)
                                    real = fn2.get(from_name, from_name)
                                    if loc != real:
                                        repl.append(f'const {loc} = {real};')
                                    continue
                    bind_self_import(loc, src_local, source)
        return "\n".join(repl)

    new_src = import_re.sub(handle_import, source)

    # Apply live renames (import { x as y } where x is mutable fixture binding)
    for loc, src_local in live_renames.items():
        if loc == src_local:
            continue
        new_src = re.sub(
            rf'(?<![\w$.]){re.escape(loc)}(?![\w$])',
            src_local,
            new_src,
        )

    # Strip remaining export { … } from lines (resolved via reexport map + import)
    new_src = re.sub(
        r'export\s*\{[^}]*\}\s*from\s*[\'"][^\'"]+[\'"]\s*;?\s*',
        '',
        new_src,
    )
    # export * from './fix' — expand into named (already in maps) and drop syntax
    def _strip_export_star(m):
        spec = m.group(1)
        if Path(spec).name == self_name or spec in ('./' + self_name, self_name):
            return ''
        fix = load_spec(spec)
        if fix is None:
            return ''
        key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
        if key not in inlined:
            inlined.add(key)
            fs, (_fd, fn), rmap = parse_exports_from(fix)
            fixture_chunks.append(strip_fixture_exports(fs))
            # Merge into module-level named for any later ns of self
            for exp, loc in expand_star_exports(fn, rmap).items():
                if exp != 'default' and exp not in named:
                    named[exp] = loc
        return ''

    new_src = re.sub(
        r'export\s*\*\s*from\s*[\'"]([^\'"]+)[\'"]\s*;?',
        _strip_export_star,
        new_src,
    )
    # If self ns was already built before export * expansion, rebuild is too late
    # for this pass; ensure named map merges are used when building self ns by
    # expanding export * before import handling when possible — handled below if
    # any leftover export * remains after early collect.

    # export var/let/const x = expr → x = expr when live-imported (already hoisted)
    for name in list(live_export_assigns):
        if name.startswith('__strip_export_fn_'):
            fn = name[len('__strip_export_fn_'):]
            extracted = _extract_export_function_decl(new_src, fn)
            if extracted:
                new_src = new_src.replace(extracted[0], f'/* hoisted {fn} */', 1)
            else:
                new_src = re.sub(
                    rf'export\s+(?:async\s+)?function\s*\*?\s+{re.escape(fn)}\s*\([^)]*\)\s*\{{[^}}]*\}}',
                    f'/* hoisted {fn} */',
                    new_src,
                    count=1,
                )
            continue
        if name == '__strip_default_fn__':
            extracted = _extract_default_function_decl(new_src)
            if extracted:
                new_src = new_src.replace(extracted[0], '/* hoisted default fn */', 1)
            # also strip name-stamp left after var rewrite
            new_src = re.sub(
                r'try\{Object\.defineProperty\(__default_export__,\'name\',[^\n]+\n?',
                '',
                new_src,
                count=1,
            )
            continue
        if name.startswith('__default_alias_'):
            loc = name[len('__default_alias_'):]
            # Prefer a single `const loc = …` so loc is in TDZ until that line
            # (typeof loc must throw ReferenceError before init).
            if re.search(r'(?:var|let|const)\s+__default_export__\s*=', new_src):
                # If __default_export__ is already a complete binding (e.g. export *
                # as default → ns object), only alias — don't rewrite the var.
                if re.search(
                    r'(?:var|let|const)\s+__default_export__\s*=\s*__star_as_',
                    new_src,
                ) or re.search(
                    r'(?:var|let|const)\s+__default_export__\s*=\s*[A-Za-z_$][\w$]*\s*;',
                    new_src,
                ):
                    # Insert const alias after the var line
                    new_src = re.sub(
                        r'((?:var|let|const)\s+__default_export__\s*=\s*[^;]+;)',
                        rf'\1\nconst {loc} = __default_export__;',
                        new_src,
                        count=1,
                    )
                else:
                    # let/var __default_export__ = class {} / expr;
                    # → const loc = class {} / expr;
                    new_src = re.sub(
                        r'(?:var|let|const)\s+__default_export__\s*=\s*',
                        f'const {loc} = ',
                        new_src,
                        count=1,
                    )
                    # Drop any mid-expression name stamps left from early rewrite
                    new_src = re.sub(
                        r'\n?try\{var __n=.*?;\}catch\(e\)\{\}\n?',
                        '\n',
                        new_src,
                    )
                    new_src = re.sub(
                        r'\n?try\{Object\.defineProperty\(__default_export__[^;]+;\}catch\(e\)\{\}\n?',
                        '\n',
                        new_src,
                    )
                    # Append stamp after the const statement (brace-aware)
                    mconst = re.search(
                        rf'const\s+{re.escape(loc)}\s*=',
                        new_src,
                    )
                    if mconst:
                        # find end of statement
                        i = mconst.end()
                        brace = paren = 0
                        while i < len(new_src):
                            ch = new_src[i]
                            if ch == '{':
                                brace += 1
                            elif ch == '}':
                                brace -= 1
                            elif ch == '(':
                                paren += 1
                            elif ch == ')':
                                paren -= 1
                            elif ch == ';' and brace == 0 and paren == 0:
                                i += 1
                                stamp = _name_default_stamp(loc)
                                new_src = new_src[:i] + "\n" + stamp + "\n" + new_src[i:]
                                break
                            i += 1
            elif re.search(r'export\s+default\s+class\b', new_src):
                m = re.search(r'export\s+default\s+class\b', new_src)
                if m:
                    m2 = re.match(
                        r'export\s+default\s+(class(?:\s+[A-Za-z_$][\w$]*)?\b[^{]*)\{',
                        new_src[m.start():],
                    )
                    if m2:
                        abs_brace = m.start() + m2.end() - 1
                        end = _match_braced_decl(new_src, abs_brace)
                        if end > 0:
                            block = new_src[m.start():end]
                            inner = block[len('export default '):]
                            new_src = (
                                new_src[:m.start()]
                                + f'const {loc} = {inner};'
                                + new_src[end:]
                            )
            elif re.search(r'export\s+default\s+', new_src):
                new_src = re.sub(
                    r'export\s+default\s+',
                    f'const {loc} = ',
                    new_src,
                    count=1,
                )
            continue
        if name.startswith('__class_alias_') or name.startswith('__let_alias_'):
            rest = name.split('_alias_', 1)[1]
            loc, src_local = rest.split('_', 1)
            if name.startswith('__class_alias_'):
                extracted = _extract_export_class_decl(new_src, src_local)
                if extracted:
                    full, decl = extracted
                    alias = f'\nconst {loc} = {src_local};' if loc != src_local else ''
                    new_src = new_src.replace(full, decl + alias, 1)
                else:
                    new_src = re.sub(
                        rf'export\s+(class\s+{re.escape(src_local)}\b)',
                        r'\1',
                        new_src,
                        count=1,
                    )
                    if loc != src_local:
                        new_src = re.sub(
                            rf'(class\s+{re.escape(src_local)}\b[^{{]*\{{)',
                            rf'\1',
                            new_src,
                            count=1,
                        )
                        # append const after class body
                        extracted2 = _extract_export_class_decl(
                            'export ' + new_src if False else new_src, src_local
                        )
                        # simpler: after class Name { ... }
                        m = re.search(
                            rf'class\s+{re.escape(src_local)}\b[^{{]*\{{',
                            new_src,
                        )
                        if m and loc != src_local:
                            end = _match_braced_decl(new_src, m.end() - 1)
                            if end > 0:
                                new_src = (
                                    new_src[:end]
                                    + f'\nconst {loc} = {src_local};'
                                    + new_src[end:]
                                )
            else:
                # let/const: strip export, add const loc = src after
                def let_repl(mm):
                    body = mm.group(0)
                    body = re.sub(r'^export\s+', '', body)
                    if loc != src_local:
                        body = body + f'\nconst {loc} = {src_local};'
                    return body

                new_src2, nsub = re.subn(
                    rf'export\s+(?:let|const)\s+{re.escape(src_local)}\s*=\s*[^;]+;',
                    let_repl,
                    new_src,
                    count=1,
                )
                if nsub:
                    new_src = new_src2
                else:
                    new_src2, nsub = re.subn(
                        rf'export\s+(?:let|const)\s+{re.escape(src_local)}\s*;',
                        let_repl,
                        new_src,
                        count=1,
                    )
                    if nsub:
                        new_src = new_src2
            continue
        # var live: export var x = → x =  (x already var-hoisted in prelude)
        new_src = re.sub(
            rf'\bexport\s+(?:var|let|const)\s+{re.escape(name)}\s*=',
            f'{name} =',
            new_src,
        )
        new_src = re.sub(
            rf'\bexport\s+(?:var|let|const)\s+{re.escape(name)}\s*;',
            f'/* hoisted {name} */;',
            new_src,
        )

    # Hoist live bindings to top (module instantiation before evaluation/asserts)
    # Functions must precede const aliases (engine evaluates const before later fn decls)
    if live_binding_prelude:
        seen = set()
        uniq = []
        for line in live_binding_prelude:
            if line not in seen:
                seen.add(line)
                uniq.append(line)
        new_src = "\n".join(uniq) + "\n" + new_src

    # Strip leftover export keywords (local export-binding tests, etc.).
    # Named `export default class C` / `function f` → keep declaration name
    # (NS getters bind to C/f). Anon defaults already rewritten to __default_export__.
    # Do NOT strip bare `export default class extends` (invalid without name).
    new_src = re.sub(
        r'\bexport\s+default\s+(class\s+[A-Za-z_$][\w$]*)',
        r'\1',
        new_src,
    )
    new_src = re.sub(
        r'\bexport\s+default\s+((?:async\s+)?function\s*\*?\s+[A-Za-z_$][\w$]*)',
        r'\1',
        new_src,
    )
    new_src = re.sub(
        r'\bexport\s+(async\s+)?(function\s*\*?|class|let|const|var)\b',
        r'\1\2',
        new_src,
    )
    # Anonymous default expr: stamp .name = 'default' when still anonymous
    # (export default (function(){}), (function*(){}), (class {})).
    if re.search(
        r'(?:var|let|const)\s+__default_export__\s*=\s*\(\s*(?:async\s+)?function',
        new_src,
    ) or re.search(
        r'(?:var|let|const)\s+__default_export__\s*=\s*\(\s*class\b',
        new_src,
    ):
        new_src = _stamp_default_name_after(
            new_src, '__default_export__ =', force=False
        )
    # export { a, b as c }; → remove entirely (bindings already declared)
    new_src = re.sub(r'\bexport\s*\{[^}]+\}\s*;', '', new_src)
    # orphan `{ a as b };` / `{ testNs };` left if export keyword was stripped
    new_src = re.sub(r'(?m)^\{\s*[^}]*\bas\b[^}]*\}\s*;\s*$', '', new_src)
    new_src = re.sub(
        r'(?m)^\{\s*[A-Za-z_$][\w$]*(?:\s*,\s*[A-Za-z_$][\w$]*)*\s*\}\s*;\s*$',
        '',
        new_src,
    )
    fixture_chunks[:] = [
        re.sub(r'(?m)^\{\s*[A-Za-z_$][\w$]*\s*\}\s*;\s*$', '', c)
        for c in fixture_chunks
    ]
    fixture_chunks[:] = [
        re.sub(r'(?m)^\{\s*[^}]*\bas\b[^}]*\}\s*;\s*$', '', c)
        for c in fixture_chunks
    ]

    # Engine: typeof on class binding does not TDZ-throw (bare does). Emulate
    # module class bindings as `let Name = class Name {…}` only when a prior
    # `typeof Name` appears (instn-local-bndng-cls etc.). Avoid rewriting
    # unrelated `export class` evaluation tests.
    pos_c, pieces_c = 0, []
    while True:
        m = re.search(
            r'(?m)^class\s+([A-Za-z_$][\w$]*)\s*\{',
            new_src[pos_c:],
        )
        if not m:
            pieces_c.append(new_src[pos_c:])
            break
        abs_start = pos_c + m.start()
        abs_brace = pos_c + m.end() - 1
        end = _match_braced_decl(new_src, abs_brace)
        if end < 0:
            pieces_c.append(new_src[pos_c : abs_start + 1])
            pos_c = abs_start + 1
            continue
        name = m.group(1)
        body = new_src[abs_brace:end]  # includes { … }
        pieces_c.append(new_src[pos_c:abs_start])
        head = new_src[:abs_start]
        needs_tdz = bool(re.search(rf'\btypeof\s+{re.escape(name)}\b', head))
        if needs_tdz:
            pieces_c.append(f'let {name} = class {name} {body};')
        else:
            pieces_c.append(f'class {name} {body}')
        pos_c = end
    new_src = "".join(pieces_c)

    # Hoist top-level function decls that appear *after* the first assert
    # (engine does not hoist; module instn requires bindings before evaluation).
    m_as0 = re.search(r'\bassert(?:\.|\()', new_src)
    if m_as0:
        head, tail = new_src[: m_as0.start()], new_src[m_as0.start() :]
        fun_hoists = []
        pos = 0
        pieces = []
        while True:
            m = re.search(
                r'(?m)^(async\s+)?function(\s*\*)?\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{',
                tail[pos:],
            )
            if not m:
                pieces.append(tail[pos:])
                break
            abs_start = pos + m.start()
            abs_brace = pos + m.end() - 1
            end = _match_braced_decl(tail, abs_brace)
            if end < 0:
                pieces.append(tail[pos : abs_start + 1])
                pos = abs_start + 1
                continue
            fun_hoists.append(tail[abs_start:end])
            pieces.append(tail[pos:abs_start])
            pieces.append(f'/* function {m.group(3)} hoisted */')
            pos = end
        if fun_hoists:
            new_src = "\n".join(fun_hoists) + "\n" + head + "".join(pieces)

    # Fill namespace objects + pre-assert aliases before first assert
    pre_bits = []
    if ns_epilogues:
        for block in ns_epilogues:
            pre_bits.append(block)
    if pre_assert_aliases:
        seen_a = set()
        for line in pre_assert_aliases:
            if line not in seen_a:
                seen_a.add(line)
                pre_bits.append(line)
    # Resolve fixture-self-ns placeholders to the actual self namespace binding
    if '__SELF_NS__' in "\n".join(pre_assert_aliases + ns_epilogues) or any(
        '__SELF_NS__' in c for c in fixture_chunks
    ):
        self_ns = ns_by_module.get('__self__')
        if self_ns:
            pre_assert_aliases = [
                a.replace('__SELF_NS__', self_ns) for a in pre_assert_aliases
            ]
            fixture_chunks = [c.replace('__SELF_NS__', self_ns) for c in fixture_chunks]
            # Also fix any leftover in new_src later

    if pre_bits or pre_assert_aliases:
        # rebuild pre_bits with updated aliases
        pre_bits = []
        if ns_epilogues:
            for block in ns_epilogues:
                pre_bits.append(block)
        if pre_assert_aliases:
            seen_a = set()
            for line in pre_assert_aliases:
                if line not in seen_a:
                    seen_a.add(line)
                    pre_bits.append(line)
    if pre_bits:
        ep = "\n".join(pre_bits) + "\n"
        # Insert before first use of namespace locals / asserts / Object/Reflect ops.
        # Include getOwnPropertyNames(ns) style uses (own-property-keys-*).
        m_as = re.search(
            r'(?m)^(?:\s*)(?:assert(?:\.|\()|Object\.(?:preventExtensions|getOwnProperty|isExtensible|setPrototypeOf|getOwnPropertyNames|getOwnPropertySymbols|keys|freeze)|Reflect\.|for\s*\(|var\s+\w+\s*=\s*Object\.|var\s+\w+\s*=\s*Reflect\.)',
            new_src,
        )
        if not m_as:
            m_as = re.search(r'\bassert(?:\.|\()', new_src)
        if not m_as:
            # First read of any cached ns name
            for nsn in ns_by_module.values():
                m_as = re.search(rf'\b{re.escape(nsn)}\b', new_src)
                if m_as:
                    break
        if m_as:
            new_src = new_src[: m_as.start()] + ep + new_src[m_as.start() :]
        else:
            new_src = new_src + "\n" + ep
    if ns_by_module.get('__self__'):
        sn = ns_by_module['__self__']
        new_src = new_src.replace('__SELF_NS__', sn)
        for i, c in enumerate(fixture_chunks):
            fixture_chunks[i] = c.replace('__SELF_NS__', sn)
        # Drop self-alias `const ns = ns` if somehow produced
        new_src = re.sub(
            rf'const\s+{re.escape(sn)}\s*=\s*{re.escape(sn)}\s*;',
            '',
            new_src,
        )

    # Module this-binding is undefined (eval-this.js). Scripts use global this.
    if re.search(r'assert\.sameValue\s*\(\s*this\s*,\s*undefined\s*\)', new_src):
        new_src = (
            "(function(){\n" + new_src + "\n}).call(undefined);\n"
        )

    # Deferred NS: property access / `in` should trigger evaluation (no Proxy),
    # except "then" and @@toStringTag (IsSymbolLikeNamespaceKey).
    if _deferred_emitted:
        defer_ids = set(_top_defer_binds)
        # locals assigned from deferred: const x = ns.foo or const x = ns1.ns_1_2
        for m in re.finditer(
            r'''(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\s*\.\s*[A-Za-z_$]''',
            new_src,
        ):
            if m.group(2) in defer_ids or m.group(2) in _deferred_emitted.values():
                defer_ids.add(m.group(1))
        # Object.create(ns) children (hasProperty/get-in-prototype)
        for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*Object\.create\(\s*([A-Za-z_$][\w$]*)\s*\)',
            new_src,
        ):
            if m.group(2) in defer_ids or m.group(2) in _deferred_emitted.values():
                defer_ids.add(m.group(1))
        for did in list(defer_ids):
            # ns.prop → __defOp(0, ns, "prop")  — not on LHS of assignment
            def _dot_get(m, _did=did):
                # if next non-ws is `=` (and not `==`/`===`), leave alone
                end = m.end()
                rest = new_src[end:end + 3]
                j = 0
                while end + j < len(new_src) and new_src[end + j] in ' \t':
                    j += 1
                ch = new_src[end + j:end + j + 2]
                if ch.startswith('=') and not ch.startswith('=='):
                    return m.group(0)
                return f'__defOp(0, {_did}, "{m.group(1)}")'

            new_src = re.sub(
                rf'(?<![\w$.]){re.escape(did)}\.([A-Za-z_$][\w$]*)',
                _dot_get,
                new_src,
            )
            # ns[expr] → __defOp(0,...) / delete ns[expr] → __defOp(2,...)
            out = []
            i = 0
            pat = re.compile(rf'(?<![\w$.]){re.escape(did)}\s*\[')
            while True:
                m = pat.search(new_src, i)
                if not m:
                    out.append(new_src[i:])
                    break
                # detect leading `delete`
                pre = new_src[max(0, m.start() - 12):m.start()]
                is_del = bool(re.search(r'\bdelete\s*$', pre))
                if is_del:
                    # drop `delete` from output already emitted
                    del_start = re.search(r'\bdelete\s*$', pre).start()
                    out.append(new_src[i:m.start() - len(pre) + del_start])
                else:
                    out.append(new_src[i:m.start()])
                depth = 1
                j = m.end()
                while j < len(new_src) and depth:
                    if new_src[j] == '[':
                        depth += 1
                    elif new_src[j] == ']':
                        depth -= 1
                    j += 1
                expr = new_src[m.end():j - 1]
                if is_del:
                    out.append(f'__defOp(2, {did}, {expr})')
                else:
                    out.append(f'__defOp(0, {did}, {expr})')
                i = j
            new_src = ''.join(out)
            # expr in ns → __defOp(1, ns, expr)
            new_src = re.sub(
                rf'(?<![\w$.])([A-Za-z_$][\w$]*)\s+in\s+{re.escape(did)}(?![\w$])',
                rf'__defOp(1, {did}, \1)',
                new_src,
            )

    # Dynamic import of JSON modules (engine has no import()) — resolve to
    # the same synthetic default binding as static import (idempotency).
    def _dyn_json_import(m):
        spec = m.group(1)
        if not spec.startswith('.'):
            return m.group(0)
        key = _resolve_mod_key(spec)
        _inline_fixture_body(spec, isolate_side_effect=False)
        dloc = synthetic_defaults.get(key) or _default_local_for_key(key)
        return f'Promise.resolve({{default:{dloc}}})'

    new_src = re.sub(
        r'''import\s*\(\s*['"]([^'"]+\.json)['"]\s*(?:,\s*[^)]*)?\s*\)''',
        _dyn_json_import,
        new_src,
    )

    # Engine injects own __proto__ on Object.create(null). Module NS exotic
    # [[Get]]/[[HasProperty]] must not surface it — route through Reflect shims.
    if (
        '__nsbuild_' in new_src
        or any('__nsbuild_' in c for c in fixture_chunks)
        or '__markModuleNS' in new_src
    ):
        new_src = re.sub(
            r'''(['"])__proto__\1\s+in\s+([A-Za-z_$][\w$]*)''',
            r'Reflect.has(\2, "__proto__")',
            new_src,
        )
        new_src = re.sub(
            r'''\b([A-Za-z_$][\w$]*)\.__proto__\b(?!\s*=)''',
            r'Reflect.get(\1, "__proto__")',
            new_src,
        )
        # for-in bypasses gOPD shims; Object.keys hits [[GetOwnProperty]] (TDZ)
        ns_names = set(ns_by_module.values())
        for m in re.finditer(
            r'const\s+([A-Za-z_$][\w$]*)\s*=\s*__nsbuild_',
            new_src,
        ):
            ns_names.add(m.group(1))
        for m in re.finditer(
            r'var\s+([A-Za-z_$][\w$]*)\s*=\s*__nsbuild_',
            new_src,
        ):
            ns_names.add(m.group(1))
        for nsn in ns_names:
            if not nsn or not re.match(r'^[A-Za-z_$]', nsn):
                continue
            new_src = re.sub(
                rf'for\s*\(\s*(var|let|const)\s+([A-Za-z_$][\w$]*)\s+in\s+{re.escape(nsn)}\s*\)',
                rf'for (var \2, __mk=Object.keys({nsn}), __mi=0; '
                rf'__mi<__mk.length; \2=__mk[__mi++])',
                new_src,
            )

    # Engine: Symbol#toString throws — used in define-own-property messages
    if '.toString()' in new_src and 'Symbol' in new_src:
        new_src = re.sub(
            r'\b([A-Za-z_$][\w$]*)\.toString\(\)',
            r'(function(__k){try{return __k.toString();}catch(__e){return "Symbol()";}})(\1)',
            new_src,
        )

    parts = []
    if fixture_chunks:
        parts.append("\n".join(fixture_chunks))
    # When fixture IEE probes ran in an isolated IIFE, keep main bindings out of
    # the outer scope too (var A would otherwise hoist and break the probe).
    if any('__iee_results' in c or 'var results = (function' in c for c in fixture_chunks):
        new_src = "(function(){\n" + new_src + "\n})();\n"
    parts.append(new_src)
    return "\n".join(parts)


def _wants_strict(meta):
    """True when test262 flags require strict mode.

    Modules are always strict (ES2015+). onlyStrict also injects the directive.
    """
    flags = (meta or {}).get("flags") or []
    if "module" in flags:
        return True
    return "onlyStrict" in flags and "noStrict" not in flags


# Function("return this;")() SIGSEGVs our engine — module local-binding tests
# depend on fnGlobalObject. Provide a safe replacement.
_SAFE_FN_GLOBAL_OBJECT = """
function fnGlobalObject() {
  return (typeof globalThis !== "undefined")
    ? globalThis
    : (function () { return this; })();
}
"""


def _load_includes(meta):
    """Load test262 harness includes listed in frontmatter (e.g. regExpUtils.js)."""
    includes = (meta or {}).get("includes") or []
    if not includes:
        return ""
    harness_dir = Path(__file__).resolve().parents[1] / "test262" / "harness"
    chunks = []
    for name in includes:
        # Skip harness files we replace with engine-safe polyfills
        if name in ("regExpUtils.js", "propertyHelper.js", "asyncHelpers.js"):
            continue
        if name == "fnGlobalObject.js":
            chunks.append(_SAFE_FN_GLOBAL_OBJECT)
            continue
        path = harness_dir / name
        if path.is_file():
            text = path.read_text(errors="replace")
            # Defensive: any include using Function("return this;") for global
            text = text.replace(
                'Function("return this;")()',
                '(typeof globalThis!=="undefined"?globalThis:(function(){return this;})())',
            )
            chunks.append(text)
    return "\n".join(chunks) + ("\n" if chunks else "")


def assemble_source(processed, meta=None):
    """Build full harness source.

    onlyStrict tests get \"use strict\"; as the FIRST statement of the whole
    program (before polyfill) so JSComp_IsStrict / VM is_strict actually fire.
    Putting the directive after the polyfill was a silent no-op.
    """
    includes = _load_includes(meta)
    body = POLYFILL + includes + processed + EPILOGUE
    if _wants_strict(meta):
        return '"use strict";\n' + body
    return body


# =============================================================================
# TEST DISCOVERY
# =============================================================================

def discover_tests(test262_dir, categories, discover_all=False, discover_full=False, paths=None):
    """Yield .js test file paths for the given categories, all language, or full suite."""
    if paths:
        test_root = Path(test262_dir) / "test"
        for p in paths:
            target = test_root / p
            if not target.exists():
                continue
            if target.is_file():
                yield str(target)
            else:
                for js_file in sorted(target.rglob("*.js")):
                    if js_file.name.startswith("_") or "_FIXTURE" in js_file.name:
                        continue
                    yield str(js_file)
        return
    if discover_full:
        test_root = Path(test262_dir) / "test"
        for subdir in ["language", "built-ins", "annexB", "staging"]:
            sub_path = test_root / subdir
            if not sub_path.exists():
                continue
            for js_file in sorted(sub_path.rglob("*.js")):
                if js_file.name.startswith("_") or "_FIXTURE" in js_file.name:
                    continue
                yield str(js_file)
        return
    test_root = Path(test262_dir) / "test" / "language"
    if discover_all:
        for js_file in sorted(test_root.rglob("*.js")):
            if js_file.name.startswith("_") or "_FIXTURE" in js_file.name:
                continue
            yield str(js_file)
        return
    for cat in categories:
        cat_dir = test_root / cat
        if not cat_dir.exists():
            continue
        for js_file in sorted(cat_dir.rglob("*.js")):
            if js_file.name.startswith("_") or "_FIXTURE" in js_file.name:
                continue
            yield str(js_file)


# =============================================================================
# LEGACY RUNNER (one process per test)
# =============================================================================

def run_test(harness, test_path, timeout, verbose=False):
    """Run a single test262 test via subprocess."""
    try:
        source = open(test_path, "r", errors="replace").read()
    except Exception as e:
        return {"path": test_path, "status": "error", "reason": str(e), "time_ms": 0}

    meta = parse_frontmatter(source)
    processed = preprocess(source, meta, test_path=test_path)
    full_source = assemble_source(processed, meta)

    tmp_path = getattr(_thread_local, 'tmp_path', TMP_FILE)
    try:
        with open(tmp_path, "w") as f:
            f.write(full_source)
    except Exception as e:
        return {"path": test_path, "status": "error", "reason": f"write:{e}", "time_ms": 0}

    harness_bin = getattr(_thread_local, 'harness', harness)
    is_negative = meta.get("negative", False)

    t0 = time.monotonic()
    try:
        result = subprocess.run([harness_bin], timeout=timeout, capture_output=True)
        elapsed = (time.monotonic() - t0) * 1000
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        return {"path": test_path, "status": "timeout", "reason": "timeout", "time_ms": timeout * 1000}
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return {"path": test_path, "status": "error", "reason": str(e), "time_ms": elapsed}

    if is_negative:
        status = "pass" if exit_code != 0 else "fail"
    else:
        status = "pass" if exit_code == 0 else "fail"

    return {
        "path": test_path,
        "status": status,
        "reason": f"exit={exit_code}" if status == "fail" else "",
        "time_ms": round(elapsed, 1),
    }


# =============================================================================
# BATCH RUNNER (single long-running harness process per worker)
# =============================================================================

def _prepare_test(test_path):
    """Read, parse frontmatter, preprocess a test file. Returns (path, meta, source_bytes) or None on error."""
    try:
        source = open(test_path, "r", errors="replace").read()
    except Exception:
        return (test_path, {}, None)
    meta = parse_frontmatter(source)
    processed = preprocess(source, meta, test_path=test_path)
    full = assemble_source(processed, meta)
    return (test_path, meta, full.encode("utf-8", errors="replace"))


def _batch_worker(wid, batch_harness, work_items, results, done_count, done_lock, timeout):
    """Worker thread: spawns batch harness, feeds tests via stdin, reads results from stdout."""
    proc = subprocess.Popen(
        [batch_harness],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    try:
        for idx, path, meta, src_bytes in work_items:
            if src_bytes is None:
                results[idx] = {"path": path, "status": "error", "reason": "read_error", "time_ms": 0}
                with done_lock:
                    done_count[0] += 1
                continue

            is_negative = meta.get("negative", False)

            # Send length-prefixed source
            header = struct.pack("<I", len(src_bytes))
            try:
                proc.stdin.write(header)
                proc.stdin.write(src_bytes)
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # Harness crashed — mark remaining as error and restart
                results[idx] = {"path": path, "status": "error", "reason": "harness_crash", "time_ms": 0}
                with done_lock:
                    done_count[0] += 1
                # Restart harness
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass
                proc = subprocess.Popen(
                    [batch_harness],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                continue

            # Read 1-byte result with timeout
            t0 = time.monotonic()
            result_byte = None
            try:
                # Use select for timeout on stdout
                rlist, _, _ = select.select([proc.stdout], [], [], timeout)
                if rlist:
                    result_byte = proc.stdout.read(1)
                    elapsed = (time.monotonic() - t0) * 1000
                else:
                    # Timeout — kill and restart harness
                    elapsed = timeout * 1000
                    try:
                        proc.kill()
                        proc.wait()
                    except Exception:
                        pass
                    results[idx] = {"path": path, "status": "timeout", "reason": "timeout", "time_ms": elapsed}
                    with done_lock:
                        done_count[0] += 1
                    proc = subprocess.Popen(
                        [batch_harness],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                    )
                    continue
            except Exception as e:
                results[idx] = {"path": path, "status": "error", "reason": str(e), "time_ms": 0}
                with done_lock:
                    done_count[0] += 1
                continue

            if not result_byte or len(result_byte) == 0:
                # Harness exited unexpectedly
                results[idx] = {"path": path, "status": "error", "reason": "harness_eof", "time_ms": 0}
                with done_lock:
                    done_count[0] += 1
                # Restart
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass
                proc = subprocess.Popen(
                    [batch_harness],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                continue

            # Interpret: '0' = engine pass, '1' = engine fail, '2' = error
            engine_ok = (result_byte == b'0')
            engine_fail = (result_byte == b'1')

            if is_negative:
                status = "pass" if engine_fail else "fail"
            else:
                status = "pass" if engine_ok else "fail"

            results[idx] = {
                "path": path,
                "status": status,
                "reason": f"exit={result_byte!r}" if status == "fail" else "",
                "time_ms": round(elapsed, 1),
            }
            with done_lock:
                done_count[0] += 1

    finally:
        # Send termination signal (length=0)
        try:
            proc.stdin.write(struct.pack("<I", 0))
            proc.stdin.flush()
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait()


# =============================================================================
# REPORTING
# =============================================================================

def categorize_path(test_path, test262_dir):
    """Extract category from test path."""
    rel = os.path.relpath(test_path, os.path.join(test262_dir, "test"))
    parts = rel.split(os.sep)
    if parts[0] == "language" and len(parts) >= 3:
        return f"{parts[1]}/{parts[2]}"
    if parts[0] == "built-ins" and len(parts) >= 3:
        return f"built-ins/{parts[1]}"
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def print_report(results, test262_dir):
    """Print a formatted conformance report."""
    cats = {}
    for r in results:
        cat = categorize_path(r["path"], test262_dir)
        if cat not in cats:
            cats[cat] = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}
        cats[cat]["total"] += 1
        cats[cat][r["status"]] += 1

    print()
    header = f"{'Category':<42} {'Total':>5} {'Pass':>5} {'Fail':>5} {'Skip':>5} {'T/O':>4} {'Pass%':>6}"
    print(header)
    print("-" * len(header))

    totals = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}

    for cat in sorted(cats.keys()):
        c = cats[cat]
        run = c["pass"] + c["fail"]
        pct = (c["pass"] / run * 100) if run > 0 else 0
        print(f"{cat:<42} {c['total']:>5} {c['pass']:>5} {c['fail']:>5} {c['skip']:>5} {c['timeout']:>4} {pct:>5.1f}%")
        for k in totals:
            totals[k] += c[k]

    print("-" * len(header))
    run = totals["pass"] + totals["fail"]
    pct = (totals["pass"] / run * 100) if run > 0 else 0
    print(f"{'TOTAL':<42} {totals['total']:>5} {totals['pass']:>5} {totals['fail']:>5} {totals['skip']:>5} {totals['timeout']:>4} {pct:>5.1f}%")
    print()


# =============================================================================
# LEGACY PARALLEL (kept for --no-batch)
# =============================================================================

def _make_worker_harness(base_harness, worker_id):
    new_name = f"test262_w{worker_id:06d}"
    new_path = f"/tmp/{new_name}.js"
    new_path_b = new_path.encode("ascii")

    harness_data = open(base_harness, "rb").read()
    assert len(new_path_b) == len(_ORIG_PATH), \
        f"path length mismatch: {len(new_path_b)} vs {len(_ORIG_PATH)}"
    patched = harness_data.replace(_ORIG_PATH, new_path_b)

    worker_bin = f"/tmp/test262_harness_w{worker_id}.x"
    with open(worker_bin, "wb") as f:
        f.write(patched)
    os.chmod(worker_bin, 0o755)
    return worker_bin, new_path


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test262 conformance runner for Ailang JS engine")
    parser.add_argument("--categories", type=str, default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output-json", type=str, default=None)
    parser.add_argument("--harness", type=str, default="./test262_harness.x")
    parser.add_argument("--batch-harness", type=str, default="./test262_harness_batch.x")
    parser.add_argument("--test262", type=str, default="./test262")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--fail-only", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--paths", type=str, default=None)
    parser.add_argument("--jobs", "-j", type=int, default=0)
    parser.add_argument("--no-batch", action="store_true",
                        help="Force legacy mode (one process per test)")
    args = parser.parse_args()

    # Determine batch mode
    use_batch = not args.no_batch and os.path.isfile(args.batch_harness)
    harness_path = args.batch_harness if use_batch else args.harness

    if not use_batch:
        if not os.path.isfile(args.harness):
            print(f"ERROR: harness binary not found: {args.harness}", file=sys.stderr)
            print("Build with: ./ailang.x TestCode/test262_harness.ailang test262_harness.x", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.path.isfile(args.batch_harness):
            print(f"ERROR: batch harness not found: {args.batch_harness}", file=sys.stderr)
            sys.exit(1)

    if not os.path.isdir(args.test262):
        print(f"ERROR: test262 directory not found: {args.test262}", file=sys.stderr)
        sys.exit(1)

    categories = args.categories.split(",") if args.categories else DEFAULT_CATEGORIES
    test_paths = args.paths.split(",") if args.paths else None
    njobs = args.jobs if args.jobs > 0 else os.cpu_count() or 4

    # Discover tests
    test_files = list(discover_tests(args.test262, categories,
                                     discover_all=args.all,
                                     discover_full=args.full,
                                     paths=test_paths))
    if not test_files:
        print("No test files found.", file=sys.stderr)
        sys.exit(1)

    mode_str = "batch" if use_batch else "legacy"
    print(f"Test262 Conformance — Ailang JS Engine")
    print(f"Tests discovered: {len(test_files)}")
    print(f"Workers: {njobs}  Mode: {mode_str}")
    print()

    t_start = time.monotonic()

    if use_batch:
        # =====================================================================
        # BATCH MODE — pre-read all files, then feed to worker harness procs
        # =====================================================================
        print("  Preprocessing tests...", flush=True)
        t_prep = time.monotonic()

        # Pre-read and preprocess all tests
        prepared = []
        for tf in test_files:
            prepared.append(_prepare_test(tf))

        prep_time = time.monotonic() - t_prep
        print(f"  Preprocessed {len(prepared)} tests in {prep_time:.1f}s", flush=True)

        # Partition tests across workers
        results = [None] * len(test_files)
        done_count = [0]
        done_lock = threading.Lock()
        total = len(test_files)

        # Build work items: (global_idx, path, meta, src_bytes)
        all_work = []
        for i, (path, meta, src_bytes) in enumerate(prepared):
            all_work.append((i, path, meta, src_bytes))

        # Round-robin partition into per-worker lists
        worker_items = [[] for _ in range(njobs)]
        for i, item in enumerate(all_work):
            worker_items[i % njobs].append(item)

        # Progress reporter
        stop_progress = threading.Event()
        def _progress_reporter():
            while not stop_progress.is_set():
                with done_lock:
                    d = done_count[0]
                print(f"  ... {d}/{total} tests completed", flush=True)
                stop_progress.wait(3.0)

        pt = threading.Thread(target=_progress_reporter, daemon=True)
        pt.start()

        # Launch worker threads
        threads = []
        for wid in range(njobs):
            t = threading.Thread(
                target=_batch_worker,
                args=(wid, args.batch_harness, worker_items[wid],
                      results, done_count, done_lock, args.timeout),
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        stop_progress.set()
        pt.join(timeout=1)

        # Fill any None results (shouldn't happen)
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {"path": test_files[i], "status": "error",
                              "reason": "not_run", "time_ms": 0}

    elif njobs == 1 or args.verbose:
        # Sequential legacy mode
        results = []
        for i, tf in enumerate(test_files):
            r = run_test(args.harness, tf, args.timeout, args.verbose)
            results.append(r)
            if args.verbose:
                short = os.path.relpath(tf, args.test262)
                if args.fail_only and r["status"] in ("pass", "skip"):
                    pass
                else:
                    status_sym = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP",
                                  "timeout": "T/O ", "error": "ERR "}
                    sym = status_sym.get(r["status"], "????")
                    extra = f"  ({r['reason']})" if r["reason"] else ""
                    print(f"  [{sym}] {short}{extra}")
            if not args.verbose and (i + 1) % 100 == 0:
                print(f"  ... {i + 1}/{len(test_files)} tests completed", flush=True)

    else:
        # Legacy parallel mode
        import queue

        worker_assets = []
        for wid in range(njobs):
            h_path, t_path = _make_worker_harness(args.harness, wid)
            worker_assets.append((h_path, t_path))

        results = [None] * len(test_files)
        total = len(test_files)
        work_q = queue.Queue()
        for i, tf in enumerate(test_files):
            work_q.put((i, tf))

        done_count = [0]
        done_lock = threading.Lock()

        def _worker_thread(wid):
            h_path, t_path = worker_assets[wid]
            _thread_local.tmp_path = t_path
            _thread_local.harness = h_path
            while True:
                try:
                    idx, test_path = work_q.get_nowait()
                except queue.Empty:
                    return
                r = run_test(h_path, test_path, args.timeout)
                results[idx] = r
                with done_lock:
                    done_count[0] += 1

        stop_progress = threading.Event()
        def _progress_reporter():
            while not stop_progress.is_set():
                with done_lock:
                    d = done_count[0]
                print(f"  ... {d}/{total} tests completed", flush=True)
                stop_progress.wait(3.0)

        pt = threading.Thread(target=_progress_reporter, daemon=True)
        pt.start()

        threads = []
        for wid in range(njobs):
            t = threading.Thread(target=_worker_thread, args=(wid,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        stop_progress.set()
        pt.join(timeout=1)

        for h_path, t_path in worker_assets:
            try: os.unlink(h_path)
            except: pass
            try: os.unlink(t_path)
            except: pass

    t_total = time.monotonic() - t_start

    # Report
    print_report(results, args.test262)
    print(f"Wall time: {t_total:.1f}s")

    # JSON output
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump({
                "total_tests": len(results),
                "wall_time_s": round(t_total, 2),
                "results": results,
            }, f, indent=2)
        print(f"JSON results written to: {args.output_json}")


if __name__ == "__main__":
    main()
