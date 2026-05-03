# Library.XArrays(ailang)

## NAME
`Library.XArrays` — generic typed array macros: `new`, `push`, `pop`, `get`, `set`, `len`, `free`

## SYNOPSIS
```
LibraryImport.XArrays
```
> Requires: `LibraryImport.TArrays`

## DESCRIPTION
XArrays is a **compile-time generic macro layer** over TArrays. It generates type-safe accessor functions specialised for a particular element type, eliminating the manual element-size arithmetic and pointer casting required when using TArrays directly.

Each instantiation produces a family of functions operating on arrays of one concrete type. The macro expansion is zero-cost: all functions inline to direct TArrays calls with the element size baked in.

| Concept | Detail |
|---|---|
| Backing store | TArrays (tiered vector) |
| Type parameter | Any AILang primitive: Integer, Float, Address (pointer) |
| Code generation | Compile-time macro expansion |
| Generated functions | new, push, pop, get, set, len, free, forEach |
| Overhead | Zero (identical machine code to hand-written TArrays calls) |

## MACROS

### Instantiation

```
Macro.XArrays.define
    Input:  typeName: String, typeSize: Integer
    Output: —
```
Defines a new typed array family. After calling this macro, the following functions become available for the named type:

- `XArrays_<typeName>.new`
- `XArrays_<typeName>.push`
- `XArrays_<typeName>.pop`
- `XArrays_<typeName>.get`
- `XArrays_<typeName>.set`
- `XArrays_<typeName>.len`
- `XArrays_<typeName>.free`
- `XArrays_<typeName>.forEach`

Common predefined families:

| Family | Element type | Size |
|---|---|---|
| `XArrays_Int` | Integer | 8 |
| `XArrays_Float` | Float | 8 |
| `XArrays_Ptr` | Address | 8 |
| `XArrays_Byte` | byte | 1 |
| `XArrays_Int32` | 32-bit integer | 4 |

## GENERATED FUNCTIONS

For a type family `XArrays_T`:

```
Function.XArrays_T.new
    Input:  —
    Output: Address  (array handle)
```
Creates an empty typed array.

```
Function.XArrays_T.push
    Input:  arr: Address, value: T
    Output: Integer  (new length)
```
Appends a value of type T. The value is passed by value (Integer/Float) or by address (Pointer).

```
Function.XArrays_T.pop
    Input:  arr: Address
    Output: T  (the removed value, or type-default if empty)
```
Removes and returns the last element. Returns 0/null if the array was empty.

```
Function.XArrays_T.get
    Input:  arr: Address, index: Integer
    Output: T
```
Returns the element at `index`. Returns type-default (0, 0.0, nil) if out of bounds.

```
Function.XArrays_T.set
    Input:  arr: Address, index: Integer, value: T
    Output: Integer  (1 = success, 0 = out of bounds)
```
Overwrites the element at `index`.

```
Function.XArrays_T.len
    Input:  arr: Address
    Output: Integer
```

```
Function.XArrays_T.free
    Input:  arr: Address
    Output: —
```

```
Function.XArrays_T.forEach
    Input:  arr: Address, callback: Address, userdata: Address
    Output: —
```
Calls `callback(value, index, userdata)` for each element.

## CONVENIENCE: Dynamic Typing

For code that needs to work with arrays of unknown type at compile time, the library also provides a dynamic interface that wraps the element size:

```
Function.XArrays.newSized
    Input:  elementSize: Integer
    Output: Address
```
Equivalent to `TArrays.new`. Raw (untyped) handle.

```
Function.XArrays.pushSized
    Input:  arr: Address, src: Address
    Output: Integer
```

```
Function.XArrays.getSized
    Input:  arr: Address, index: Integer
    Output: Address  (pointer to element)
```

## MEMORY
Same as TArrays. Each typed family stores the element size in the handle (inherited from TArrays).

## EXAMPLE

```ailang
LibraryImport.XArrays

# Integer array
XArrays_Int.new    → ia
XArrays_Int.push   ia  42   → _
XArrays_Int.push   ia  99   → _
XArrays_Int.push   ia  7    → _
XArrays_Int.get    ia  1    → v  # 99
XArrays_Int.pop    ia        → _  # removes 7
XArrays_Int.len    ia        → n  # 2
XArrays_Int.forEach ia  (Label @printEach)  0
XArrays_Int.free   ia

# Pointer array (store string handles)
XArrays_Ptr.new    → pa
String.literal "hello"  → s1
XArrays_Ptr.push  pa  s1  → _
XArrays_Ptr.free  pa
```

## SEE ALSO
`Library.TArrays` — underlying tiered vector implementation
`Library.HashMap` — key-value mapping, often paired with typed arrays
`Library.SortedSet` — ordered set using typed arrays internally

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
