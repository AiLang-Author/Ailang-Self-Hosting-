# Library.OOP(ailang)

## NAME

`Library.OOP` — opt-in object-oriented programming for AILang

## SYNOPSIS

```ailang
LibraryImport.OOP
```

> Requires: `LibraryImport.XArrays`, `LibraryImport.TArrays`,
> `LibraryImport.HashMap` (pulled in automatically)

---

## DESCRIPTION

`Library.OOP` provides class definition, instantiation, single
inheritance, mixins, dynamic method dispatch, super calls, and
introspection — implemented entirely as a library on top of AILang
primitives. No compiler support required.

**OOP is opt-in.** Code that doesn't import this library pays none
of the overhead. Systems code, grep, the compiler — none of them
need a vtable. Import this library only when the OOP model is the
right fit for the problem.

### Object model

Every object is a `HashMap` with two keys:

```
{
  "__class__": "ClassName"       — class name string
  "__data__":  {field: value}    — instance field HashMap
}
```

Every class definition is a `HashMap` stored in the global
`ClassRegistry`:

```
{
  "name":           "ClassName"
  "parent":         "ParentName" or 0
  "fields":         {field_name: field_type}
  "methods":        {method_name: func_address}
  "field_defaults": {field_name: default_value}
}
```

Method dispatch walks the inheritance chain at call time via
`_MethodLookupWithInheritance`, resolving the function address and
invoking it with `CallIndirect`. Self (`obj`) is always the first
argument.

---

## QUICK EXAMPLE

```ailang
LibraryImport.OOP

// Define a class
OOP.ClassDefine("Animal", 0)
OOP.ClassField("Animal", "name", "string")
OOP.ClassField("Animal", "sound", "string")
OOP.ClassMethod("Animal", "speak", AddressOf(Animal_Speak))

Function.Animal_Speak {
    Input: self: Address
    Output: Integer
    Body: {
        name  = OOP.ObjectGet(self, "name")
        sound = OOP.ObjectGet(self, "sound")
        PrintMessage(name)
        PrintMessage(" says ")
        PrintMessage(sound)
        PrintMessage("\n")
        ReturnValue(0)
    }
}

// Define a subclass
OOP.ClassDefine("Dog", "Animal")
OOP.ClassField("Dog", "breed", "string")
OOP.ClassMethod("Dog", "fetch", AddressOf(Dog_Fetch))

Function.Dog_Fetch {
    Input: self: Address
    Output: Integer
    Body: {
        PrintMessage("Fetching!\n")
        ReturnValue(1)
    }
}

// Instantiate and use
SubRoutine.Main {
    dog = OOP.ObjectNew("Dog")
    OOP.ObjectSet(dog, "name",  "Rex")
    OOP.ObjectSet(dog, "sound", "Woof")
    OOP.ObjectSet(dog, "breed", "Labrador")

    args = TArray.TCreate(0)
    OOP.MethodCall(dog, "speak", args)   // Rex says Woof
    OOP.MethodCall(dog, "fetch", args)   // Fetching!

    // Inherited from Animal
    is_animal = OOP.ObjectIsInstance(dog, "Animal")  // → 1
}
RunTask(Main)
```

---

## CLASS DEFINITION

---

### `OOP.ClassDefine`

```ailang
result = OOP.ClassDefine(name, parent)
```

Define a new class. `name` is a string identifier. `parent` is the
name of the parent class, or `0` for a root class with no parent.

When a parent is specified, the parent's fields, field defaults, and
methods are copied into the new class at definition time. Subsequent
changes to the parent do not affect already-defined subclasses.

Returns `1` on success, `0` if the class already exists or the parent
is not found.

```ailang
OOP.ClassDefine("Vehicle", 0)          // root class
OOP.ClassDefine("Car", "Vehicle")      // inherits Vehicle
OOP.ClassDefine("SportsCar", "Car")    // inherits Car → Vehicle
```

---

### `OOP.ClassField`

