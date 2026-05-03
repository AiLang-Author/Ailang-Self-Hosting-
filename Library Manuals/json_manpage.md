# Library.JSON(ailang)

## NAME
`Library.JSON` — RFC 8259 JSON parser and emitter with DOM and streaming modes

## SYNOPSIS
```
LibraryImport.JSON
```
> Requires: `LibraryImport.XArrays`, `LibraryImport.HashMap`

## DESCRIPTION
JSON provides full RFC 8259 compliance for parsing and generating JSON text. It supports two usage modes: (1) a DOM (Document Object Model) mode that builds an in-memory tree of JSON values, and (2) a streaming callback mode for large documents where the caller registers event handlers.

The value model represents JSON types as tagged unions.

| JSON type | AILang type tag | Payload |
|---|---|---|
| null | 0 | — |
| boolean | 1 | Integer 0 or 1 |
| number | 2 | String (raw literal) or Float |
| string | 3 | String (decoded) |
| array | 4 | XArray of JSON values |
| object | 5 | HashMap (String→JSON value) |

Error reporting includes line/column position and a descriptive message.

## FUNCTIONS — DOM MODE

```
Function.JSON.parse
    Input:  text: Address
    Output: Address  (root JSON value, or nil on error)
```
Parses a complete JSON document from a null-terminated string. Returns the root value. On parse error, returns nil and parks the error message accessible via `JSON.lastError`.

```
Function.JSON.parseLen
    Input:  text: Address, length: Integer
    Output: Address
```
Like `parse` but consumes exactly `length` bytes from the buffer (not null-terminated). Useful for parsing JSON embedded in binary protocols.

```
Function.JSON.emit
    Input:  value: Address
    Output: Address  (String)
```
Serialises a JSON value tree into a compact (no whitespace) JSON text string. The caller must free the returned string.

```
Function.JSON.emitPretty
    Input:  value: Address, indent: Integer
    Output: Address
```
Serialises with indentation. `indent` specifies the number of spaces per nesting level (typically 2 or 4).

```
Function.JSON.lastError
    Input:  —
    Output: Address  (String or nil)
```
Returns the last parse error message as a human-readable string. Returns nil if the last parse succeeded.

```
Function.JSON.lastErrorPos
    Input:  —
    Output: Integer  (byte offset, or -1)
```
Returns the byte offset of the last parse error, or -1 if none.

## FUNCTIONS — VALUE CONSTRUCTION

```
Function.JSON.newNull
    Input:  —
    Output: Address
```

```
Function.JSON.newBool
    Input:  b: Integer
    Output: Address
```

```
Function.JSON.newNumber
    Input:  s: Address
    Output: Address
```
Accepts the raw number literal as a String. The stored representation preserves the original text for faithful re-emission.

```
Function.JSON.newString
    Input:  s: Address
    Output: Address
```
Copies the given string into a JSON string value.

```
Function.JSON.newArray
    Input:  —
    Output: Address
```
Returns an empty JSON array backed by an XArray.

```
Function.JSON.newObject
    Input:  —
    Output: Address
```
Returns an empty JSON object backed by a HashMap.

```
Function.JSON.arrayPush
    Input:  array: Address, value: Address
    Output: Integer  (new length)
```
Appends a value to a JSON array.

```
Function.JSON.arrayGet
    Input:  array: Address, index: Integer
    Output: Address
```
Returns the value at `index` (0-based), or nil if out of bounds.

```
Function.JSON.objectPut
    Input:  obj: Address, key: Address, value: Address
    Output: Integer
```
Inserts a key-value pair into a JSON object. `key` must be a JSON string value.

```
Function.JSON.objectGet
    Input:  obj: Address, key: Address
    Output: Address
```
Looks up a key in a JSON object. `key` must be a JSON string.

## FUNCTIONS — TYPE QUERY

```
Function.JSON.typeOf
    Input:  value: Address
    Output: Integer  (0–5)
```
Returns the type tag: 0=null, 1=bool, 2=number, 3=string, 4=array, 5=object.

```
Function.JSON.asBool
    Input:  value: Address
    Output: Integer
```

```
Function.JSON.asNumber
    Input:  value: Address
    Output: Address  (raw string)
```

```
Function.JSON.asString
    Input:  value: Address
    Output: Address
```

```
Function.JSON.asArray
    Input:  value: Address
    Output: Address
```

```
Function.JSON.asObject
    Input:  value: Address
    Output: Address
```
Type-specific accessors. Return nil if the value is not of the expected type.

```
Function.JSON.free
    Input:  value: Address
    Output: —
```
Recursively frees a JSON value tree.

## FUNCTIONS — STREAMING

```
Function.JSON.streamParse
    Input:  text: Address, callbacks: Address
    Output: Integer  (0 = success, 1 = error)
```
Incremental streaming parser. `callbacks` is a HashMap mapping event names (String) to callback functions. Events: `onObjectStart`, `onObjectEnd`, `onArrayStart`, `onArrayEnd`, `onKey`, `onString`, `onNumber`, `onBool`, `onNull`.

## CONSTANTS

| Constant | Value |
|---|---|
| `JSON.TYPE_NULL` | 0 |
| `JSON.TYPE_BOOL` | 1 |
| `JSON.TYPE_NUMBER` | 2 |
| `JSON.TYPE_STRING` | 3 |
| `JSON.TYPE_ARRAY` | 4 |
| `JSON.TYPE_OBJECT` | 5 |

## MEMORY

| Allocation | Freed by |
|---|---|
| Value nodes | `JSON.free` (recursive) |
| Emit string | Caller |
| Parse error string | Internal, overwritten on next parse |

## EXAMPLE

```ailang
LibraryImport.JSON
LibraryImport.String

# Parse a JSON string
String.literal  '{"name":"Alice","scores":[95,87,91]}'  → src
JSON.parse  src  → doc

# Read fields
JSON.typeOf  doc  → t  # 5 = OBJECT
JSON.objectGet  doc  (String.literal "name")  → nameVal
JSON.asString    nameVal                       → nameStr
String.print     nameStr                       # Alice

# Modify and emit
JSON.objectPut  doc  (String.literal "extra")  (JSON.newBool 1)
JSON.emitPretty  doc  2  → out
String.print  out
JSON.free  doc
JSON.free  out
```

## SEE ALSO
`Library.String` — string manipulation for keys and values
`Library.HashMap` — backing store for JSON objects
`Library.XArrays` — backing store for JSON arrays
`Library.Socket` / `Library.HTTP` — typical transport layers carrying JSON

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
