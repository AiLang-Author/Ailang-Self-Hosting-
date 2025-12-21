# AILang Function Calls and Nesting Guide

## Overview

AILang follows the x86-64 System V ABI for function calls. Understanding the constraints and best practices for function nesting is critical for writing efficient, reliable code.

---

## Parameter Limits

Functions may have **at most 6 parameters** passed in registers:

| Parameter | Register |
|-----------|----------|
| 1st | RDI |
| 2nd | RSI |
| 3rd | RDX |
| 4th | RCX |
| 5th | R8 |
| 6th | R9 |

```ailang
// Good - 6 or fewer parameters
Function.Calculate {
    Input: a: Integer
    Input: b: Integer
    Input: c: Integer
    Input: d: Integer
    Input: e: Integer
    Input: f: Integer
    Output: Integer
    Body: { ... }
}

// Need more? Use a list:
Function.ProcessMany {
    Input: params: Address
    Output: Integer
    Body: {
        a = XArray.XGet(params, 0)
        b = XArray.XGet(params, 1)
        c = XArray.XGet(params, 2)
        // ... etc
    }
}
```

---

## Expression Nesting

### The Problem

Each nested call in an expression creates register pressure and stack usage:

```ailang
// Bad - 4 levels of nesting
result = Foo(Bar(Baz(Qux(x))))
```

This requires the compiler to:
1. Evaluate `Qux(x)`, save result
2. Evaluate `Baz(result)`, save result
3. Evaluate `Bar(result)`, save result
4. Evaluate `Foo(result)`

### The Solution: Flatten

```ailang
// Good - explicit temporaries
t0 = Qux(x)
t1 = Baz(t0)
t2 = Bar(t1)
result = Foo(t2)
```

Benefits:
- Each intermediate is inspectable
- Clearer data flow
- Maps directly to assembly
- Easier debugging

### Recommended Limits

| Metric | Limit | Reason |
|--------|-------|--------|
| Expression nesting | 2-3 levels max | Register pressure |
| Call chain depth | Keep shallow | Stack growth |
| Arguments per call | 6 max | ABI constraint |

---

## Recursion

### Safe Recursion

Bounded, shallow recursion is fine:

```ailang
Function.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock: {
            ReturnValue(1)
        }
        sub = Subtract(n, 1)
        rec = Factorial(sub)
        result = Multiply(n, rec)
        ReturnValue(result)
    }
}
```

Stack depth: `n` frames. For `n=20`, ~640 bytes of stack. Fine.

### Dangerous Recursion

Unbounded or very deep recursion will overflow the stack:

```ailang
// DANGEROUS - tree could be 100,000 levels deep
Function.ProcessTree {
    Input: node: Address
    Body: {
        left = GetLeft(node)
        right = GetRight(node)
        ProcessTree(left)   // Stack frame
        ProcessTree(right)  // Another stack frame
    }
}
```

### Convert to Iteration

For deep structures, use an explicit stack:

```ailang
SubRoutine.ProcessTreeSafe {
    stack = XArray.XCreate(1000)
    XArray.XPush(stack, root)
    
    WhileLoop GreaterThan(XArray.XSize(stack), 0) {
        size = XArray.XSize(stack)
        node = XArray.XGet(stack, Subtract(size, 1))
        XArray.XPop(stack)
        
        // Process node...
        
        // Push children
        left = GetLeft(node)
        right = GetRight(node)
        IfCondition NotEqual(left, 0) ThenBlock: {
            XArray.XPush(stack, left)
        }
        IfCondition NotEqual(right, 0) ThenBlock: {
            XArray.XPush(stack, right)
        }
    }
    
    XArray.XDestroy(stack)
}
```

---

## Stack Frame Size

Each function call consumes stack space:

| Component | Size |
|-----------|------|
| Return address | 8 bytes |
| Saved RBP | 8 bytes |
| Local variables | Varies |
| Spilled registers | 0-48 bytes |
| **Typical frame** | **32-64 bytes** |

### Calculating Stack Usage

```
Max safe recursion depth ≈ Stack size / Frame size
                        ≈ 8MB / 64 bytes
                        ≈ 125,000 calls
```

But don't push it. Keep recursive depth under 1,000 unless you know your frame size.

---

## The AIMacro Transpiler

The AIMacro transpiler automatically flattens nested expressions:

**Input (AIMacro):**
```python
result = foo(bar(x), baz(y, qux(z)))
```

**Output (AILang):**
```ailang
t0 = bar(x)
t1 = qux(z)
t2 = baz(y, t1)
result = foo(t0, t2)
```

This ensures:
- One call per line
- All intermediates named
- Clean register usage
- Debuggable output

---

## Summary

| Do | Don't |
|----|-------|
| Flatten deep expressions | Nest more than 2-3 calls |
| Use iteration for deep structures | Recurse unbounded |
| Pass max 6 parameters | Exceed ABI limits |
| Name intermediates | Hide data flow |
| Keep recursion bounded | Trust infinite stack |

**Remember:** AILang is a structured assembler. Each call is real. Each frame costs stack. Write what you mean, explicitly.