```ailang
result = OOP.ClassField(class_name, field_name, field_type)
```

Add a field to a class. `field_type` is a descriptive string
(`"string"`, `"integer"`, `"address"`, etc.) — used for
documentation and introspection only, not enforced at runtime.
Fields default to `0` unless a default is set with
`OOP.ClassFieldDefault`.

```ailang
OOP.ClassField("Car", "make",  "string")
OOP.ClassField("Car", "model", "string")
OOP.ClassField("Car", "year",  "integer")
```

---

### `OOP.ClassFieldDefault`

```ailang
result = OOP.ClassFieldDefault(class_name, field_name, default_val)
```

Set a default value for a field. `default_val` is an `Integer` —
store string pointers or addresses here for non-integer defaults.
Applied when `OOP.ObjectNew` initializes the instance.

```ailang
OOP.ClassFieldDefault("Car", "year", 2026)
```

---

### `OOP.ClassMethod`

```ailang
result = OOP.ClassMethod(class_name, method_name, func_addr)
```

Register a method on a class. `func_addr` is the address of a
function obtained via `AddressOf`. The function must accept `self`
(an `Address`) as its first parameter, followed by any additional
arguments.

```ailang
OOP.ClassMethod("Car", "start",    AddressOf(Car_Start))
OOP.ClassMethod("Car", "describe", AddressOf(Car_Describe))
```

Method registration overwrites any inherited method of the same name,
enabling method overriding in subclasses.

---

## MIXINS

Mixins copy methods from one class into another without establishing
an inheritance relationship.

### `OOP.ClassMixin`

```ailang
result = OOP.ClassMixin(target_class, mixin_class)
```

Copy methods from `mixin_class` into `target_class`. Methods that
already exist on `target_class` are **not** overwritten — the
target's existing methods take priority.

```ailang
OOP.ClassDefine("Serializable", 0)
OOP.ClassMethod("Serializable", "to_json", AddressOf(Ser_ToJson))

OOP.ClassMixin("Car", "Serializable")   // Car gets to_json
                                         // but keeps its own methods
```

---

### `OOP.ClassMixinOverride`

```ailang
result = OOP.ClassMixinOverride(target_class, mixin_class)
```

Same as `OOP.ClassMixin` but mixin methods **overwrite** any
existing methods of the same name on the target.

---

## INSTANTIATION

---

### `OOP.ObjectNew`

```ailang
obj = OOP.ObjectNew(class_name)
```

Allocate and initialize a new instance of `class_name`. All fields
are initialized to their defaults (or `0` if no default is set).
Returns the object address, or `0` if the class is not found.

```ailang
car = OOP.ObjectNew("Car")
```

---

### `OOP.ObjectNewInit`

```ailang
obj = OOP.ObjectNewInit(class_name, init_args)
```

Allocate a new instance and call `__init__` on it if the method
exists. `init_args` is a `TArray` of arguments to pass (not
including `self`). Returns the object or `0` on failure.

```ailang
args = TArray.TCreate(2)
TArray.TPush(args, name_ptr)
TArray.TPush(args, year)
car = OOP.ObjectNewInit("Car", args)
```

---

## FIELD ACCESS

---

### `OOP.ObjectGet`

```ailang
value = OOP.ObjectGet(obj, field_name)
```

Read a field from an object. Returns the field value, or `0` if the
object is null or the field doesn't exist.

---

### `OOP.ObjectSet`

```ailang
result = OOP.ObjectSet(obj, field_name, value)
```

Write a field on an object. Returns `1` on success, `0` if the
object is null.

---

### `OOP.ObjectHasField`

```ailang
result = OOP.ObjectHasField(obj, field_name)
```

Returns `1` if the field exists on the object (even if its value is
`0`), `0` otherwise. Use this to distinguish "field is `0`" from
"field doesn't exist."

---

## METHOD DISPATCH

---

### `OOP.MethodCall`

```ailang
result = OOP.MethodCall(obj, method_name, args)
```

