# Library.JSON (ailang)

## NAME
`Library.JSON` — RFC 8259 JSON parser and builder using tagged-value DOM

## SYNOPSIS
```ailang
LibraryImport.JSON
```
> Requires: `LibraryImport.Arrays`, `LibraryImport.StringUtils`

## DESCRIPTION

JSON provides a complete RFC 8259-compliant parser and serializer built on a
**tagged-value** representation. Every JSON value is a 16-byte heap allocation:

| Offset | Size | Field |
|--------|------|-------|
| 0–7  | 8 bytes | Type tag (one of the `JType` constants) |
| 8–15 | 8 bytes | Value: `Address` for strings/objects/arrays, `Integer` for numbers/bools |

### Type tags (`JType`)

| Constant | Value | Payload |
|----------|-------|---------|
| `JType.NULL`   | 0 | — |
| `JType.STRING` | 1 | Address of null-terminated String |
| `JType.NUMBER` | 2 | Address of raw number literal String |
| `JType.BOOL`   | 3 | Integer: 0 or 1 |
| `JType.OBJECT` | 4 | Address of SHash (String→tagged value) via Library.Arrays |
| `JType.ARRAY`  | 5 | Address of Array of tagged values (Library.Array / Library.Arrays) |

Objects are backed by `SHash` (from `Library.Arrays`); arrays are backed by `Library.Array`. Modern code may also use `Library.Hash` for new JSON-like structures.

---

## VALUE CONSTRUCTION

### Creating containers

```ailang
JSON.NewObject   → obj       # empty JSON object (SHash-backed via Arrays)
JSON.NewArray    → arr       # empty JSON array  (Array-backed)
```

### Setting fields on objects

All `Set*` functions take `obj: Address, key: Address, value`. The key must be a
null-terminated String (not a JSON string value).

| Function | Value type |
|----------|------------|
| `JSON.SetString(obj, key, s)`   | String |
| `JSON.SetNumber(obj, key, n)`   | String (raw literal) |
| `JSON.SetBool(obj, key, b)`     | Integer (0 or 1) |
| `JSON.SetNull(obj, key)`        | — |
| `JSON.SetObject(obj, key, v)`   | JSON object value |
| `JSON.SetArray(obj, key, v)`    | JSON array value |

### Appending to arrays

All `Push*` functions take `arr: Address, value` and return the new array length.

| Function | Value type |
|----------|------------|
| `JSON.PushString(arr, s)`   | String |
| `JSON.PushNumber(arr, n)`   | String (raw literal) |
| `JSON.PushBool(arr, b)`     | Integer (0 or 1) |
| `JSON.PushNull(arr)`        | — |
| `JSON.PushObject(arr, v)`   | JSON object value |
| `JSON.PushArray(arr, v)`    | JSON array value |

---

## VALUE ACCESS (type-checked)

Each `Get*` accessor returns the typed payload or **0 / nil** if the key is
missing or the stored value is of a different type.

### Reading object fields

| Function | Returns |
|----------|---------|
| `JSON.GetString(obj, key)`  | Address (String) or 0 |
| `JSON.GetNumber(obj, key)`  | Address (raw literal String) or 0 |
| `JSON.GetBool(obj, key)`    | Integer (0 or 1) or 0 |
| `JSON.GetObject(obj, key)`  | Address (JSON object) or 0 |
| `JSON.GetArray(obj, key)`   | Address (JSON array) or 0 |
| `JSON.GetType(obj, key)`    | Integer 0–5 (JType tag) |

### Reading array elements

| Function | Returns |
|----------|---------|
| `JSON.ArrayGet(arr, index)` | Address (tagged value) or 0 if OOB |
| `JSON.ArrayLength(arr)`    | Integer (element count) |

### Type casting / unwrapping

After retrieving a tagged value (e.g. from `ArrayGet`), cast it to the expected type:

| Function | Returns |
|----------|---------|
| `JSON.AsObject(v)`  | Address (object/HashMap) or 0 |
| `JSON.AsArray(v)`   | Address (array/XArray) or 0 |
| `JSON.AsString(v)`  | Address (String) or 0 |
| `JSON.AsNumber(v)`  | Address (raw number String) or 0 |
| `JSON.AsBool(v)`    | Integer (0 or 1) or 0 |

### Tag introspection (rarely needed)

```
JSON.Tag(v)      → Integer  (type tag 0–5)
JSON.TagType(v)   → Integer  (same as Tag)
JSON.TagValue(v)  → Address  (raw payload at offset 8)
```

---

## SERIALIZATION

```
JSON.Serialize(v)         → Address (compact JSON String, caller frees)
JSON.EscapeString(s)      → Address (JSON-escaped copy of String)
JSON.SerializeObject(obj) → Address (serializes to `{...}`, caller frees)
JSON.SerializeArray(arr)  → Address (serializes to `[...]`, caller frees)
```

`Serialize` delegates to `SerializeObject` or `SerializeArray` based on the
type tag. All three return a freshly allocated String the caller must free.

