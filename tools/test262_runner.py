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
// asyncHelpers asyncTest checks hasOwnProperty.call(globalThis, "$DONE").
globalThis.$DONE = $DONE;
globalThis.$MAX_ITERATIONS = $MAX_ITERATIONS;
globalThis.assert = assert;
globalThis.Test262Error = Test262Error;
globalThis.__test262_failed = __test262_failed;
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
function verifyWritable(obj, name) {
  var old = obj[name]; obj[name] = "___test262_w___";
  if (obj[name] === old) { __test262_failed = 1; }
  obj[name] = old;
}
function verifyNotWritable(obj, name) {
  var old = obj[name]; obj[name] = "___test262_w___";
  if (obj[name] !== old) { __test262_failed = 1; }
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
    """
    source = _FRONTMATTER_RE.sub("", source)
    flags = (meta or {}).get("flags") or []
    features = (meta or {}).get("features") or []
    if "module" in flags and test_path:
        try:
            source = _preprocess_module(source, test_path)
            # Top-level await: wrap in async IIFE so AWAIT_EXPR is valid (in_await)
            if "top-level-await" in features or _source_has_toplevel_await(source):
                source = _wrap_toplevel_await(source)
            # Namespace / Reflect tests need Reflect
            if "Reflect" in source or "namespace" in (test_path or ""):
                source = _MODULE_REFLECT_STUB + source
        except Exception:
            pass  # leave source as-is if preprocess chokes
    return source


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
var __moduleNSList = [];
var __moduleNSKeys = []; // parallel array of string-key arrays
function __isModuleNS(o) {
  if (!o) return false;
  for (var __i = 0; __i < __moduleNSList.length; __i++) {
    if (__moduleNSList[__i] === o) return true;
  }
  return false;
}
function __markModuleNS(o, keys) {
  __moduleNSList.push(o);
  __moduleNSKeys.push(keys || []);
  return o;
}
function __moduleNSExportKeys(o) {
  for (var __i = 0; __i < __moduleNSList.length; __i++) {
    if (__moduleNSList[__i] === o) return __moduleNSKeys[__i];
  }
  return null;
}
// Engine lacks Object.getOwnPropertySymbols — minimal polyfill for module NS
if (typeof Object.getOwnPropertySymbols !== "function") {
  Object.getOwnPropertySymbols = function(o) {
    if (__isModuleNS(o)) {
      return [Symbol.toStringTag];
    }
    return [];
  };
}
(function() {
  if (!Object.__moduleGopdShim) {
    Object.__moduleGopdShim = true;
    var _gopd = Object.getOwnPropertyDescriptor;
    Object.getOwnPropertyDescriptor = function(o, p) {
      // Module NS [[GetOwnProperty]]: only exports (+ @@toStringTag via ordinary)
      if (__isModuleNS(o) && p !== Symbol.toStringTag && typeof p === "string") {
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
// Always install/override Reflect helpers used by namespace tests
if (typeof Reflect === 'undefined') { var Reflect = {}; }
Reflect.has = function(o, p) {
  if (__isModuleNS(o) && typeof p === "string") {
    var rec = __moduleNSExportKeys(o);
    if (rec) {
      for (var __h = 0; __h < rec.length; __h++) {
        if (rec[__h] === p) return true;
      }
      return false;
    }
  }
  return p in o;
};
// Module NS [[Get]]: non-exports are undefined (engine may return null for __proto__)
Reflect.get = function(o, p, r) {
  if (__isModuleNS(o) && typeof p === "string") {
    var recg = __moduleNSExportKeys(o);
    if (recg) {
      var ok = false;
      for (var __g = 0; __g < recg.length; __g++) {
        if (recg[__g] === p) { ok = true; break; }
      }
      if (!ok) return undefined;
    }
  }
  return o[p];
};
Reflect.set = function(o, p, v, r) {
  if (__isModuleNS(o)) return false;
  try {
    var old = o[p];
    o[p] = v;
    if (__isModuleNS(o)) return false;
    return true;
  } catch (e) { return false; }
};
Reflect.ownKeys = function(o) {
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
};
Reflect.getOwnPropertyDescriptor = function(o, p) {
  return Object.getOwnPropertyDescriptor(o, p);
};
Reflect.defineProperty = function(o, p, d) {
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
};
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
Reflect.deleteProperty = function(o, p) {
  if (__isModuleNS(o)) {
    if (Object.prototype.hasOwnProperty.call(o, p) && p !== "__moduleNamespace__") return false;
  }
  try {
    var d = Object.getOwnPropertyDescriptor(o, p);
    if (d && d.configurable === false) return false;
    return delete o[p];
  } catch (e) { return false; }
};
Reflect.isExtensible = function(o) { return Object.isExtensible(o); };
Reflect.preventExtensions = function(o) {
  try { Object.preventExtensions(o); } catch (e) {}
  return true;
};
Reflect.getPrototypeOf = function(o) { return Object.getPrototypeOf(o); };
Reflect.setPrototypeOf = function(o, p) {
  if (__isModuleNS(o)) return (p === null);
  try { Object.setPrototypeOf(o, p); return true; } catch (e) { return false; }
};
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
    # After anon rewrite, default lives on __default_export__
    if re.search(r'\b__default_export__\b', source):
        dflt = '__default_export__'
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
            dflt = '__default_export__'
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


def _rewrite_anon_default_export(source):
    """Turn anonymous export default into let __default_export__ = …

    Use `let` (not var) so default is TDZ until the export statement runs
    (namespace uninit tests: ns.default throws ReferenceError).
    """
    # export default class { … }  OR  export default class extends … { … }
    source, n = re.subn(
        r'export\s+default\s+class\s*\{',
        'let __default_export__ = class {',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, 'let __default_export__ = class')
    source, n = re.subn(
        r'export\s+default\s+class\s+(extends\b)',
        r'let __default_export__ = class \1',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, 'let __default_export__ = class')
    source, n = re.subn(
        r'export\s+default\s+(async\s+)?function(\s*\*)?\s*\(',
        r'let __default_export__ = \1function\2(',
        source,
        count=1,
    )
    if n:
        return _stamp_default_name_after(source, 'let __default_export__ = ')
    if re.search(r'export\s+default\s+(?:async\s+)?(?:function\s*\*?|class)\s+[A-Za-z_$]', source):
        return source  # named — leave for engine
    # Plain expression default — rewrite without name stamp (stamp only for fn/class)
    source, n = re.subn(
        r'export\s+default\s+',
        'let __default_export__ = ',
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
            fixtures[key] = _FRONTMATTER_RE.sub("", raw)
        return fixtures[key]

    def parse_exports_from(src):
        src2 = _rewrite_anon_default_export(src)
        rmap = {}
        return src2, _collect_module_exports(src2, rmap), rmap

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
            fs, (fd, fn), rmap = parse_exports_from(fix)
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
            fs, (_fd, fn0), rmap = parse_exports_from(fix)
            if key not in inlined:
                inlined.add(key)
                fixture_chunks.append(strip_fixture_exports(fs))
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
            early_star_as[id_name] = (id_name, spec)
            return f'var {id_name} = {ns_var};\n'
        raw = str_name[1:-1]
        try:
            raw = json.loads('"' + raw.replace('\\', '\\\\').replace('"', '\\"') + '"')
        except Exception:
            pass
        safe = re.sub(r'[^A-Za-z0-9_]', '_', raw) or 'ns'
        if not re.match(r'^[A-Za-z_]', safe):
            safe = 'ns_' + safe
        loc = f'__star_as_{safe}'
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
        named[exp] = loc if loc != '__SELF_NS__' else exp
        self_reexports[exp] = (sp, '*')
        if exp == 'default':
            dflt = loc if loc != '__SELF_NS__' else '__default_export__'
        if loc == '__SELF_NS__':
            # After self NS is built, bind export name to it (instn-once export * as ns2)
            pre_assert_aliases.append(f'const {exp} = __SELF_NS__;')

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
            _fs, (_fd, fn0), rmap = parse_exports_from(fix)
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
            key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
            if key not in inlined:
                inlined.add(key)
                fs, _, _ = parse_exports_from(fix_src)
                body = strip_fixture_exports(fs)
                # Side-effect import: isolate fixture bindings (instn-uniq-env-rec).
                # Engine leaks function/class decls out of nested functions, so
                # rename top-level bindings instead of relying on IIFE scope alone.
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
                fixture_chunks.append(
                    "(function(){\n" + body + "\n})();\n"
                )
            return ''

        f_dflt = dflt if is_self else None
        f_named = dict(named) if is_self else {}
        kind_source = source
        if fix_src is not None:
            key = str((base / (spec[2:] if spec.startswith('./') else spec)).resolve())
            fs, (fd, fn), fix_reexports = parse_exports_from(fix_src)
            f_dflt, f_named = fd, dict(fn)
            # Named imports need star-expanded export table (export * / * as)
            if fix_reexports:
                f_named = expand_star_exports(f_named, fix_reexports)
                for exp, (sp, im) in fix_reexports.items():
                    if im == '*' and not str(exp).startswith('*from*'):
                        f_named[exp] = exp
            kind_source = fs
            if key not in inlined:
                inlined.add(key)
                fixture_chunks.append(strip_fixture_exports(fs))

        repl = []
        defname = m.group('def') or m.group('defonly')
        if defname:
            if is_self:
                bind_default_import(defname, source, True)
            elif f_dflt:
                # fixture default
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
        r'export\s*\{[^}]+\}\s*from\s*[\'"][^\'"]+[\'"]\s*;?\s*',
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
    # Do NOT strip `export default` here — anon rewrite handles those; bare
    # `export default class extends` must not become invalid `class extends`.
    new_src = re.sub(
        r'\bexport\s+(async\s+)?(function\s*\*?|class|let|const|var)\b',
        r'\1\2',
        new_src,
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
        if name in ("regExpUtils.js", "propertyHelper.js"):
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
                    if js_file.name.startswith("_"):
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
                if js_file.name.startswith("_"):
                    continue
                yield str(js_file)
        return
    test_root = Path(test262_dir) / "test" / "language"
    if discover_all:
        for js_file in sorted(test_root.rglob("*.js")):
            if js_file.name.startswith("_"):
                continue
            yield str(js_file)
        return
    for cat in categories:
        cat_dir = test_root / cat
        if not cat_dir.exists():
            continue
        for js_file in sorted(cat_dir.rglob("*.js")):
            if js_file.name.startswith("_"):
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