Call a method on an object. `args` is a `TArray` of arguments (not
including `self` — `self` is passed automatically as the first
argument). Walks the inheritance chain to find the method. Prints
an error and returns `0` if the method is not found.

Supports 0–5 arguments. For more than 5, only the first 5 are passed.

```ailang
args = TArray.TCreate(0)
OOP.MethodCall(car, "start", args)

args2 = TArray.TCreate(1)
TArray.TPush(args2, speed)
OOP.MethodCall(car, "accelerate", args2)
```

---

### `OOP.MethodExists`

```ailang
result = OOP.MethodExists(obj, method_name)
```

Returns `1` if the method exists on the object's class or any
ancestor, `0` otherwise. Use before `OOP.MethodCall` when the
method is optional.

---

### `OOP.MethodLookup`

```ailang
func_addr = OOP.MethodLookup(obj, method_name)
```

Returns the function address for a method, or `0` if not found.
Useful for caching dispatch or calling with `CallIndirect` directly.

---

## SUPER CALLS

### `OOP.SuperCall`

```ailang
result = OOP.SuperCall(obj, current_class, method_name, args)
```

Call the parent class's version of a method. `current_class` is the
class making the super call (not the object's actual class, which
may be a deeper subclass). Walks from `current_class`'s parent
upward.

```ailang
Function.SportsCar_Start {
    Input: self: Address
    Output: Integer
    Body: {
        // Call Car's start first
        args = TArray.TCreate(0)
        OOP.SuperCall(self, "SportsCar", "start", args)
        // Then do SportsCar-specific startup
        PrintMessage("Turbo engaged\n")
        ReturnValue(0)
    }
}
```

---

## INTROSPECTION

| Function | Returns |
|----------|---------|
| `OOP.ObjectClass(obj)` | Class name string of this object |
| `OOP.ObjectIsInstance(obj, class_name)` | `1` if obj is an instance of class or any subclass |
| `OOP.ClassGetFields(class_name)` | `XArray` of field name strings |
| `OOP.ClassGetMethods(class_name)` | `XArray` of method name strings |
| `OOP.ClassGetParent(class_name)` | Parent class name or `0` |
| `OOP.ClassExists(class_name)` | `1` if class is registered |

```ailang
// Walk the inheritance chain
current = OOP.ObjectClass(obj)
WhileLoop NotEqual(current, 0) {
    PrintMessage(current)
    PrintMessage("\n")
    current = OOP.ClassGetParent(current)
}
```

---

## PERFORMANCE NOTES

Every field access is a `HashMap` lookup. Every method call is a
HashMap traversal up the inheritance chain plus a `CallIndirect`.
This is appropriate for high-level modeling code — it is not
appropriate for hot paths, tight loops, or systems code.

For performance-critical objects, use `LinkagePool` instead —
field access is a single `[R15 + offset]` instruction with no
HashMap overhead. `Library.OOP` is the right choice when the OOP
model matters more than raw speed.

---

## LIMITATIONS

- **Max 5 method arguments** (plus implicit `self`). Functions with
  more than 5 parameters cannot be registered as methods.
- **No multiple inheritance** — use mixins for composing behavior
  from multiple sources.
- **No generic types** — `OOP.ObjectGet` returns `Integer`. Store
  `Address` values as integers (they fit in 64 bits).
- **No compile-time type checking** — field types are documentation
  only. Wrong-type assignments are not caught at compile time.
- **Parent changes don't propagate** — modifying a parent class
  after subclasses are defined does not update those subclasses.

---

## SEE ALSO

`Library.HashMap`,
`Library.Option`,
`LinkagePool` (Memory Management Reference Manual),
`AILang Language Introduction`

---

## VERSION

Opt-in OOP library. Implemented entirely on `HashMap` + `CallIndirect`
with no compiler support. Single inheritance, mixins, dynamic dispatch,
super calls, and full introspection.

## COPYRIGHT

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