`EscapeString` produces a JSON-safe quoted form with backslash escapes for
`"`, `\`, `/`, newline, carriage-return, tab, backspace, and form-feed.
Non-ASCII bytes (≥0x80) are emitted as `\u00XX` escapes.

---

## PARSING

```
JSON.ParseJSON(text)    → Address (root tagged value, or 0 on error)
JSON.ParseValue(text)   → Address (next value at current JParse.pos)
JSON.ParseObject(text)  → Address (object at current JParse.pos)
JSON.ParseArray(text)   → Address (array at current JParse.pos)
JSON.ParseString(text)  → Address (string at current JParse.pos)
JSON.ParsePrimitive(text) → Address (null/true/false/number at current pos)
```

### Parser state (`JParse`)

Parsing uses a shared global state pool. Before calling `ParseJSON`, the
caller must set:

| Field | Meaning |
|-------|---------|
| `JParse.buffer` | Address of the raw JSON text |
| `JParse.size`   | Integer: total byte length of the text |
| `JParse.pos`    | **Must** be set to 0 before `ParseJSON` |
| `JParse.error`  | Set to 1 by the parser on failure |
| `JParse.error_msg` | Address of error message string (set on failure) |

`ParseJSON` resets `JParse.pos` to 0 internally. After a successful parse,
`JParse.error` is 0 and `JParse.error_msg` is 0.

### Low-level / internal parsers

These operate from the current `JParse.pos` and advance it:

```
JSON.SkipWhitespace()   → void    (skips spaces, tabs, newlines, carriage returns)
JSON.BuildObject()       → Address (creates empty HashMap-backed object)
JSON.BuildArray()        → Address (creates empty XArray-backed array)
JSON.ParseDataField()    → Address (parses "key": value, used internally)
```

---

## CLEANUP

```
JSON.Free(v)        → Recursively frees a tagged value tree
JSON.FreeObject(obj) → Frees an object and all its values
JSON.FreeArray(arr)  → Frees an array and all its elements
```

`Free` dispatches based on the type tag (calls `FreeObject` or `FreeArray` for
containers, deallocates strings, etc.). After a `Free`, the value pointer is
**invalid** — do not reuse.

---

## MEMORY

| Allocation | Freed by |
|---|---|
| Tagged value nodes (16 bytes) | `JSON.Free` (or the container-specific free) |
| String values | `JSON.Free` (container traversal) |
| Serialization output | **Caller** must `Deallocate` the returned String |
| Parse error message | Internal; overwritten on next parse |

---

## EXAMPLE: Build and serialize

```ailang
LibraryImport.JSON
LibraryImport.StringUtils

# Build a response object
JSON.NewObject  → obj
JSON.SetString  obj  "status"   "ok"
JSON.SetNumber  obj  "count"    "42"
JSON.SetBool    obj  "cached"   0

# Push into an array
JSON.NewArray   → arr
JSON.PushString arr  "alpha"
JSON.PushString arr  "beta"
JSON.PushString arr  "gamma"
JSON.SetArray   obj  "items"  arr

# Serialize
out = JSON.Serialize(obj)
StringUtils.PrintString out   # {"status":"ok","count":42,"cached":false,"items":["alpha","beta","gamma"]}
Deallocate out, 0
JSON.Free obj
```

## EXAMPLE: Parse and walk

```ailang
LibraryImport.JSON
LibraryImport.StringUtils

# Set up parser state
JParse.buffer = text
JParse.size   = StringUtils.StringLength(text)
JParse.pos    = 0

result = JSON.ParseJSON(text)
IfCondition EqualTo(result, 0) ThenBlock: {
    StringUtils.PrintString "[ERROR] "
    StringUtils.PrintString JParse.error_msg
    StringUtils.PrintString "\n"
    ReturnValue(1)
}

obj   = JSON.AsObject(result)
name  = JSON.GetString(obj, "name")       # "Alice"
scores = JSON.GetArray(obj, "scores")     # [95, 87, 91]
len   = JSON.ArrayLength(scores)          # 3
first = JSON.ArrayGet(scores, 0)          # tagged value for 95
n     = JSON.AsNumber(first)              # "95" (raw literal)

JSON.Free result
```

## EXAMPLE: Parse → tweak → re-serialize

```ailang
JParse.buffer = text
JParse.size   = StringUtils.StringLength(text)
JParse.pos    = 0

root = JSON.ParseJSON(text)
obj  = JSON.AsObject(root)
JSON.SetString obj  "extra"  "added"
JSON.SetBool   obj  "flag"   1
out = JSON.Serialize(root)
# use out...
Deallocate out, 0
JSON.Free root
```

---

## CONSTANTS

| Pool | Constant | Value |
|------|----------|-------|
| JType | NULL   | 0 |
| JType | STRING | 1 |
| JType | NUMBER | 2 |
| JType | BOOL   | 3 |
| JType | OBJECT | 4 |
| JType | ARRAY  | 5 |

---

## SEE ALSO
- `Library.StringUtils` — string length, printing, concatenation
- `Library.Arrays` (SHash + Array) — backing store for JSON objects and arrays
- `Library.Hash` — newer, faster hash table (recommended for new non-JSON work)
- `Library.Array` — dynamic arrays used for JSON arrays
- `Library.HTTP` — transport that typically carries JSON payloads
- `Library.Socket` — low-level TCP transport

---

## VERSION
2026-05-16 — rewritten to match actual v2.2 tagged-value API

## COPYRIGHT
Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
