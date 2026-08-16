# CAD Kernel Design Specification
## AILang-Native Geometric Modeling Kernel — Core Engine

> **Readers:** This is the long kernel tome (~19k words). For **UI / IPC / host chrome / tools.json / PG catalog**, use **`CAD_UI_PLAN.md` (v3)** — ~10 min read. Do not scan this file for windowing.

**Project:** Clean-Sheet CAD Kernel
**Author:** 2 Paws Machine and Engineering
**Document version:** 3.1
**Supersedes:** v3.0 (`.cadx` native file format), v2.0 (AILang Native)
**Implementation language:** AILang
**Scope:** Core engine only. No GUI. No FFI. No C++.

> **v3.1 errata (normative):** The proprietary `.cadx` binary document format
> (`CAD.Doc`) is **abandoned**. **PostgreSQL is the system of record** for
> documents, feature trees, parameters, sessions, users, revisions, and
> cached B-rep/mesh blobs. Neutral interchange remains **STEP / STL / DXF**
> only (import/export). Kernel algorithms still run on an **in-memory arena**
> (handles + slabs); Postgres is load/store and product substrate, not a
> per-lookup geometry query engine. Pure-memory unit tests stay headless with
> no server; product/open-save paths use `CAD.Repo` + `Library.PostgreSQL_Complete`.
> See §1.3 and §7.3 `CAD.Repo`. Companion process note: `Docs/CAD/CAD_DEV_GUIDE.md`.

---

## 0. How to Read This Document

This document is written to be **executed by implementation agents working in
parallel**. It is not a vision document. Every library below has:

1. A **frozen interface** — the exact function signatures other libraries may call.
2. An **invariant set** — properties that must hold after every public call.
3. A **may-call list** — the only other libraries it is permitted to depend on.
4. **Test obligations** — what must be proven before the library is considered done.

The may-call lists are the coordination mechanism. An agent implementing
`CAD.Bool` never needs to talk to the agent implementing `CAD.Sketch`, because
the layer graph guarantees they never touch. If an implementation needs a
function not in its may-call list, that is a **design escalation**, not a
judgment call — the interface gets amended explicitly and the amendment is
recorded in §13.

**Interfaces freeze before implementation begins.** This is the single most
important process rule. Parallel agents cannot converge if the contracts move
underneath them.

---

## 1. Scope

### 1.1 In Scope

The **kernel**: everything required to take a parametric description and produce
a validated boundary representation, plus the persistence and tessellation
needed to get data in and out.

- Numeric foundation, exact geometric predicates, tolerance policy
- Curve and surface geometry, evaluation and differential properties
- Topological structure, validation, Euler operators
- Curve/curve, curve/surface, and surface/surface intersection
- Boolean operations (union, subtract, intersect)
- 2D sketch geometry and constraint solving
- Feature tree, dependency graph, regeneration, persistent naming
- Tessellation
- Native document format, STEP and STL import/export
- A headless command-line driver and test harness

### 1.2 Explicitly Out of Scope

- **All GUI.** No Qt, no QML, no OpenGL, no widget bindings, no window system.
  v2's Qt chapter is deleted, not deferred with a plan.
- **All FFI.** No C shims, no `dlopen`, no linking against C++ libraries. The
  kernel is pure AILang over Linux syscalls.
- **SQLite.** It is a C library and unreachable without FFI.
- **Proprietary native binary documents (`.cadx` / `CAD.Doc`).** Abandoned in
  v3.1. Postgres + STEP/STL/DXF replace that role. See §1.3.
- **Python (or any non-AILang) code as a kernel substitute.** Fixture generators
  and gallery scripts are not the engine. Goldens come from `cadk` / AILang
  tests once the layer is real.

### 1.3 Persistence Model — Postgres Is the System of Record

A complete pure-AILang Postgres driver already exists
(`Library.PostgreSQL_Complete`). Local or shared server is free setup: users,
sessions, ACLs, transactions, revisions, LISTEN/NOTIFY — capabilities a custom
`.cadx` file would force us to reinvent badly.

| Layer | Role | State |
|---|---|---|
| In-memory arena | Runtime geometry kernel | Fixed-stride slabs, integer handles |
| Postgres (`CAD.Repo`) | **System of record** | Parts, feature trees, params, sessions, revs, users, cached B-rep/mesh |
| Neutral files (`CAD.IO`) | Interchange only | STEP, STL, DXF (import/export edges) |

**What lives where**

1. **Performance.** Booleans and intersections never query PG per edge. Hot
   path is always the in-memory arena. Open loads a revision into slabs;
   commit writes authoritative rows + optional cache blobs.
2. **Testability.** Unit / phase gates for Num, Geom, Topo, Isect, Bool run
   headless with **no server** — synthetic solids in memory. A separate
   `repo` integration suite exercises live PG when available.
3. **Product simplicity.** PG local = single-user workstation. PG shared =
   multi-user and agents. Session management and concurrency come from the
   database, not a new file format.
4. **Interchange.** Email/git/USB portability is **STEP** (and STL/DXF), not
   a private binary. Optional later: dump/restore a project schema or
   logical PG transfer between machines.

**Schema principle (unchanged from v3, format changed).** Topology is
**derived**. Authoritative data is the feature tree, parameters, sketches, and
identity. B-rep and meshes are caches (BYTEA or large objects) with kernel
version + content hash. Do **not** reify every coedge as a permanent SQL row
for the hot path. Optionally materialize queryable param/feature tables for
PDM search — that is free relational value, not runtime topology.

**`CAD.Repo` is on the product critical path.** It is not required to unit-test
L0–L6 geometry, but open/save, sessions, and multi-user work go through it.
There is no `.cadx` fallback.

### 1.4 Part root, Sketch_0, plane recipes, and ordered trees (normative)

This section freezes the **product coordinate and dependency model**. It is why
PostgreSQL is the system of record, and why FreeCAD-style topological naming
rot is treated as a data-model problem rather than a mesh problem.

**Sketch_0 is the part root.**

- Every part has exactly one **root sketch** (`Sketch_0`). It defines the part
  origin and the home construction plane (typically world XY at `(0,0,0)`).
- Sketch geometry is always **local X/Y** on its plane (machinist Cartesian,
  ISO 841). **Z** is the plane normal / pad direction. Do **not** label sketch
  axes U/V/W in the product — those names collide with secondary linear axes
  and with A/B/C rotary convention. World XYZ is obtained only by evaluating
  `world = PlaneTransform(plane) × (x, y, 0)`.
- Camera / table rotations are **A about X, B about Y, C about Z**. Free-orbit
  drag is C (yaw about world Z) + B-like pitch. The host only sends `orbit` /
  `pan` / `zoom` / `view0`–`view7` / `iso`; `CAD.View` owns the camera.
  Sketch-on-face uses that same camera (no second view, no Gtk viewport math).
  The orientation cube is **host chrome**: it reads `cam.txt` (yaw/pitch) and
  sends those cmds. It is not part of the B-Rep / screenshot framebuffer.
- All subsequent sketches and construction planes are **relative recipes** that
  ultimately hang off Sketch_0 (or bodies/features grown from it): offset,
  angle, distance, plane-on-face-of-feature, flip normal, local ΔX/ΔY, etc.
- Reordering or orphaning the root sketch **breaks the model** in every major
  CAD system. That is not a bug to paper over. Root reorder is unsupported
  (or a deliberate break-and-rebind tool), never a silent renumber.

**Planes are recipes, not free-floating matrices.**

| Object | Role | Authoritative? |
|--------|------|----------------|
| Construction plane / plane feature | Origin ref + construction mode + modifiers (see `plane_coordinate_tree_spec.md`) | Yes (feature tree) |
| Evaluated frame (origin, X, Y, Z) | Cache for eval / sketch embed | No (derived) |
| B-Rep planar face | Topology after solid ops; may back a construction plane | Derived solid |
| Sketch | 2D entities in local X/Y of its plane handle | Yes (under its plane) |

When the user draws on a face, the system creates a **plane feature** parented to
that face (or its supporting surface / generating feature), with a known list of
offset / angle / distance parameters from the lineage rooted at Sketch_0. If a
body changes height or a parent face moves, dependent planes re-evaluate, then
sketches re-embed, then child features regenerate. Absolute vertex soup is never
the source of truth.

**Ordered tree lives in Postgres.**

- Authoritative layout is an **ordered feature/sketch DAG**: `feat_index`,
  parent links, plane recipes, parameters, sketch payloads.
- `cad_revision.feature_tree` (JSONB) and/or normalized `cad_feature` rows with
  stable order make recovery, history, multi-user checkout, and agent jobs
  boring SQL problems — not a proprietary document fight.
- In-memory arena loads a revision, regenerates derived B-Rep/mesh, and exports
  STEP/STL/DXF. Hot geometry loops never query Postgres per edge.

```
Postgres:  ordered feature DAG + params + Sketch_0 root + plane recipes
    ↓ open / commit
Memory:    eval plane frames → sketch UV → solid B-Rep (derived)
    ↓ interchange only
STEP/STL:  snapshot of derived geometry
```

**Persistent naming (TNP) policy.**

- Do **not** store “face index after last boolean” as the long-term reference.
- Prefer **provenance**: Sketch_0 → pad/extrude → end/side face of that feature;
  or construction plane with parent feature id + geometric recipe.
- `Feat_Pid` (`origin_feat`, `origin_kind`, `source_*`) resolves regen against
  that lineage. Geometric fallback is last resort and must fail loud when
  ambiguous.
- Relative coordinates from Sketch_0 collapse most TNP surface area; they do not
  remove the need for provenance on generated faces — they make that provenance
  start from a stable root instead of ephemeral B-Rep renumbering.

**Invariants (product model).**

1. Exactly one root sketch per part; it is feature index 0 in the ordered tree.
2. No feature is parentless except Sketch_0 (and optional world datums under the part).
3. Sketch plane = evaluated frame from parent recipe; sketch data is local X/Y only.
4. Tree order + parent links in Postgres are authoritative; memory mirrors them.
5. B-Rep, tessellation, and STEP/STL are caches with content hash + kernel version.
6. Changing a dimension is param edit + regenerate the DAG, not edit absolute coords.

---

## 2. Design Principles

1. **The kernel is a compiler.** Feature tree is the AST, topology is the IR,
   B-rep is the target. Passes are separable and independently testable.
2. **Derived data is never authoritative.** The feature tree is the source of
   truth. Topology, B-rep, and meshes are caches with validity bits.
3. **One tolerance authority.** Every library cites §6. No library invents its
   own epsilon. This is the difference between a kernel that works and one that
   fails mysteriously in year two.
4. **Exact where it matters.** Combinatorial decisions (which side of a plane,
   do these segments cross) use exact predicates, never floating-point
   comparison. Numeric approximation is confined to *values*, never to
   *branch conditions* that determine topology.
5. **Handles, not pointers.** All entities are referenced by opaque 64-bit
   handles with generation counters. Dangling references are detectable, not
   undefined.
6. **Headless and scriptable.** Everything the kernel does is reachable from a
   CLI with file in / file out. This is what makes agent-driven development and
   fuzzing possible.
7. **Deterministic.** Same input, same build, bit-identical output. No
   iteration-order dependence on pointer values, no unseeded randomness.
8. **OpenCascade is a reference and an oracle, never a dependency.**

---

## 3. AILang Constraints That Shape the Design

These are properties of the language, taken from the reference manuals. They are
not preferences — code that violates them does not work. Every one of them has a
structural consequence.

| Constraint | Source | Consequence for this design |
|---|---|---|
| Max 6 register parameters (RDI, RSI, RDX, RCX, R8, R9) | Function Calls guide | No function takes loose coordinate triples. Vectors and points are passed as `Address` to a `LinkagePool`. See §4.3. |
| Expression nesting 2–3 levels max | Function Calls guide | Mandatory flat SSA style. One call per line, every intermediate named. §5.1. |
| `Deallocate` size must exactly match `Allocate` | Memory manual | No per-entity allocation. One slab per entity type, fixed stride, index handles, never individually freed. §4.2. |
| No exceptions; errors are return values | Intro | Uniform status-code protocol. §4.4. |
| `FixedPool` = `MOV RAX, [R15+off]`, single instruction | Memory manual | Hot-path globals (tolerance context, error state, slab bases) live in `FixedPool`. |
| `FixedPool` capped at 131,072 vars | Memory manual | Entity storage never uses `FixedPool`. Slabs only. |
| **R15 is reserved** | Memory manual | Never touched, including inside the sanctioned inline-asm blocks of §5.6. |
| Inline assembly is supported | Language | Permitted at exactly one site: the exact-predicate kernels. See §5.6 and §6.5. |
| `LinkagePool` with `@` access, `PointerTo=` type propagation | LinkagePool manual | The structural primitive for `Vec3`, `Coedge`, `Curve`, `Surface`. Compile-time field validation is exactly what topology traversal needs. |
| Built-in arrays: fixed size, **no bounds checking** | Array manual | Every slab access goes through a checked accessor in `CAD.Store`. Raw `ArrayGet`/`ArraySet` is banned outside `CAD.Store`. |
| `Arrays` dynamic, auto-resizing | Array manual | Used for transient result sets (intersection curve lists, candidate face sets). |
| `DebugAssert` + `-D` levels | Debug manual | Invariant checks compile out of release builds. The tier-1 test strategy in §10 is built on this. |
| No native `BreakLoop` in current build (flag workaround documented) | Flow Control manual | Loop-exit flag idiom is standard style. §5.1. |
| Recursion is real stack; deep recursion overflows | Function Calls guide | All traversals (topology walks, tree regeneration, BVH descent) use explicit `Arrays` stacks. No recursive traversal anywhere in the kernel. |
| `ReadTextFile` / `GetFileSize` are **not implemented** | File I/O manual | `CAD.Sys` must implement file reading over raw syscalls. This is Phase 0 and blocks all import and document loading. §7.1. |

### 3.1 Floating Point — Resolved

Both open questions from earlier drafts are answered by the FPU compiler
backend (`Library.FPUCompileX86SSE`, `FPUCompileX86AVX`,
`FPUCompileX86Trans`, `FPUTypes`). The answers are favorable, with one
significant footgun.

**Representation.** `FPUSize.FLOAT = 8` — 64-bit IEEE-754 doubles. Values are
stored and passed as **raw 64-bit bit patterns in general-purpose registers**
(arriving in RAX), moved into XMM via `MOVQ` for computation with SSE2/AVX
scalar-double instructions, and moved back to RAX as the result.

**Q1 — parameter registers: resolved, no boxing needed.** Because floats travel
as bit patterns in the *integer* register file, they consume the same six
argument slots as everything else. There is no separate XMM argument budget.
Every signature in §7.3 was audited against this: the widest are five arguments
(`Topo_MakeEdge`, `Num_InSphere`, `Sketch_AddConstraint`,
`Geom_MakeNurbsSrf`). **No signature requires a boxed parameter struct.** The
`[Q1]` markers are removed.

**Q2 — transcendentals: resolved, all present.** The full set is available as
compiler primitives:

| Category | Available |
|---|---|
| Arithmetic | `Float_Add`, `Float_Sub`, `Float_Mul`, `Float_Div`, `Float_Min`, `Float_Max`, `Float_Sqrt` |
| Transcendental | `Float_Sin`, `Float_Cos`, `Float_Tan`, `Float_Atan2`, `Float_Exp`, `Float_Log`, `Float_Pow` |
| FMA / extended | `Float_FMA`, `Float_FMS`, `Float_FNMA`, `Float_DotPD` |
| Rounding / conversion | `Float_Floor`, `Float_Ceil`, `Float_Trunc`, `Float_Round`, `Float_FromInt`, `Float_ToInt` |
| Comparison | `Float_Eq`, `Float_Ne`, `Float_Lt`, `Float_Gt`, `Float_Le`, `Float_Ge` |

`Float_Sqrt` (SQRTSD) and `Float_Atan2` (with quadrant tracking) are exactly
what §9's dependency table needed. **No CORDIC section is required**;
`CAD.Num` does not grow. `Library.FixedPointTrig` exists as an alternative and
is not used by this kernel.

`Float_FMA` is the consequential one: it makes exact-predicate arithmetic writable
in plain AILang with no assembly (§5.6, §6.5).

### 3.2 `Real` Is Not a Type — Read This Before Writing Any Geometry Code

AILang's type system remains `Integer` and `Address`. **There is no distinct
float type.** A double is an `Integer` whose 64 bits happen to be an IEEE-754
bit pattern, and float operations are ordinary named functions
(`Float_Add`, `Float_Mul`, …) rather than overloads of `Add` and `Multiply`.

Throughout this document, `Real` is a **documentation alias** meaning "an
`Integer` holding an f64 bit pattern." It signals intent to the reader and to
implementing agents. It is not enforced by the compiler.

This produces the single most dangerous failure mode in the entire project:

```ailang
// CATASTROPHIC — integer-adds two IEEE-754 bit patterns.
// Compiles clean. Runs. Produces garbage that is *sometimes* plausible.
sum = Add(x, y)

// CORRECT
sum = Float_Add(x, y)
```

There is no type error, no crash, and no assertion. The result is a nonsense
double that may be finite, may be the right order of magnitude, and will produce
geometry that is subtly wrong rather than obviously broken. In a kernel where
correctness is judged by tolerances, this is the worst possible class of bug.

**Countermeasures, all mandatory:**

1. **Naming discipline.** Any variable holding a `Real` is suffixed `_r`, or
   is a field of a `LinkagePool` whose contract documents it as `Real`. A bare
   integer name never holds a float.
2. **Automated audit (§12.4).** The integer-op audit flags the integer
   arithmetic and comparison operators — `Add`, `Subtract`, `Multiply`,
   `Divide`, `Modulo`, `Power`, `Abs`, `Min`, `Max`, `ISqrt`, `LessThan`,
   `GreaterThan`, `EqualTo`, and their infix forms `+ - * / ^ < > ==` — applied
   to any `_r`-suffixed variable, any expression sourced from a `Float_*` call,
   or any field documented as `Real`. Since infix and named forms are the same
   operation, the audit treats them identically. This is the highest-priority
   audit in the project.
3. **Golden-value tests.** Every `CAD.Num` function has at least one test with
   a hard-coded expected bit pattern, generated offline. Integer-op
   contamination changes those bits immediately.
4. **Infix is integer arithmetic — use it freely, but know its scope.** Infix
   is fully supported and compiles to identical code as the named form, so
   `(a + b)` *is* `Add(a, b)`. Because AILang deliberately has no operator
   overloading, there is no float infix and never will be. Use infix
   throughout for indices, offsets, counters, handle arithmetic, and loop
   bounds — that is most of the kernel's line count and it reads better for
   it. Float arithmetic uses the explicit `Float_*` call form. The two never
   mix in one expression.

```ailang
// Integer arithmetic — infix, natural
offset = ((i * 8) + base)
IfCondition ((idx >= 0) && (idx < count)) ThenBlock: { ... }

// Float arithmetic — explicit calls
t0_r = Float_Mul(dx_r, dx_r)
t1_r = Float_FMA(dy_r, dy_r, t0_r)
d2_r = Float_FMA(dz_r, dz_r, t1_r)
```

5. **`^` is Power, not XOR.** This bites twice in this kernel specifically: the
   xorshift64* PRNG (§7.3 `CAD.Num`) and the spatial hash used for vertex
   merging (§6.6) are both built on XOR. Both must use `BitwiseXor(a, b)` —
   there is no infix form, and `(a ^ b)` silently computes exponentiation
   instead. A PRNG built with `^` will produce a plausible-looking but wrong
   sequence, which would make every fuzz result irreproducible in a way that is
   very hard to trace.

**Ergonomic consequence.** Float-heavy code is verbose. A Vec3 dot product is
one multiply plus two `Float_FMA` calls, written as three named lines. This is
the cost of no-overloading, and it buys something real: every float operation is
greppable, and there is never a question of what an operator means for a given
operand type.

Two mitigations. First, `CAD.Num` exposes fused helpers generously
(`Num_V3Dot`, `Num_V3Cross`, `Num_V3Madd`, `Num_V3Lerp`), so layers above L0
rarely write raw `Float_*` chains at all — the verbosity is concentrated in one
library that is written once and tested hard. Second, prefer `Float_FMA`
wherever the algebra allows: it is faster, more accurate than separate
multiply-then-add, and shortens the code.

---

## 4. Universal Conventions

Every library obeys these. They are not negotiable per-library.

### 4.1 Naming

```
Function.<Lib>_<Verb><Noun>      public API      e.g. Function.Topo_MakeFace
Function.<Lib>__<name>           private         e.g. Function.Bool__classifyLoop
SubRoutine.<Lib>_<Name>          void operations
FixedPool.<Lib>_State            per-library global state
LinkagePool.<Lib>_<Type>         structured records
```

Double underscore marks a private function. Private functions are called only
from within their own library. This is a convention the compiler does not
enforce — it is enforced by review and by the `may-call` audit script (§12.4).

File layout:

```
cad/
  src/
    sys/      CAD.Sys      syscall wrappers, file I/O, timing
    num/      CAD.Num      arithmetic, vectors, matrices, predicates, tolerance
    store/    CAD.Store    slab allocator, handle tables
    geom/     CAD.Geom     curves and surfaces
    topo/     CAD.Topo     radial-edge topology
    isect/    CAD.Isect    intersection
    bool/     CAD.Bool     boolean operations
    sketch/   CAD.Sketch   2D geometry and constraint solver
    feat/     CAD.Feat     feature tree, regeneration, persistent naming
    tess/     CAD.Tess     tessellation
    io/       CAD.IO       STEP, STL, DXF interchange only
    repo/     CAD.Repo     Postgres system of record (product path)
    cli/      cadk         command-line driver
  test/
    unit/         per-library unit tests
    invariant/    property-based invariant tests
    golden/       golden corpus + expected checksums
    fuzz/         adversarial generators
    oracle/       OCCT-generated reference fixtures
  contracts/      frozen interface files, one per library
  docs/
```

### 4.2 Handles

Every entity is a 64-bit handle. Never a raw pointer in any public interface.

```
bit 63..56   type tag        (8 bits, see table)
bit 55..40   generation      (16 bits, wraps)
bit 39..0    slab index      (40 bits, ~1.1e12 entities)
```

Handle `0` is always invalid and is the universal "none" value. Index 0 of every
slab is reserved and never allocated, so a zeroed field reads as a null handle.

The generation counter increments when a slot is recycled. `Store_IsLive(h)`
compares the handle's generation against the slot's. A stale handle is therefore
**detected**, not silently followed into recycled memory. This is worth the 16
bits many times over during boolean debugging.

| Tag | Type | Slab |
|---|---|---|
| 0x01 | Vertex | topo |
| 0x02 | Edge | topo |
| 0x03 | Coedge | topo |
| 0x04 | Loop | topo |
| 0x05 | Face | topo |
| 0x06 | Shell | topo |
| 0x07 | Solid | topo |
| 0x10 | Curve | geom |
| 0x11 | Surface | geom |
| 0x12 | PCurve | geom |
| 0x20 | SketchPoint | sketch |
| 0x21 | SketchCurve | sketch |
| 0x22 | Constraint | sketch |
| 0x30 | Feature | feat |
| 0x31 | Parameter | feat |
| 0x40 | Mesh | tess |
| 0x50 | Document | doc |

Type tags are checked on every public entry point under `-D1`. Passing a Face
handle where an Edge is expected is caught immediately rather than producing
garbage 200 calls later.

### 4.3 Value Types

Small numeric aggregates are `LinkagePool` records passed by `Address`. They are
allocated from a caller-provided scratch arena, never individually heap-freed.

```ailang
LinkagePool.Num_Vec3 {
    "x": Initialize=0
    "y": Initialize=0
    "z": Initialize=0
}

LinkagePool.Num_Vec2 {
    "u": Initialize=0
    "v": Initialize=0
}

// Surface evaluation result: position, first and second derivatives, normal.
LinkagePool.Geom_SurfEval {
    "p":    Type=LinkagePool.Num_Vec3     // position
    "du":   Type=LinkagePool.Num_Vec3     // dP/du
    "dv":   Type=LinkagePool.Num_Vec3     // dP/dv
    "duu":  Type=LinkagePool.Num_Vec3
    "duv":  Type=LinkagePool.Num_Vec3
    "dvv":  Type=LinkagePool.Num_Vec3
    "n":    Type=LinkagePool.Num_Vec3     // unit normal
    "valid": Initialize=0                 // 0 = degenerate (n undefined)
}
```

**Out-parameter convention:** functions that produce an aggregate take a
caller-allocated destination as the last argument and return a status code.
This keeps every signature within the 6-register budget and makes allocation
the caller's problem, which is where it belongs.

```ailang
// Correct
Function.Geom_EvalSurface {
    Input: surf: Integer, u: Real, v: Real, out: Address
    Output: Integer      // status
}

// Wrong — returns an allocation the caller must remember to free
Function.Geom_EvalSurface {
    Input: surf: Integer, u: Real, v: Real
    Output: Address
}
```

### 4.4 Status Codes and Error Reporting

Every fallible function returns `Integer`. `0` is success. Negative values are
errors. Functions that naturally return a handle return `0` on failure (the
invalid handle) and set error state.

```ailang
FixedPool.CAD_Err {
    "code":     Initialize=0     // last error code
    "detail":   Initialize=0     // library-specific sub-code
    "entity_a": Initialize=0     // implicated handle, if any
    "entity_b": Initialize=0
    "site":     Initialize=0     // static string address: function name
}
```

| Code | Name | Meaning |
|---|---|---|
| 0 | `CAD_OK` | Success |
| -1 | `CAD_E_NULL` | Null or invalid handle |
| -2 | `CAD_E_TYPE` | Handle type tag mismatch |
| -3 | `CAD_E_STALE` | Handle generation mismatch (use-after-free) |
| -4 | `CAD_E_RANGE` | Index or parameter out of range |
| -5 | `CAD_E_ALLOC` | Slab exhausted or allocation failed |
| -6 | `CAD_E_DEGENERATE` | Degenerate geometry (zero-length, zero-area, cusp) |
| -7 | `CAD_E_NOCONVERGE` | Iterative solver failed to converge |
| -8 | `CAD_E_TOLERANCE` | Result not representable within tolerance |
| -9 | `CAD_E_NONMANIFOLD` | Non-manifold configuration where manifold required |
| -10 | `CAD_E_UNCLOSED` | Shell failed to close during stitching |
| -11 | `CAD_E_SELFINT` | Self-intersecting input |
| -12 | `CAD_E_OVERCONSTRAINED` | Constraint system over-determined |
| -13 | `CAD_E_UNDERCONSTRAINED` | Under-determined where full constraint required |
| -14 | `CAD_E_CYCLE` | Dependency cycle in feature graph |
| -15 | `CAD_E_UNRESOLVED` | Persistent name could not be resolved on rebuild |
| -16 | `CAD_E_IO` | File or syscall error |
| -17 | `CAD_E_FORMAT` | Malformed input file |
| -18 | `CAD_E_UNSUPPORTED` | Valid but unimplemented case |
| -19 | `CAD_E_INTERNAL` | Invariant violation — a bug, not bad input |

`CAD_E_INTERNAL` is distinct on purpose. It means the kernel broke its own
contract, and in fuzz runs it is a hard failure even when other errors are
acceptable outcomes.

**Propagation rule:** a caller checks and returns early. Error state is set at
the deepest site and never overwritten by intermediate frames.

```ailang
st = Isect_SurfaceSurface(sa, sb, curves)
IfCondition NotEqual(st, 0) ThenBlock: {
    ReturnValue(st)
}
```

### 4.5 Units

The kernel is unit-agnostic and stores all lengths in **millimeters** and all
angles in **radians**. Unit presentation is a UI concern and does not exist in
the kernel. Document metadata records a display unit; nothing in the kernel
reads it.

---

## 5. Coding Standard

Mandatory. The audit script in §12.4 checks the mechanical parts.

### 5.1 Flat Expressions

AILang's 2–3 level nesting limit is a register-pressure constraint, not a style
preference. Write SSA-flat code with named intermediates.

```ailang
// BANNED
d = Sqrt(Add(Add(Multiply(dx,dx), Multiply(dy,dy)), Multiply(dz,dz)))

// REQUIRED
xx = Multiply(dx, dx)
yy = Multiply(dy, dy)
zz = Multiply(dz, dz)
s1 = Add(xx, yy)
s2 = Add(s1, zz)
d  = Sqrt(s2)
```

This is verbose and it is correct. It also happens to be the form that is
easiest to review, easiest to step through, and most reliably generated by
implementation agents.

Loop exit uses the flag idiom, since `BreakLoop` is unavailable in the current
build:

```ailang
i = 0
running = 1
WhileLoop And(LessThan(i, n), running) {
    // ...
    IfCondition found ThenBlock: { running = 0 }
    i = Add(i, 1)
}
```

### 5.2 No Recursion in Traversals

Every topology walk, tree descent, and flood fill uses an explicit `Arrays`
stack. A model with 200,000 faces will blow an 8 MB stack through recursive
traversal, and it will do it in the field, not in testing.

### 5.3 Every Public Function Validates

Under `-D1`, every public entry point asserts handle validity and type tag
before touching anything:

```ailang
Function.Topo_FaceSurface {
    Input: face: Integer
    Output: Integer
    Body: {
        DebugAssert(Store_IsLive(face), "Topo_FaceSurface: dead handle")
        DebugAssert(EqualTo(Store_Tag(face), 5), "Topo_FaceSurface: not a face")
        // ...
    }
}
```

### 5.4 No Bare Array Access Outside CAD.Store

`ArrayGet` and `ArraySet` have no bounds checking. They appear only inside
`CAD.Store`, behind checked accessors. Any other occurrence is a review failure.

### 5.5 No Magic Numbers

Tolerances come from the tolerance context (§6). Type tags, status codes, and
enumerations come from `FixedPool` constants. A bare numeric literal in
geometric code is a review failure, with the sole exception of `0`, `1`, `2`,
and small loop bounds.

---

### 5.6 Inline Assembly Policy

AILang supports inline assembly in two forms — mnemonic
(`InlineAsm["POPCNT rax, rax"]`) and raw hex — with <cite index="40-1">the full x86-64 ISA available, 10,363 forms including SSE, AVX, and AVX-512</cite>. Expression form
captures RAX after execution; statement form does not.

**The default answer for this kernel is: don't.** The case that seemed to
require it no longer does.

Exact predicates need an exact two-product, which is classically written with
Dekker/Veltkamp splitting or an FMA instruction. `Float_FMA` is already a
compiler primitive (§3.1). Shewchuk-style expansion arithmetic is therefore
writable entirely in ordinary AILang, at full speed, with no assembly at all.
That was the one place where asm looked mandatory, and it isn't.

Note also that `ISqrt` is <cite index="41-1">already implemented with inline assembly inside the compiler</cite> — the language ships the
low-level work already done where it matters.

**If assembly is used anyway**, these rules apply. The register-allocator
caveat is the dangerous one: <cite index="40-1">InlineAsm does not participate in AILang's register allocator, so it is the programmer's responsibility not to clobber registers the compiler is using</cite>.

1. Confined to `src/num/predicates.ailang` and `src/num/expansion.ailang`.
   No other file in the kernel contains assembly.
2. Never writes R15 (pool table base) or R14 (reserved). Corrupting R15 breaks
   every `FixedPool` access in the program, which will not present as a
   geometry bug and will cost days to find.
3. Every register touched beyond RAX is saved and restored with a PUSH/POP pair
   in the same block. <cite index="40-1">PUSH/POP pairs are the documented-safe idiom for temporary register use</cite>.
4. Every asm block has a pure-AILang reference implementation beside it,
   compiled under a build flag, and a test asserting bit-for-bit agreement
   across the full corpus. **The reference implementation is the specification;
   the assembly is an optimization.** If they disagree, the assembly is wrong.
5. Mnemonic form only — never raw hex. Hex bytes are unreviewable.
6. AVX-512 and BMI2 paths are CPUID-detected at runtime with an SSE2 fallback,
   or gated at build time. No silent illegal-instruction failures.
7. Every block carries a comment stating its clobbers and its exact
   mathematical contract.

Rule 4 is the load-bearing one. Assembly in a geometry kernel is defensible only
when equivalence to something readable is mechanically checked on every run.

Candidate uses, in descending order of justification, all of them optional:

| Use | Instruction | Verdict |
|---|---|---|
| Exact 128-bit integer product | `MUL r64` → RDX:RAX | Only if integer-lattice predicates are added later |
| Exact two-product for f64 | — | **Unnecessary** — `Float_FMA` is a primitive |
| Vec3 SIMD batch operations | `VMULPD`, `VFMADD231PD` | Defer. Profile first; the allocator boundary costs may exceed the gain |
| Population count for spatial hashing | `POPCNT` | Marginal |

---

## 6. Tolerance Policy — Normative

**This section is the single authority on tolerance for the entire kernel.
Every library cites it. No library defines its own epsilon.**

Nearly every hard bug in a geometric kernel is a tolerance bug. The usual cause
is not a wrong value; it is *many different* values, each locally reasonable,
scattered across a codebase. Ten agents will otherwise invent ten incompatible
notions of "equal."

### 6.1 The Core Rule

> **Exact predicates decide topology. Approximate arithmetic computes values.**

A floating-point comparison must never determine a combinatorial outcome — which
side of a plane a point lies on, whether two segments cross, whether a loop is
inside another. Those go through the exact predicates in §6.5. Approximation is
confined to positions, parameters, and derivatives.

This single discipline eliminates the failure mode where a kernel makes two
*mutually contradictory* decisions about the same configuration — a point judged
inside by one test and outside by another — which is what produces unclosed
shells and inverted volumes.

### 6.2 The Tolerance Context

```ailang
FixedPool.Num_Tol {
    "linear":      Initialize=0    // default 1e-7 mm
    "angular":     Initialize=0    // default 1e-9 rad
    "param":       Initialize=0    // default 1e-9 (normalized param space)
    "model_size":  Initialize=0    // diagonal of model bounding box, mm
    "resolution":  Initialize=0    // linear * relative scale factor
}
```

- `linear` — **absolute** distance below which two positions are the same point.
  Default 1e-7 mm (0.1 nm). Chosen because f64 gives ~15–16 significant digits;
  on a 1000 mm part, 1e-7 mm leaves roughly six digits of headroom above the
  representable floor. Tightening this without widening the numeric type
  produces false coincidences, not more accuracy.
- `angular` — absolute angle below which two directions are parallel.
- `param` — tolerance in *normalized* parameter space. Curves and surfaces are
  parameterized to [0,1] at the interface boundary precisely so that one
  parametric tolerance is meaningful across all geometry types.
- `resolution` — `linear` scaled by model size, for tests that must be
  scale-relative. Computed once per document load and after any operation that
  changes the bounding box by more than 2×.

### 6.3 Per-Entity Tolerance

Vertices, edges, and faces each carry their own tolerance, initialized to
`Num_Tol.linear` and **widened — never narrowed** — by operations that introduce
uncertainty.

This is the mechanism that makes booleans survivable. When a surface/surface
intersection produces a curve accurate only to 1e-5 mm because the surfaces meet
at a shallow angle, the resulting edge records that fact. Every downstream
query on that edge uses the widened value. The alternative — pretending global
tolerance holds everywhere — is precisely how kernels produce shells that "look
closed" and fail to stitch.

**Widening rule:** when entity B is derived from entities A₁…Aₙ,

```
tol(B) = max(tol(A₁), …, tol(Aₙ), numeric_error_estimate_of_operation)
```

Tolerance is monotone non-decreasing through a modeling session. A "healing"
pass may recompute it downward, but only by re-deriving the entity from scratch.

### 6.4 Comparison Vocabulary

The **only** approved forms. Every library uses these names and no others.

```ailang
Function.Num_IsZero      { Input: a: Real Output: Integer }
Function.Num_IsEqual     { Input: a: Real, b: Real Output: Integer }
Function.Num_PointsEqual { Input: pa: Address, pb: Address, tol: Real Output: Integer }
Function.Num_DirsParallel{ Input: da: Address, db: Address Output: Integer }  // ± both
Function.Num_DirsSame    { Input: da: Address, db: Address Output: Integer }  // + only
Function.Num_ParamEqual  { Input: a: Real, b: Real Output: Integer }
```

Anything else — a bare `Num_IsEqual(Subtract(a,b), 0)`, a hand-rolled
`LessThan(Abs(d), 1e-9)` — is a review failure.

### 6.5 Exact Predicates

Adaptive-precision predicates after Shewchuk. Each returns an exact sign
(`-1`, `0`, `+1`) with no tolerance parameter. They begin with a fast
floating-point filter and escalate to exact arithmetic only when the filter's
error bound cannot certify the sign, so the common case is nearly free.

```ailang
Function.Num_Orient2D { Input: a: Address, b: Address, c: Address Output: Integer }
Function.Num_Orient3D { Input: a: Address, b: Address, c: Address, d: Address Output: Integer }
Function.Num_InCircle { Input: a: Address, b: Address, c: Address, d: Address Output: Integer }
Function.Num_InSphere { Input: a: Address, b: Address, c: Address, d: Address, e: Address Output: Integer }
```

`Orient3D` and `InSphere` take five points; both fit the 6-register budget.

**Where they are mandatory:**
- Point-in-loop and point-in-solid classification (`CAD.Bool`)
- Segment crossing tests in the constraint solver and in tessellation
- Delaunay in-circle tests (`CAD.Tess`)
- Face orientation and shell closure validation (`CAD.Topo`)
- Convex hull and BVH split-plane decisions

Exact predicates require wider-than-f64 intermediates, obtained through
Shewchuk-style floating-point expansions. The core operation is an exact
two-product — recovering the rounding error of a multiply — and `Float_FMA` is
a compiler primitive, so `Num_ExpansionMul` and friends are written in plain
AILang with no assembly and no Dekker/Veltkamp splitting. Expect roughly
400–700 lines for the expansion layer.

`Float_FMA(a, b, c)` computes `a*b + c` with a single rounding; the exact
product error is `Float_FMA(a, b, Float_Neg(Float_Mul(a, b)))`. That two-line
identity is the entire foundation of the adaptive-precision escalation path.

The predicates are among the most testable code in the project: verify against
arbitrary-precision reference values generated offline, on inputs constructed to
be degenerate to within 1 ulp.

### 6.6 Vertex Snapping

After any operation that creates vertices, `Topo_MergeVertices` snaps vertices
within combined tolerance. Merging is done by **union-find over an exact spatial
hash**, never by pairwise floating-point comparison, so the result is
independent of processing order.

Order-dependent merging is a classic source of non-determinism: A merges with B,
B with C, but not A with C, and the outcome depends on which pair was examined
first. Union-find makes the relation transitive by construction.

---

## 7. Layer Architecture

### 7.1 The Layer Graph

Strictly acyclic. Each layer may call only downward, and only into the layers
listed. This graph *is* the parallelization plan.

```
                        ┌──────────────────┐
                        │   cadk (CLI)     │   L8
                        └────────┬─────────┘
                                 │
        ┌────────────────┬───────┴────────┬─────────────────┐
        ▼                ▼                ▼                 ▼
  ┌──────────┐     ┌──────────┐                     ┌──────────┐
  │ CAD.IO   │     │ CAD.Repo │                     │ CAD.Tess │   L7
  │STEP/STL/ │     │ Postgres │                     │          │
  │  DXF     │     │   SoR    │                     │          │
  └────┬─────┘     └────┬─────┘                     └────┬─────┘
       └────────────────┴───────┬────────────────────────┘
                                ▼
                        ┌──────────────┐
                        │  CAD.Feat    │  L6
                        └──────┬───────┘
                  ┌────────────┴────────────┐
                  ▼                         ▼
          ┌──────────────┐          ┌──────────────┐
          │ CAD.Sketch   │  L5      │  CAD.Bool    │  L4
          └──────┬───────┘          └──────┬───────┘
                 │                         ▼
                 │                  ┌──────────────┐
                 │                  │  CAD.Isect   │  L3
                 │                  └──────┬───────┘
                 │                         ▼
                 │                  ┌──────────────┐
                 │                  │  CAD.Topo    │  L2
                 │                  └──────┬───────┘
                 └───────────┬─────────────┘
                             ▼
                     ┌──────────────┐
                     │  CAD.Geom    │  L1
                     │ + CAD.BSpline│
                     └──────┬───────┘
                            ▼
                     ┌──────────────┐
                     │  CAD.Store   │  L0.5
                     └──────┬───────┘
                            ▼
              ┌─────────────┴─────────────┐
              ▼                           ▼
       ┌─────────────┐            ┌─────────────┐
       │  CAD.Num    │            │  CAD.Sys    │   L0
       └─────────────┘            └─────────────┘
```

**Parallel tracks.** After L0–L1 land, three tracks proceed independently:

| Track | Libraries | Depends on | Notes |
|---|---|---|---|
| A — Solids | Topo → Isect → Bool | Geom | The long pole. Start first. |
| B — Sketch | Sketch | Geom, Num | Fully independent of A. |
| C — Output | Tess, IO, Repo | Topo (Tess), Store + PG (Repo) | Tess needs Topo; Repo schema can start early; IO is interchange only. |

`CAD.Feat` integrates A and B and starts once both have a working slice.

### 7.2 Size Estimates

Revised from v2. Increases are concentrated where v2 underestimated:
intersection is split out of Boolean and is larger than the Boolean logic
itself; the numeric foundation did not exist in v2 at all.

| Library | Lines | Notes |
|---|---|---|
| CAD.Sys | 600–900 | Syscalls, file read/write, mmap, timing |
| CAD.Num | 3,000–4,500 | Vec/mat, exact predicates, expansions, tolerance |
| CAD.Store | 800–1,200 | Slabs, handles, generations, scratch arenas |
| CAD.Geom | 4,000–6,000 | Analytic + NURBS curves and surfaces |
| CAD.Topo | 3,000–4,500 | Radial edge, Euler ops, validation |
| CAD.Isect | 6,000–9,000 | **The real hard part** |
| CAD.Bool | 4,000–6,000 | Split, classify, stitch |
| CAD.Sketch | 3,000–4,500 | Solver ~1,200 of that |
| CAD.Feat | 3,000–4,500 | Regeneration + persistent naming |
| CAD.Tess | 2,000–3,000 | Delaunay + adaptive refinement |
| CAD.IO | 4,000–7,000 | STEP is most of this; no proprietary container |
| CAD.Repo | 2,000–4,000 | Postgres SoR: schema, sessions, rev I/O |
| cadk | 800–1,200 | CLI driver (memory + repo + interchange) |
| test harness | 3,000–5,000 | Framework, generators, oracle comparison |
| **Total** | **~40,000–62,000** | vs. v2's 22–35k estimate; no CAD.Doc |

The v2 estimate was low mainly because it had no numeric layer, folded
intersection into Boolean, and had no test infrastructure line item. Against
2M lines of OpenCascade the ratio is still ~40:1.

---

### 7.3 Library Contracts

Each subsection is the frozen interface. All signatures are final with respect to
the language questions of §3.1, which are resolved.

---

#### CAD.Sys — L0

**May call:** nothing (syscalls only)
**Purpose:** Everything the kernel needs from the OS. Exists because
`ReadTextFile` and `GetFileSize` are unimplemented in the current build.

```ailang
// File I/O over raw syscalls (open=2, read=0, write=1, close=3, lseek=8, fstat=5)
Function.Sys_Open       { Input: path: Address, mode: Integer Output: Integer }  // fd or -1
Function.Sys_Close      { Input: fd: Integer Output: Integer }
Function.Sys_Read       { Input: fd: Integer, buf: Address, n: Integer Output: Integer }
Function.Sys_Write      { Input: fd: Integer, buf: Address, n: Integer Output: Integer }
Function.Sys_Seek       { Input: fd: Integer, off: Integer, whence: Integer Output: Integer }
Function.Sys_FileSize   { Input: path: Address Output: Integer }
Function.Sys_ReadAll    { Input: path: Address, out_len: Address Output: Address }  // whole file, arena
Function.Sys_WriteAll   { Input: path: Address, buf: Address, n: Integer Output: Integer }
Function.Sys_Mmap       { Input: path: Address, out_len: Address Output: Address }  // read-only map
Function.Sys_Munmap     { Input: addr: Address, len: Integer Output: Integer }

// Timing (clock_gettime=228) — for benchmarks and deterministic seeding
Function.Sys_NanoTime   { Output: Integer }

// Argv access for the CLI
Function.Sys_ArgCount   { Output: Integer }
Function.Sys_ArgAt      { Input: i: Integer Output: Address }
```

**Invariants:** every fd opened is closed on every path including error paths.
`Sys_ReadAll` returns arena memory; caller does not free.

**Tests:** round-trip write/read of 0, 1, 4095, 4096, 4097, and 10 MB byte
buffers; read of nonexistent file returns `-1` without crashing; mmap of a file
larger than available RAM succeeds.

---

#### CAD.Num — L0

**May call:** CAD.Sys
**Purpose:** All arithmetic above language primitives. Owns tolerance.

```ailang
// --- Vector (Vec3 by Address) ---
SubRoutine.Num_V3Set      { Input: v: Address, x: Real, y: Real, z: Real }
SubRoutine.Num_V3Copy     { Input: dst: Address, src: Address }
SubRoutine.Num_V3Add      { Input: dst: Address, a: Address, b: Address }
SubRoutine.Num_V3Sub      { Input: dst: Address, a: Address, b: Address }
SubRoutine.Num_V3Scale    { Input: dst: Address, a: Address, s: Real }
SubRoutine.Num_V3Cross    { Input: dst: Address, a: Address, b: Address }
Function.Num_V3Dot        { Input: a: Address, b: Address Output: Real }
Function.Num_V3Len        { Input: a: Address Output: Real }
Function.Num_V3LenSq      { Input: a: Address Output: Real }
Function.Num_V3Dist       { Input: a: Address, b: Address Output: Real }
Function.Num_V3Normalize  { Input: dst: Address, a: Address Output: Integer }  // E_DEGENERATE if zero
Function.Num_V3PerpAny    { Input: dst: Address, a: Address Output: Integer }  // any unit perp

// --- Transform: 4x3 affine (rotation 3x3 + translation), 12 Reals ---
SubRoutine.Num_XfIdentity { Input: m: Address }
SubRoutine.Num_XfMul      { Input: dst: Address, a: Address, b: Address }
SubRoutine.Num_XfApplyPt  { Input: dst: Address, m: Address, p: Address }
SubRoutine.Num_XfApplyDir { Input: dst: Address, m: Address, d: Address }
Function.Num_XfInvert     { Input: dst: Address, m: Address Output: Integer }
Function.Num_XfIsRigid    { Input: m: Address Output: Integer }

// --- Dense linear algebra (constraint solver, surface fitting) ---
Function.Num_MatCreate    { Input: rows: Integer, cols: Integer Output: Address }
SubRoutine.Num_MatDestroy { Input: m: Address }
Function.Num_MatGet       { Input: m: Address, r: Integer, c: Integer Output: Real }
SubRoutine.Num_MatSet     { Input: m: Address, r: Integer, c: Integer, v: Real }
Function.Num_MatLUSolve   { Input: a: Address, b: Address, x: Address Output: Integer }
Function.Num_MatQRSolve   { Input: a: Address, b: Address, x: Address Output: Integer }  // least squares
Function.Num_MatSVD       { Input: a: Address, u: Address, s: Address, v: Address Output: Integer }
Function.Num_MatRank      { Input: a: Address, tol: Real Output: Integer }

// --- Root finding ---
Function.Num_Newton1D     { Input: fn: Address, ctx: Address, x0: Real, out: Address Output: Integer }
Function.Num_NewtonND     { Input: fn: Address, ctx: Address, x0: Address, out: Address Output: Integer }
Function.Num_Bisect       { Input: fn: Address, ctx: Address, lo: Real, hi: Real, out: Address Output: Integer }

// --- Exact predicates (§6.5) ---
Function.Num_Orient2D     { Input: a: Address, b: Address, c: Address Output: Integer }
Function.Num_Orient3D     { Input: a: Address, b: Address, c: Address, d: Address Output: Integer }
Function.Num_InCircle     { Input: a: Address, b: Address, c: Address, d: Address Output: Integer }
Function.Num_InSphere     { Input: a: Address, b: Address, c: Address, d: Address, e: Address Output: Integer }

// --- Tolerance vocabulary (§6.4) ---
Function.Num_IsZero       { Input: a: Real Output: Integer }
Function.Num_IsEqual      { Input: a: Real, b: Real Output: Integer }
Function.Num_PointsEqual  { Input: pa: Address, pb: Address, tol: Real Output: Integer }
Function.Num_DirsParallel { Input: da: Address, db: Address Output: Integer }
Function.Num_DirsSame     { Input: da: Address, db: Address Output: Integer }
Function.Num_ParamEqual   { Input: a: Real, b: Real Output: Integer }
SubRoutine.Num_SetModelSize { Input: diag: Real }

// --- Bounding boxes ---
SubRoutine.Num_BoxInit    { Input: b: Address }              // empty box
SubRoutine.Num_BoxAddPt   { Input: b: Address, p: Address }
SubRoutine.Num_BoxExpand  { Input: b: Address, d: Real }
Function.Num_BoxOverlap   { Input: a: Address, b: Address, tol: Real Output: Integer }
Function.Num_BoxContains  { Input: b: Address, p: Address, tol: Real Output: Integer }
Function.Num_BoxDiagonal  { Input: b: Address Output: Real }

// --- Deterministic PRNG (fuzzing; xorshift64*) ---
SubRoutine.Num_RandSeed   { Input: seed: Integer }
Function.Num_RandU64      { Output: Integer }
Function.Num_RandReal     { Input: lo: Real, hi: Real Output: Real }
```

**Invariants:**
- Predicates return exactly `-1`, `0`, or `+1` and are consistent: swapping two
  arguments negates the sign, always.
- `Num_V3Normalize` either returns a unit vector to within `angular` tolerance
  or `CAD_E_DEGENERATE`. Never both, never neither.
- PRNG is reproducible from seed alone, independent of platform and build.

**Tests:** predicate signs against arbitrary-precision reference values on
near-degenerate configurations (collinear to 1 ulp, coplanar to 1 ulp);
`Orient3D` antisymmetry under all 24 argument permutations; LU/QR solves against
known systems including rank-deficient ones; SVD reconstruction error;
normalize on vectors spanning 1e-300 to 1e300.

---

#### CAD.Store — L0.5

**May call:** CAD.Sys, CAD.Num
**Purpose:** All entity memory. The single place `Allocate`/`Deallocate` and
raw array access appear.

```ailang
// Slab: fixed-stride table with free list and generation counters
Function.Store_SlabCreate  { Input: tag: Integer, stride: Integer, cap: Integer Output: Address }
SubRoutine.Store_SlabDestroy { Input: slab: Address }
Function.Store_Alloc       { Input: slab: Address Output: Integer }   // handle, 0 on failure
Function.Store_Free        { Input: h: Integer Output: Integer }      // bumps generation
Function.Store_Ptr         { Input: h: Integer Output: Address }      // checked record address
Function.Store_IsLive      { Input: h: Integer Output: Integer }
Function.Store_Tag         { Input: h: Integer Output: Integer }
Function.Store_Index       { Input: h: Integer Output: Integer }
Function.Store_Count       { Input: slab: Address Output: Integer }

// Iteration over live entries (compaction-safe)
Function.Store_First       { Input: slab: Address Output: Integer }
Function.Store_Next        { Input: h: Integer Output: Integer }

// Scratch arenas: bump allocation for transient per-operation data
Function.Store_ScratchOpen { Input: bytes: Integer Output: Address }
Function.Store_ScratchAlloc{ Input: sc: Address, bytes: Integer Output: Address }
SubRoutine.Store_ScratchReset { Input: sc: Address }
SubRoutine.Store_ScratchClose { Input: sc: Address }
```

**Design notes.** Slabs grow by chunk, never by realloc — an existing record's
address is stable for its lifetime, so `Store_Ptr` results can be held across
allocations within a single operation. Because `Deallocate` requires an exact
size match, slabs allocate and free in fixed chunk sizes only, and individual
entities are never passed to `Deallocate`.

Scratch arenas are the standard idiom for boolean intermediates: open one at the
top of the operation, bump-allocate freely, close at the end. No per-object
lifetime tracking anywhere in `CAD.Bool`.

**Invariants:** a handle returned by `Store_Alloc` is live until `Store_Free`;
after free, `Store_IsLive` returns 0 forever for that exact handle value, even
after the slot is recycled (generation differs). Index 0 of every slab is
reserved.

**Tests:** allocate/free/realloc cycles verifying generation bumps; stale handle
detection after 65,537 recycles (generation wrap must still be caught by index
liveness); iteration correctness with holes; scratch arena reset reuse.

---

#### CAD.Geom — L1

**May call:** CAD.Num, CAD.Store
**Purpose:** Pure geometry. Curves and surfaces, evaluation and differential
properties. **Knows nothing about topology** — no faces, no edges, no solids.
This separation is what makes the layer independently testable.

```ailang
FixedPool.Geom_CurveType {
    "LINE":     Initialize=1
    "CIRCLE":   Initialize=2
    "ELLIPSE":  Initialize=3
    "NURBS":    Initialize=4
    "INTCURVE": Initialize=5     // approximated intersection curve
}

FixedPool.Geom_SurfType {
    "PLANE":     Initialize=1
    "CYLINDER":  Initialize=2
    "CONE":      Initialize=3
    "SPHERE":    Initialize=4
    "TORUS":     Initialize=5
    "NURBS":     Initialize=6
    "EXTRUSION": Initialize=7
    "REVOLUTION":Initialize=8
    "OFFSET":    Initialize=9
}

// --- Construction ---
Function.Geom_MakeLine     { Input: p: Address, d: Address Output: Integer }
Function.Geom_MakeCircle   { Input: c: Address, n: Address, r: Real Output: Integer }
Function.Geom_MakeNurbsCrv { Input: deg: Integer, ctrl: Address, knots: Address, w: Address Output: Integer }
Function.Geom_MakePlane    { Input: p: Address, n: Address Output: Integer }
Function.Geom_MakeCylinder { Input: p: Address, axis: Address, r: Real Output: Integer }
Function.Geom_MakeCone     { Input: apex: Address, axis: Address, half_angle: Real Output: Integer }
Function.Geom_MakeSphere   { Input: c: Address, r: Real Output: Integer }
Function.Geom_MakeTorus    { Input: c: Address, axis: Address, rmaj: Real, rmin: Real Output: Integer }
Function.Geom_MakeExtrusion{ Input: profile: Integer, dir: Address Output: Integer }
Function.Geom_MakeRevolution{Input: profile: Integer, axis_p: Address, axis_d: Address Output: Integer }
Function.Geom_MakeNurbsSrf { Input: du: Integer, dv: Integer, ctrl: Address, ku: Address, kv: Address Output: Integer }

// --- Evaluation. Parameter domains are normalized to [0,1]. ---
Function.Geom_EvalCurve    { Input: c: Integer, t: Real, nderiv: Integer, out: Address Output: Integer }
Function.Geom_EvalSurface  { Input: s: Integer, u: Real, v: Real, out: Address Output: Integer }
Function.Geom_CurveTangent { Input: c: Integer, t: Real, out: Address Output: Integer }
Function.Geom_SurfNormal   { Input: s: Integer, u: Real, v: Real, out: Address Output: Integer }
Function.Geom_Curvature    { Input: c: Integer, t: Real, out: Address Output: Integer }
Function.Geom_PrincipalCurv{ Input: s: Integer, u: Real, v: Real, out: Address Output: Integer }

// --- Inversion (point → parameter) ---
Function.Geom_InvertCurve  { Input: c: Integer, p: Address, out_t: Address Output: Integer }
Function.Geom_InvertSurface{ Input: s: Integer, p: Address, out_uv: Address Output: Integer }

// --- Properties ---
Function.Geom_CurveType    { Input: c: Integer Output: Integer }
Function.Geom_SurfType     { Input: s: Integer Output: Integer }
Function.Geom_CurveLength  { Input: c: Integer, t0: Real, t1: Real, out: Address Output: Integer }
Function.Geom_CurveBox     { Input: c: Integer, box: Address Output: Integer }
Function.Geom_SurfBox      { Input: s: Integer, box: Address Output: Integer }
Function.Geom_IsPeriodicU  { Input: s: Integer Output: Integer }
Function.Geom_IsPeriodicV  { Input: s: Integer Output: Integer }
Function.Geom_IsPlanar     { Input: s: Integer Output: Integer }
Function.Geom_IsClosed     { Input: c: Integer Output: Integer }

// --- Conversion and approximation ---
Function.Geom_ToNurbsCrv   { Input: c: Integer Output: Integer }   // exact for conics
Function.Geom_ToNurbsSrf   { Input: s: Integer Output: Integer }
Function.Geom_ApproxCurve  { Input: pts: Address, n: Integer, tol: Real Output: Integer }
Function.Geom_SplitCurve   { Input: c: Integer, t: Real, out_a: Address, out_b: Address Output: Integer }

// --- Parametric curves in surface parameter space (for trimming) ---
Function.Geom_MakePCurve   { Input: surf: Integer, uv_curve: Integer Output: Integer }
Function.Geom_EvalPCurve   { Input: pc: Integer, t: Real, out_uv: Address Output: Integer }
```

**Design notes.**

*Normalized parameter domains.* Every curve and surface presents `[0,1]`
parameterization at the interface. Internally a NURBS keeps its native knot
vector; the mapping is applied at the boundary. This is what makes a single
`param` tolerance meaningful across every geometry type, and it removes an
entire class of "which parameterization is this in" bugs.

*Analytic surfaces stay analytic.* A cylinder is stored as axis + radius, not as
a NURBS. Intersections between analytic surfaces have closed-form solutions
(§7.3 `CAD.Isect`) that are exact, fast, and robust. Converting everything to
NURBS up front — a common shortcut — throws that away permanently and is the
main reason some kernels struggle with simple mechanical geometry.

*Second derivatives are required*, not optional. Surface/surface marching needs
curvature to choose step size, and tessellation needs it for adaptive
refinement.

**Invariants:**
- `EvalSurface` at any interior `(u,v)` returns `valid=1` with a unit normal, or
  `valid=0` at a genuine degeneracy (cone apex, sphere pole). Never a
  near-zero-length "normal".
- `InvertCurve(c, EvalCurve(c,t).p)` returns `t` to within `param` tolerance,
  for every curve type, on the whole domain.
- `ToNurbsCrv` on a conic reproduces the original to within `linear/10` at 1000
  sample points — rational NURBS represent conics exactly, so any larger error
  is a bug.

**Tests:** analytic derivatives vs. high-order finite differences at 10,000
random parameters per type; inversion round-trips; NURBS evaluation against
de Boor reference values computed offline; degenerate constructions (zero-radius
circle, zero-length extrusion) return `CAD_E_DEGENERATE` rather than producing
an entity.

---

#### CAD.Topo — L2

**May call:** CAD.Num, CAD.Store, CAD.Geom
**Purpose:** Topological structure and its invariants.

**The central design change from v2: radial edge, not half-edge.**

v2 specified a half-edge structure. Half-edge assumes manifold topology — every
edge has exactly two adjacent faces. Boolean intermediate states routinely
violate this: coincident faces, edges with four or more incident faces where two
solids touch along a seam, dangling faces mid-stitch, non-manifold vertices
where two solids meet at a point. A half-edge structure cannot represent these
states, so a boolean built on it must special-case around configurations it
cannot express — which is where kernels fail.

Radial edge stores, per edge, a **ring of coedges** ordered radially around the
edge. Two faces, four faces, or one is equally representable.

Discovering this in Phase 7 means rewriting Topo, Bool, and everything that
touches a face loop. It is the most expensive possible mistake to make late, and
it is free to avoid now.

```
Solid ──1:N──> Shell ──1:N──> Face ──1:N──> Loop ──1:N──> Coedge
                                 │                            │
                                 └──> Surface            radial ring
                                                              │
                                                              v
                              Vertex <──2──  Edge ──1:N──> Coedge
                                               │
                                               └──> Curve
```

```ailang
LinkagePool.Topo_Coedge {
    "edge":       Initialize=0    // parent edge
    "loop":       Initialize=0    // owning loop
    "next":       Initialize=0    // next coedge in loop
    "prev":       Initialize=0    // prev coedge in loop
    "radial_next":Initialize=0    // next coedge around edge (radial ring)
    "radial_prev":Initialize=0
    "pcurve":     Initialize=0    // parameter-space curve on the face's surface
    "sense":      Initialize=0    // 0 = with edge direction, 1 = against
}

LinkagePool.Topo_Edge {
    "vstart":  Initialize=0
    "vend":    Initialize=0
    "curve":   Initialize=0
    "coedge":  Initialize=0    // entry into radial ring
    "tol":     Initialize=0    // per-entity tolerance (§6.3)
    "tstart":  Initialize=0    // curve parameter at vstart
    "tend":    Initialize=0
}

LinkagePool.Topo_Face {
    "surface": Initialize=0
    "loop":    Initialize=0    // first loop; outer loop is always first
    "shell":   Initialize=0
    "sense":   Initialize=0    // 0 = surface normal is outward
    "tol":     Initialize=0
    "pid":     Initialize=0    // persistent id (§7.3 CAD.Feat)
}
```

```ailang
// --- Construction (low level) ---
Function.Topo_MakeVertex   { Input: p: Address Output: Integer }
Function.Topo_MakeEdge     { Input: v0: Integer, v1: Integer, curve: Integer, t0: Real, t1: Real Output: Integer }
Function.Topo_MakeLoop     { Input: face: Integer Output: Integer }
Function.Topo_MakeCoedge   { Input: loop: Integer, edge: Integer, sense: Integer Output: Integer }
Function.Topo_MakeFace     { Input: surface: Integer, shell: Integer Output: Integer }
Function.Topo_MakeShell    { Input: solid: Integer Output: Integer }
Function.Topo_MakeSolid    { Output: Integer }

// --- Euler operators (structure-preserving primitives) ---
Function.Topo_MEV  { Input: v: Integer, loop: Integer, p: Address, out: Address Output: Integer }  // make edge+vertex
Function.Topo_MEF  { Input: c0: Integer, c1: Integer, surf: Integer, out: Address Output: Integer }// make edge+face
Function.Topo_KEV  { Input: e: Integer Output: Integer }   // kill edge+vertex
Function.Topo_KEF  { Input: e: Integer Output: Integer }   // kill edge+face
Function.Topo_MEKR { Input: c0: Integer, c1: Integer Output: Integer }  // make edge, kill ring
Function.Topo_KEMR { Input: e: Integer, out: Address Output: Integer }  // kill edge, make ring

// --- Radial ring navigation ---
Function.Topo_EdgeCoedgeCount { Input: e: Integer Output: Integer }
Function.Topo_EdgeCoedgeAt    { Input: e: Integer, i: Integer Output: Integer }
Function.Topo_RadialNext      { Input: ce: Integer Output: Integer }
Function.Topo_CoedgePartner   { Input: ce: Integer Output: Integer }  // 0 if non-manifold
Function.Topo_IsManifoldEdge  { Input: e: Integer Output: Integer }

// --- Queries ---
Function.Topo_FaceLoopCount   { Input: f: Integer Output: Integer }
Function.Topo_FaceOuterLoop   { Input: f: Integer Output: Integer }
Function.Topo_LoopCoedgeCount { Input: l: Integer Output: Integer }
Function.Topo_FaceEdges       { Input: f: Integer, out: Address Output: Integer }  // Arrays
Function.Topo_VertexEdges     { Input: v: Integer, out: Address Output: Integer }
Function.Topo_EdgeFaces       { Input: e: Integer, out: Address Output: Integer }
Function.Topo_SolidFaces      { Input: s: Integer, out: Address Output: Integer }
Function.Topo_FaceBox         { Input: f: Integer, box: Address Output: Integer }
Function.Topo_SolidBox        { Input: s: Integer, box: Address Output: Integer }

// --- Geometric properties ---
Function.Topo_FaceArea        { Input: f: Integer, out: Address Output: Integer }
Function.Topo_SolidVolume     { Input: s: Integer, out: Address Output: Integer }
Function.Topo_SolidCentroid   { Input: s: Integer, out: Address Output: Integer }

// --- Validation and repair ---
Function.Topo_Validate        { Input: s: Integer, report: Address Output: Integer }
Function.Topo_MergeVertices   { Input: s: Integer, tol: Real Output: Integer }
Function.Topo_StitchFaces     { Input: faces: Address, out: Address Output: Integer }
Function.Topo_OrientShell     { Input: sh: Integer Output: Integer }
Function.Topo_RemoveSliver    { Input: s: Integer, tol: Real Output: Integer }

// --- Copy ---
Function.Topo_CopySolid       { Input: s: Integer Output: Integer }
Function.Topo_TransformSolid  { Input: s: Integer, xf: Address Output: Integer }
```

**Invariants — checked by `Topo_Validate`, and asserted after every Euler
operator under `-D2`:**

1. **Euler–Poincaré:** `V − E + F = 2(S − G) + R` for every solid, where S is
   shells, G genus, R inner loops (rings).
2. **Loop closure:** following `next` from any coedge returns to the start in
   exactly `LoopCoedgeCount` steps.
3. **Radial ring closure:** following `radial_next` from any coedge returns to
   the start in exactly `EdgeCoedgeCount` steps.
4. **Coedge/edge consistency:** every coedge in edge E's radial ring has
   `edge == E`; every coedge in loop L has `loop == L`.
5. **Vertex consistency:** an edge's `vstart`/`vend` match the endpoints of its
   curve at `tstart`/`tend`, to within the edge's tolerance.
6. **Orientation consistency:** for a manifold edge, the two coedges have
   opposite `sense`.
7. **Shell closure:** a closed shell has every edge with an even number of
   coedges (≥2), and the sum of signed face areas produces zero net flux.
8. **Volume positivity:** a solid bounded by an outward-oriented closed shell has
   positive volume; inner void shells have negative volume.

**Tests:** all invariants after every Euler operator on 500 random operator
sequences; construct-and-validate for the canonical corpus (§10.3); genus 0–5
solids satisfy Euler–Poincaré; deliberate corruption of each invariant is
detected by `Topo_Validate` (a validator that never fires is untested).

---

#### CAD.Isect — L3

**May call:** CAD.Num, CAD.Store, CAD.Geom
**Purpose:** All intersection mathematics.

**Split out from Boolean deliberately.** In v2 this was buried inside
`CAD.Boolean`. It is larger than the Boolean logic itself, it is where the real
mathematical difficulty lives, and it is independently testable in a way that
Boolean is not — you can verify an intersection curve by evaluating both
surfaces along it and measuring deviation, with no topology involved at all.
Separating it means the hardest code in the project gets the cleanest test
harness.

```ailang
LinkagePool.Isect_Result {
    "kind":    Initialize=0    // 0 none, 1 point(s), 2 curve(s), 3 coincident/overlap
    "points":  Initialize=0    // Arrays of Vec3
    "params_a":Initialize=0    // Arrays of parameter on A
    "params_b":Initialize=0
    "curves":  Initialize=0    // Arrays of curve handles (3D)
    "pcurve_a":Initialize=0    // Arrays of pcurves in A's parameter space
    "pcurve_b":Initialize=0
    "tol":     Initialize=0    // achieved accuracy — feeds §6.3 widening
}

// --- Entry points ---
Function.Isect_CurveCurve    { Input: ca: Integer, cb: Integer, res: Address Output: Integer }
Function.Isect_CurveSurface  { Input: c: Integer, s: Integer, res: Address Output: Integer }
Function.Isect_SurfaceSurface{ Input: sa: Integer, sb: Integer, res: Address Output: Integer }

// --- Analytic fast paths (exact, closed form) ---
Function.Isect__planePlane      { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__planeCylinder   { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__planeCone       { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__planeSphere     { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__planeTorus      { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__cylCylinder     { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__cylSphere       { Input: a: Integer, b: Integer, res: Address Output: Integer }
Function.Isect__sphereSphere    { Input: a: Integer, b: Integer, res: Address Output: Integer }

// --- General numeric path ---
Function.Isect__findSeedPoints  { Input: sa: Integer, sb: Integer, seeds: Address Output: Integer }
Function.Isect__marchCurve      { Input: sa: Integer, sb: Integer, seed: Address, out: Address Output: Integer }
Function.Isect__refinePoint     { Input: sa: Integer, sb: Integer, p: Address Output: Integer }
Function.Isect__subdivide       { Input: sa: Integer, sb: Integer, depth: Integer, out: Address Output: Integer }

// --- Support ---
Function.Isect_PointOnSurface   { Input: s: Integer, p: Address, tol: Real Output: Integer }
Function.Isect_PointOnCurve     { Input: c: Integer, p: Address, tol: Real Output: Integer }
Function.Isect_ClosestPoint     { Input: s: Integer, p: Address, out_uv: Address Output: Integer }
Function.Isect_SurfacesCoincide { Input: sa: Integer, sb: Integer, tol: Real Output: Integer }
```

**Algorithm strategy, in dispatch order:**

1. **Bounding-box reject.** No overlap within tolerance → `kind=0`, done.
2. **Analytic dispatch.** Both surfaces analytic → closed-form solver. This
   covers the overwhelming majority of mechanical geometry (planes, cylinders,
   spheres, cones, tori) and is exact, fast, and free of convergence failure.
   The analytic table is a 5×5 upper triangle: 15 pairs.
3. **Coincidence test.** Same surface type, same parameters within tolerance →
   `kind=3`. Must be tested *before* marching, because marching on coincident
   surfaces does not terminate.
4. **Subdivision + marching.** General case. Recursive box subdivision to
   isolate intersection branches, seed points refined by Newton on the
   two-surface system, then marching with curvature-adaptive step size and
   Newton correction at each step.
5. **Approximate to NURBS.** Marched point sequence fitted within tolerance.
   Achieved deviation is recorded in `Isect_Result.tol` and propagates into edge
   tolerance per §6.3.

**Hard cases that must be handled explicitly, not discovered later:**

| Case | Why it breaks naive marching | Required handling |
|---|---|---|
| Tangential contact | Newton Jacobian is singular | Detect via cross-product magnitude; use higher-order local analysis |
| Near-tangential | Convergence stalls, step size collapses | Widen result tolerance rather than failing; record in `res.tol` |
| Closed intersection curves | No boundary seed exists | Seed via extremal points of surface distance function |
| Multiple branches | Marching finds one, misses others | Subdivision must isolate all branches before marching any |
| Singular points (self-crossing) | Marching takes the wrong branch | Detect rank drop; enumerate branches explicitly |
| Coincident surfaces | Never terminates | Test in step 3, before marching |
| Grazing at a cone apex or sphere pole | Surface normal undefined | Degenerate-point registry per surface type |

**Invariants:**
- Every point on a returned intersection curve lies on both surfaces within
  `res.tol`. Verified by sampling — this is the primary correctness test.
- `Isect_SurfaceSurface(a,b)` and `Isect_SurfaceSurface(b,a)` return
  geometrically identical curve sets, up to parameterization direction.
- The function terminates for all inputs. There is a hard iteration cap; hitting
  it returns `CAD_E_NOCONVERGE` rather than hanging. **A kernel that hangs is
  worse than one that fails.**

**Tests:** all 15 analytic pairs against closed-form reference values; sampled
deviation ≤ `res.tol` at 1,000 points per curve; symmetry under argument swap;
the full hard-case table above as named regression fixtures; fuzz with
near-tangential configurations at increasing degeneracy (offset 1e-3 down to
1e-12) verifying either a correct result or a clean `CAD_E_NOCONVERGE`, never a
hang and never `CAD_E_INTERNAL`.

---

#### CAD.Bool — L4

**May call:** CAD.Num, CAD.Store, CAD.Geom, CAD.Topo, CAD.Isect
**Purpose:** Regularized boolean operations.

```ailang
FixedPool.Bool_Op {
    "UNION":     Initialize=1
    "SUBTRACT":  Initialize=2
    "INTERSECT": Initialize=3
}

Function.Bool_Union     { Input: a: Integer, b: Integer, out: Address Output: Integer }
Function.Bool_Subtract  { Input: a: Integer, b: Integer, out: Address Output: Integer }
Function.Bool_Intersect { Input: a: Integer, b: Integer, out: Address Output: Integer }

// Pipeline stages — exposed for testing, not for general use
Function.Bool__buildBVH      { Input: s: Integer Output: Address }
Function.Bool__candidatePairs{ Input: a: Integer, b: Integer, out: Address Output: Integer }
Function.Bool__intersectAll  { Input: pairs: Address, out: Address Output: Integer }
Function.Bool__imprintEdges  { Input: s: Integer, curves: Address Output: Integer }
Function.Bool__splitFaces    { Input: s: Integer Output: Integer }
Function.Bool__classifyFace  { Input: f: Integer, other: Integer Output: Integer }  // IN/OUT/ON_SAME/ON_OPP
Function.Bool__selectFaces   { Input: a: Integer, b: Integer, op: Integer, out: Address Output: Integer }
Function.Bool__stitch        { Input: faces: Address, out: Address Output: Integer }

// Point classification — exact, used by classifyFace
Function.Bool_ClassifyPoint  { Input: p: Address, s: Integer Output: Integer }  // -1 in, 0 on, +1 out
```

**Pipeline:**

```
1. BVH build           both solids, face-level bounding volume hierarchy
2. Candidate pairs     BVH traversal → face pairs with overlapping boxes
3. Intersect           CAD.Isect on each pair → 3D curves + pcurves on both faces
4. Imprint             insert intersection curves as edges into both solids,
                       splitting existing edges at crossings, merging coincident
                       vertices via union-find (§6.6)
5. Split faces         partition each imprinted face into regions bounded by
                       imprint edges and original loops
6. Classify            each region: inside / outside / on-boundary-same-sense /
                       on-boundary-opposite-sense relative to the other solid
7. Select              per operation table below
8. Stitch              assemble selected faces into closed shells; orient;
                       validate
```

**Classification table:**

| Op | From A keep | From B keep | ON pairs |
|---|---|---|---|
| Union | OUT | OUT | keep one of each same-sense pair |
| Subtract (A−B) | OUT | IN, reversed | keep opposite-sense pairs |
| Intersect | IN | IN | keep one of each same-sense pair |

**Classification is exact.** `Bool_ClassifyPoint` casts a ray from the test
point and counts signed crossings using `Num_Orient3D`, never floating-point
sign tests. Ray direction is chosen deterministically (derived from a hash of
the point coordinates) and re-chosen on any degenerate hit — a hit exactly on an
edge or vertex — so the result is reproducible across runs and independent of
face ordering.

Test points for a face region are placed at the region's parametric centroid,
projected to the surface, and verified to lie strictly inside the region by an
exact point-in-loop test before being used.

**The ON-boundary cases are where booleans actually fail.** Coincident faces
between the two solids are not an edge case to patch later; they occur in
ordinary use (a pad placed exactly on an existing face, a pocket cut exactly to
a wall). They are handled explicitly in step 6 with a same-sense/opposite-sense
distinction, and every one of them appears in the golden corpus.

**Invariants:**
- `A ∪ A ≡ A`, `A ∩ A ≡ A`, `A − A ≡ ∅` (idempotence)
- `A ∪ B ≡ B ∪ A`, `A ∩ B ≡ B ∩ A` (commutativity, geometric equality)
- `(A ∪ B) ∪ C ≡ A ∪ (B ∪ C)` (associativity)
- `vol(A ∪ B) + vol(A ∩ B) = vol(A) + vol(B)` within tolerance
- `A − B ≡ A ∩ complement(B)` for bounded test cases
- Every result passes `Topo_Validate` with a closed, correctly oriented shell
- Disjoint inputs: union yields two shells, intersect yields empty, subtract
  yields A unchanged
- Result is deterministic: identical inputs produce bit-identical output

**Tests:** the invariant set above as property tests over the golden corpus
(§10.3); volume conservation to `linear × surface_area`; OCCT oracle comparison
on volume, surface area, face count, and genus (§10.4); adversarial fuzz on
coincident, tangent, and near-degenerate configurations (§10.5).

---

#### CAD.Sketch — L5

**May call:** CAD.Num, CAD.Store, CAD.Geom
**Purpose:** 2D geometry and constraint solving. Independent of Topo/Isect/Bool,
so this track proceeds fully in parallel.

```ailang
FixedPool.Sketch_EntType {
    "POINT": Initialize=1  "LINE":   Initialize=2  "ARC":    Initialize=3
    "CIRCLE":Initialize=4  "ELLIPSE":Initialize=5  "SPLINE": Initialize=6
}

FixedPool.Sketch_ConType {
    "COINCIDENT":   Initialize=1   "PARALLEL":     Initialize=2
    "PERPENDICULAR":Initialize=3   "TANGENT":      Initialize=4
    "DISTANCE":     Initialize=5   "ANGLE":        Initialize=6
    "HORIZONTAL":   Initialize=7   "VERTICAL":     Initialize=8
    "EQUAL":        Initialize=9   "FIXED":        Initialize=10
    "RADIUS":       Initialize=11  "SYMMETRIC":    Initialize=12
    "MIDPOINT":     Initialize=13  "CONCENTRIC":   Initialize=14
    "POINT_ON":     Initialize=15
}

Function.Sketch_Create      { Input: plane_origin: Address, plane_n: Address, plane_x: Address Output: Integer }
Function.Sketch_AddPoint    { Input: sk: Integer, x: Real, y: Real Output: Integer }
Function.Sketch_AddLine     { Input: sk: Integer, p0: Integer, p1: Integer Output: Integer }
Function.Sketch_AddArc      { Input: sk: Integer, c: Integer, p0: Integer, p1: Integer Output: Integer }
Function.Sketch_AddCircle   { Input: sk: Integer, c: Integer, r: Real Output: Integer }
Function.Sketch_AddSpline   { Input: sk: Integer, pts: Address, n: Integer Output: Integer }
Function.Sketch_SetConstruction { Input: ent: Integer, flag: Integer Output: Integer }

Function.Sketch_AddConstraint { Input: sk: Integer, type: Integer, e0: Integer, e1: Integer, val: Real Output: Integer }
Function.Sketch_RemoveConstraint { Input: con: Integer Output: Integer }
Function.Sketch_DriveParam    { Input: con: Integer, val: Real Output: Integer }

Function.Sketch_Solve       { Input: sk: Integer, report: Address Output: Integer }
Function.Sketch_DOF         { Input: sk: Integer Output: Integer }
Function.Sketch_Diagnose    { Input: sk: Integer, report: Address Output: Integer }

// Profile extraction — the bridge to CAD.Feat
Function.Sketch_FindLoops   { Input: sk: Integer, out: Address Output: Integer }
Function.Sketch_LoopIsClosed{ Input: loop: Address Output: Integer }
Function.Sketch_LoopArea    { Input: loop: Address, out: Address Output: Integer }
Function.Sketch_ToCurves3D  { Input: sk: Integer, loop: Address, out: Address Output: Integer }
Function.Sketch_Validate    { Input: sk: Integer, report: Address Output: Integer }
```

**Solver design.** Newton–Raphson on the constraint residual system, with
analytic Jacobian (not finite-differenced — analytic derivatives are
straightforward for this constraint set and dramatically improve convergence).
QR least-squares for the underdetermined case, moving the system minimally from
its current configuration so the sketch does not jump when a user drags.
Rank analysis via SVD distinguishes the three diagnostic outcomes.

Constraints are decomposed into independent subsystems by connected-component
analysis on the constraint graph before solving. A 400-entity sketch typically
decomposes into many small systems, turning one large dense solve into many tiny
ones. This is the single biggest performance factor in the solver.

**Diagnostics** — must distinguish, because "solve failed" is useless to a user:
- Under-constrained: report remaining DOF and which entities carry them
- Over-constrained: report the *specific redundant constraint set* via rank
  analysis, not just a flag
- Inconsistent: constraints that cannot be satisfied simultaneously
- Non-convergent: consistent but Newton failed from this starting point

**Invariants:** a fully constrained sketch has DOF 0 and a rank-complete
Jacobian; solving twice from the solved state is a no-op within `param`
tolerance; solving is invariant under constraint reordering; profile loops
extracted from a valid sketch are closed, non-self-intersecting (verified with
exact segment-crossing predicates), and correctly nested.

**Tests:** a corpus of ~100 sketches spanning fully/under/over-constrained;
known-DOF verification; drag stability (perturb a driving dimension by 1% for
1,000 steps, confirm no jumps and no divergence); redundant constraint
identification against hand-computed expected sets.

---

#### CAD.Feat — L6

**May call:** all of L0–L5
**Purpose:** Parametric feature tree, dependency graph, regeneration, and
persistent naming.

**Persistent naming gets a real algorithm here, not a table.** v2 had a
`persistent_id` table with no scheme attached to it. This is the single most
common reason parametric CAD models break: you edit an early feature, and later
features that referenced "the top face" now reference the wrong face or nothing
at all. FreeCAD's topological naming problem is exactly this. It must be
designed before `CAD.Feat` is implemented, not bolted on after.

```ailang
FixedPool.Feat_Type {
    "EXTRUDE":Initialize=1  "CUT":Initialize=2      "REVOLVE":Initialize=3
    "FILLET": Initialize=4  "CHAMFER":Initialize=5  "HOLE":Initialize=6
    "SHELL":  Initialize=7  "DRAFT":Initialize=8    "PATTERN_LIN":Initialize=9
    "PATTERN_CIR":Initialize=10 "MIRROR":Initialize=11 "IMPORT":Initialize=12
}

// --- Feature tree ---
Function.Feat_DocCreate     { Output: Integer }
Function.Feat_Create        { Input: doc: Integer, type: Integer, seq: Integer Output: Integer }
Function.Feat_SetParamReal  { Input: f: Integer, name: Address, v: Real Output: Integer }
Function.Feat_SetParamInt   { Input: f: Integer, name: Address, v: Integer Output: Integer }
Function.Feat_SetParamRef   { Input: f: Integer, name: Address, pid: Integer Output: Integer }
Function.Feat_GetParamReal  { Input: f: Integer, name: Address, out: Address Output: Integer }
Function.Feat_SetSuppressed { Input: f: Integer, flag: Integer Output: Integer }
Function.Feat_Reorder       { Input: f: Integer, new_seq: Integer Output: Integer }
Function.Feat_Delete        { Input: f: Integer Output: Integer }

// --- Dependency graph ---
Function.Feat_Dependencies  { Input: f: Integer, out: Address Output: Integer }
Function.Feat_Dependents    { Input: f: Integer, out: Address Output: Integer }
Function.Feat_TopoSort      { Input: doc: Integer, out: Address Output: Integer }  // E_CYCLE on cycle
Function.Feat_MarkDirty     { Input: f: Integer Output: Integer }

// --- Regeneration ---
Function.Feat_Rebuild       { Input: doc: Integer, report: Address Output: Integer }  // incremental
Function.Feat_RebuildAll    { Input: doc: Integer, report: Address Output: Integer }  // full
Function.Feat_Evaluate      { Input: f: Integer Output: Integer }
Function.Feat_ResultSolid   { Input: f: Integer Output: Integer }

// --- Persistent naming ---
Function.Feat_PidCreate     { Input: doc: Integer, entity: Integer, origin: Integer Output: Integer }
Function.Feat_PidResolve    { Input: doc: Integer, pid: Integer Output: Integer }   // → live handle
Function.Feat_PidMatch      { Input: doc: Integer, pid: Integer, candidates: Address Output: Integer }
Function.Feat_PidStatus     { Input: pid: Integer Output: Integer }  // resolved / ambiguous / lost
```

**Persistent naming scheme — generative provenance.**

Every topological entity records *how it came to exist*, not where it currently
sits. A face is not "face #7"; it is "the lateral face generated by extruding
sketch-3 edge-2." That description survives dimensional changes, because
changing the extrude distance does not change what generated the face.

```ailang
LinkagePool.Feat_Pid {
    "id":          Initialize=0
    "origin_feat": Initialize=0    // feature that created the entity
    "origin_kind": Initialize=0    // SKETCH_EDGE / SWEEP_CAP / BOOL_SPLIT / FILLET_FACE ...
    "source_a":    Initialize=0    // pid of generating entity (e.g. sketch edge)
    "source_b":    Initialize=0    // second source, for boolean-derived entities
    "ordinal":     Initialize=0    // disambiguator when one source yields several
    "geom_hint":   Initialize=0    // Vec3: a representative point, for fallback matching
    "surf_kind":   Initialize=0    // surface type, for fallback matching
    "status":      Initialize=0    // 0 resolved, 1 ambiguous, 2 lost
}
```

Resolution on rebuild, in strict order — each stage is tried only if the
previous produced no unique match:

1. **Exact provenance match.** Same origin feature, same kind, same sources,
   same ordinal. This resolves the overwhelming majority of cases and is the
   only stage that is fully reliable.
2. **Provenance without ordinal.** If exactly one candidate matches on
   everything but ordinal, take it. Handles a source entity that previously
   produced several children and now produces one.
3. **Geometric fallback.** Among candidates matching origin kind and surface
   type, choose the one nearest `geom_hint`, but **only if it is uniquely
   nearest by a clear margin** — the runner-up must be at least 10× further.
   Otherwise mark ambiguous.
4. **Fail loudly.** Mark the pid `lost`, mark the dependent feature invalid, and
   report it. **Never silently pick a face.** A model that reports "the fillet
   lost its reference edge" is repairable; a model that silently filleted the
   wrong edge is a wrong part that machines wrong.

Stage 4 is the design decision that separates this from FreeCAD's behavior, and
it is a deliberate choice of loud failure over quiet corruption.

**Incremental rebuild.** Dirty-marking propagates forward through the dependency
graph. Only dirty features re-evaluate; clean features reuse cached solids.
Editing the last feature of a 200-feature tree costs one evaluation.
`Feat_RebuildAll` exists for validation and for the invariant test that
incremental and full rebuild produce identical results.

**Invariants:**
- `Feat_Rebuild` and `Feat_RebuildAll` produce geometrically identical results,
  always. This is the master test for incremental correctness.
- Rebuild is deterministic and idempotent: rebuilding a clean document changes
  nothing.
- Parameter round-trip: set a parameter, rebuild, set it back, rebuild — the
  result is bit-identical to the original.
- A cycle in the dependency graph is detected and reported, never entered.
- Suppressing then unsuppressing a feature restores the exact prior result.

**Tests:** a 50-feature reference model with every parameter perturbed
individually, verifying incremental == full; reference-breaking scenarios
(delete the source sketch edge for a fillet; reorder features so a reference
precedes its source) verifying loud failure rather than silent misresolution;
feature reordering, deletion, and suppression matrices.

---

#### CAD.Tess — L7

**May call:** CAD.Num, CAD.Store, CAD.Geom, CAD.Topo

```ailang
Function.Tess_Solid      { Input: s: Integer, quality: Address, out: Address Output: Integer }
Function.Tess_Face       { Input: f: Integer, quality: Address, out: Address Output: Integer }
Function.Tess_Edge       { Input: e: Integer, quality: Address, out: Address Output: Integer }  // polyline
Function.Tess_MeshVerts  { Input: m: Integer, out: Address Output: Integer }
Function.Tess_MeshNormals{ Input: m: Integer, out: Address Output: Integer }
Function.Tess_MeshIndices{ Input: m: Integer, out: Address Output: Integer }
Function.Tess_MeshStats  { Input: m: Integer, out: Address Output: Integer }
Function.Tess_Validate   { Input: m: Integer, report: Address Output: Integer }

LinkagePool.Tess_Quality {
    "chord_tol":  Initialize=0    // max deviation from true surface (mm)
    "angle_tol":  Initialize=0    // max normal deviation between adjacent tris (rad)
    "max_edge":   Initialize=0    // max triangle edge length, 0 = unlimited
    "min_edge":   Initialize=0    // collapse below this
}
```

**Approach:** constrained Delaunay in each face's parameter space, using the
exact `Num_InCircle` predicate, with boundary edges from trimming loops as
constraints. Adaptive refinement driven by chord and angle tolerance evaluated
against actual surface curvature. Parameter-space Delaunay must account for
metric distortion — a triangle that is well-shaped in `(u,v)` can be a sliver in
3D on a highly distorted surface, so refinement criteria are evaluated in 3D.

**Watertightness is non-negotiable.** Adjacent faces must produce identical
vertex positions along shared edges. This is guaranteed structurally: edges are
tessellated **once**, into a shared polyline keyed by edge handle, and both
adjacent faces consume that same polyline as a boundary constraint. Tessellating
each face independently and hoping the boundaries agree is the standard way STL
exports come out leaking.

**Invariants:** the mesh of a closed solid is watertight (every mesh edge shared
by exactly two triangles); mesh volume converges to `Topo_SolidVolume` as
`chord_tol → 0`; no degenerate or inverted triangles; all normals outward.

**Tests:** watertightness on the full golden corpus; volume convergence at
tolerances 1e-1 through 1e-5; triangle quality distribution; determinism.

---

#### CAD.Doc — L7 — **REMOVED (v3.1)**

`.cadx` / `CAD.Doc` is **not implemented**. All former `Doc_*` responsibilities
move to:

- **`CAD.Repo`** — authoritative document open/save, sessions, revisions
- **`CAD.IO`** — STEP / STL / DXF interchange only

Do not add a proprietary binary container without a design escalation in §13.

---

#### CAD.IO — L7

**May call:** CAD.Sys, CAD.Store, CAD.Num, CAD.Geom, CAD.Topo, CAD.Tess

```ailang
Function.IO_ImportSTEP { Input: path: Address, out: Address, report: Address Output: Integer }
Function.IO_ExportSTEP { Input: solids: Address, path: Address Output: Integer }
Function.IO_ExportSTL  { Input: mesh: Integer, path: Address, binary: Integer Output: Integer }
Function.IO_ImportSTL  { Input: path: Address, out: Address Output: Integer }
Function.IO_ExportDXF  { Input: sketches: Address, path: Address Output: Integer }
Function.IO_ExportOBJ  { Input: mesh: Integer, path: Address Output: Integer }
```

STEP is the bulk of this library. Target AP203/AP214 geometric subset:
`ADVANCED_BREP_SHAPE_REPRESENTATION` with the analytic surface set plus B-spline
surfaces. Three stages: tokenizer/parser for ISO-10303-21 exchange syntax,
entity reference graph resolution (forward references are pervasive), and
geometric entity construction mapping STEP entities onto `CAD.Geom`/`CAD.Topo`.

Imported geometry is *always* validated and healed on entry — real-world STEP
files routinely contain gaps above tolerance, inconsistent face orientations,
and duplicate vertices. Import runs `Topo_MergeVertices`, `Topo_StitchFaces`,
`Topo_OrientShell`, and `Topo_Validate`, and reports what it repaired.

**Tests:** round-trip STEP export/import preserving volume, surface area, and
face count; import of a public STEP corpus with validation reports; STL
watertightness; deliberately malformed files rejected cleanly.

---

#### CAD.Repo — L7, product system of record

**May call:** CAD.Sys, CAD.Store, CAD.Num, CAD.Feat, Postgres driver  
(Geometry load/save may also touch CAD.Topo / CAD.Tess when materializing caches.)

**Role.** Authoritative persistence for the product: documents, feature trees,
parameters, sketches, sessions, users, checkouts, revisions, and optional
derived B-rep/mesh caches. Local PG = workstation. Shared PG = multi-user and
agents. Kernel *unit* tests do not require PG; product open/save does.

The driver (`Library.PostgreSQL_Complete`) is already in-tree. Prefer binary
or hex/base64-safe paths for `BYTEA`. Verify NUL-safe blob round-trip early.

```ailang
Function.Repo_Connect      { Input: conninfo: Address Output: Integer }
Function.Repo_Disconnect   { Input: conn: Integer Output: Integer }
Function.Repo_InitSchema   { Input: conn: Integer Output: Integer }
Function.Repo_OpenPart     { Input: conn: Integer, doc_uuid: Address, rev: Integer, out_doc: Address Output: Integer }
Function.Repo_CommitPart   { Input: conn: Integer, doc: Integer, msg: Address Output: Integer }  // → new rev
Function.Repo_ListRevisions{ Input: conn: Integer, doc_uuid: Address, out: Address Output: Integer }
Function.Repo_BeginSession { Input: conn: Integer, user: Address, out_session: Address Output: Integer }
Function.Repo_EndSession   { Input: conn: Integer, session: Integer Output: Integer }
Function.Repo_Checkout     { Input: conn: Integer, doc_uuid: Address, session: Integer Output: Integer }
Function.Repo_Checkin      { Input: conn: Integer, doc: Integer, session: Integer Output: Integer }
```

**Schema sketch (v3.1).** Authoritative rows are relational where it helps
query; heavy geometry is BYTEA cache. Expand feature/sketch tables as the
kernel solidifies — Postgres gives parametric search for free.

```sql
CREATE TABLE cad_project (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cad_document (
    uuid        UUID PRIMARY KEY,
    project_id  BIGINT REFERENCES cad_project(id),
    name        TEXT NOT NULL,
    kind        SMALLINT NOT NULL,        -- 1 part, 2 assembly
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cad_session (
    id          BIGSERIAL PRIMARY KEY,
    project_id  BIGINT REFERENCES cad_project(id),
    user_name   TEXT NOT NULL,
    started_at  TIMESTAMPTZ DEFAULT now(),
    ended_at    TIMESTAMPTZ,
    status      TEXT DEFAULT 'active'
);

CREATE TABLE cad_revision (
    id          BIGSERIAL PRIMARY KEY,
    doc_uuid    UUID REFERENCES cad_document(uuid),
    rev_number  INTEGER NOT NULL,
    parent_rev  BIGINT REFERENCES cad_revision(id),
    author      TEXT,
    message     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    -- Authoritative: feature/param source (JSON or normalized child tables)
    feature_tree JSONB NOT NULL,
    params       JSONB NOT NULL DEFAULT '{}',
    content_sha  BYTEA NOT NULL,
    UNIQUE (doc_uuid, rev_number)
);

-- Optional normalized features for SQL search / PDM (not hot-path topology)
CREATE TABLE cad_feature (
    id          BIGSERIAL PRIMARY KEY,
    rev_id      BIGINT REFERENCES cad_revision(id) ON DELETE CASCADE,
    feat_index  INTEGER NOT NULL,
    kind        TEXT NOT NULL,            -- pad, pocket, revolve, hole, ...
    params      JSONB NOT NULL,
    suppressed  BOOLEAN DEFAULT false
);

CREATE TABLE cad_reference (             -- assembly / external-geometry links
    id          BIGSERIAL PRIMARY KEY,
    from_rev    BIGINT REFERENCES cad_revision(id),
    to_doc      UUID REFERENCES cad_document(uuid),
    to_rev      BIGINT REFERENCES cad_revision(id),   -- NULL = float to latest
    role        SMALLINT NOT NULL
);

CREATE TABLE cad_checkout (
    doc_uuid    UUID PRIMARY KEY REFERENCES cad_document(uuid),
    session_id  BIGINT REFERENCES cad_session(id),
    owner       TEXT NOT NULL,
    acquired_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cad_cache_brep (            -- purely derived, safe to truncate
    rev_id        BIGINT PRIMARY KEY REFERENCES cad_revision(id),
    kernel_ver    INTEGER NOT NULL,
    payload       BYTEA NOT NULL,
    payload_sha   BYTEA NOT NULL
);

CREATE TABLE cad_cache_mesh (
    rev_id        BIGINT NOT NULL REFERENCES cad_revision(id),
    lod_key       TEXT NOT NULL,         -- deflection params fingerprint
    kernel_ver    INTEGER NOT NULL,
    payload       BYTEA NOT NULL,
    PRIMARY KEY (rev_id, lod_key)
);

-- UI configuration (workbenches, toolbars, tools) — free with PG; no local
-- binary UI registry. Per-user overrides optional later.
CREATE TABLE cad_workbench (
    id          BIGSERIAL PRIMARY KEY,
    project_id  BIGINT REFERENCES cad_project(id),  -- NULL = global
    name        TEXT NOT NULL,
    icon        TEXT,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE cad_toolbar (
    id          BIGSERIAL PRIMARY KEY,
    workbench_id BIGINT REFERENCES cad_workbench(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE cad_tool (
    id          BIGSERIAL PRIMARY KEY,
    toolbar_id  BIGINT REFERENCES cad_toolbar(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    command     TEXT NOT NULL,            -- cadk / command id
    icon        TEXT,
    sort_order  INTEGER DEFAULT 0,
    enabled     BOOLEAN DEFAULT true
);

CREATE TABLE cad_ui_pref (
    session_or_user TEXT NOT NULL,       -- user name or session key
    key           TEXT NOT NULL,
    value         JSONB NOT NULL,
    PRIMARY KEY (session_or_user, key)
);
```

---

#### cadk — L8, CLI driver

Everything the kernel does, reachable from a shell. Agent development and
fuzzing target this binary. Documents are **repo ids / revs** or **interchange
files**, never `.cadx`.

```
cadk test     <suite>                         # registered pure-memory suites
cadk props    --solid <handle-or-step>        # volume, area, centroid, genus
cadk bool     --op union|subtract|intersect   # memory or STEP inputs → STEP/STL
cadk tess     --in <step> -o <out.stl> --chord 0.01 --angle 0.1
cadk isect    ...
cadk solve    --sketch <id> --report
cadk import   <in.step|dxf|stl> --project P --name N   # → new doc rev in PG
cadk export   --doc UUID [--rev N] -o <out.step|stl>
cadk open     --doc UUID [--rev N]            # load into session
cadk commit   --doc UUID -m "msg"             # write new rev
cadk session  begin|end
cadk fuzz     --seed N --ops M --op-set booleans
cadk diff     --doc UUID --rev-a A --rev-b B  # geometric comparison
```

Every command returns 0 on success and the negated status code on failure, so
shell scripts and test harnesses can branch on outcome directly.

---

## 8. Data Flow

```
  Sketch entities + constraints
            │
            ▼  Sketch_Solve            (Newton + QR, subsystem decomposition)
  Fully-defined 2D geometry
            │
            ▼  Sketch_FindLoops        (exact segment predicates)
  Closed, nested profile loops
            │
            ▼  Feat_Evaluate           (sweep: extrude / revolve)
  Topology + geometry for one feature
            │
            ▼  Bool_*                  (imprint → split → classify → stitch)
  Combined topology
            │
            ▼  Topo_Validate           (Euler-Poincaré, closure, orientation)
  Validated B-rep  ────────────────────────┐
            │                              │
            ▼  Tess_Solid                  ▼  Repo_Commit / IO_ExportSTEP
  Watertight mesh                    PG rev / .step
            │
            ▼  IO_ExportSTL
         .stl
```

Feature evaluation is a fold over the tree: each feature consumes the previous
result solid and produces a new one. Suppressed features are skipped; clean
features return their cache.

---

## 9. Numeric Foundation — Resolved

The open questions of earlier drafts are closed (§3.1). Recording the outcome
because it removes a substantial speculative line item:

| Earlier concern | Outcome |
|---|---|
| Transcendentals may be absent; `CAD.Num` grows 600–900 lines of CORDIC | **Not needed.** `Float_Sin`, `Float_Cos`, `Float_Tan`, `Float_Atan2`, `Float_Exp`, `Float_Log`, `Float_Pow` are compiler primitives |
| `Sqrt` may need software implementation | **Not needed.** `Float_Sqrt` compiles to `SQRTSD` |
| Exact two-product needs assembly or Dekker splitting | **Not needed.** `Float_FMA` is a primitive |
| Float params may need boxing to fit 6 registers | **Not needed.** Floats occupy ordinary integer slots; no signature exceeds 5 arguments |

The dependency table, for reference:

| Function | Needs | Status |
|---|---|---|
| `Geom_EvalCurve` (circle, ellipse) | `Float_Sin`, `Float_Cos` | available |
| `Geom_InvertSurface` (cylinder, cone) | `Float_Atan2` | available, with quadrant tracking |
| `Geom_InvertSurface` (sphere, torus) | `Float_Atan2`, arcsine | `Float_Atan2` available; arcsine via `Atan2` identity |
| `Geom_MakeRevolution` | `Float_Sin`, `Float_Cos` | available |
| `Num_V3Normalize` | `Float_Sqrt` | available |
| `Num_Expansion*` | `Float_FMA` | available |

`Num_DirsParallel` is specified via cross-product magnitude rather than an
arccosine. This is not a workaround for a missing intrinsic — it is the more
numerically stable formulation near parallel, where `Acos` loses precision
catastrophically, and it would be the right choice regardless.

**One genuine gap.** There is no `Float_Neg` in the documented operation list.
Negation is `Float_Sub(zero_r, x_r)`, or a sign-bit flip via
`BitwiseXor(x_r, sign_mask)` where `sign_mask` is `0x8000000000000000`. The
latter is exact, branchless, and correct for zeros and NaNs; `CAD.Num` should
wrap it as `Num_FNeg` and use that everywhere. Note this is one of the few
places where bit manipulation of a `Real` is legitimate — it must be exempted
from the §3.2 integer-op audit by name.

**Exact predicates remain insulated from all of this.** They need only f64
multiply, add, and `Float_FMA`. This is why §6.1 confines topological decisions
to them: the combinatorial core of the kernel depends on the smallest, most
stable part of the numeric surface.

---

## 10. Testing Scheme

Four tiers. Every library declares which tiers apply to it and what its specific
obligations are. Nothing merges without its declared tiers passing.

### 10.1 Tier 1 — Invariants and Properties

Executable assertions of mathematical truths, run continuously. This tier is
built on `DebugAssert` and the `-D` levels, so it is free in release builds.

Two forms:

**In-code invariants.** Compiled in at `-D2`, checked after every mutating
operation. Euler–Poincaré after every Euler operator, loop and radial ring
closure after every topology edit, handle liveness on every public entry.

**Property tests.** Generated inputs, asserted relationships:

| Property | Library |
|---|---|
| `Orient3D` antisymmetry under all 24 permutations | Num |
| `Orient3D` sign agrees with arbitrary-precision reference | Num |
| `InvertCurve(EvalCurve(t)) == t` | Geom |
| Analytic derivative == high-order finite difference | Geom |
| `V − E + F = 2(S − G) + R` | Topo |
| Loop and radial ring closure | Topo |
| Closed shell has zero net flux | Topo |
| Intersection points lie on both surfaces within `res.tol` | Isect |
| `Isect(a,b) ≡ Isect(b,a)` | Isect |
| `A ∪ A ≡ A`, `A ∩ A ≡ A`, `A − A ≡ ∅` | Bool |
| `vol(A∪B) + vol(A∩B) = vol(A) + vol(B)` | Bool |
| Commutativity and associativity of union | Bool |
| `A − B ≡ A ∩ complement(B)` on bounded cases | Bool |
| Solved sketch has DOF 0 and full-rank Jacobian | Sketch |
| Re-solving a solved sketch is a no-op | Sketch |
| Incremental rebuild == full rebuild | Feat |
| Parameter round-trip is bit-identical | Feat |
| Mesh of a closed solid is watertight | Tess |
| Mesh volume → solid volume as `chord_tol → 0` | Tess |
| `save→load→save` is byte-identical | Doc |

Property tests are the highest-value tier because they find bugs nobody thought
to write a case for, and because they are the tests that stay meaningful as the
implementation changes underneath them.

### 10.2 Tier 2 — Unit Tests

Per-function, per-library, in `test/unit/<lib>/`. Deterministic, fast, no I/O
beyond fixtures. Each public function needs at minimum: nominal case, boundary
case, degenerate case, and error case.

Output is TAP-like for machine parsing:

```
ok 1 - Num_Orient3D coplanar returns 0
ok 2 - Num_Orient3D antisymmetry over 24 permutations
not ok 3 - Geom_InvertSurface torus near-pole
  ---
  expected_u: 0.5000000000
  actual_u:   0.4999982341
  tolerance:  1.0e-9
  site:       Geom_InvertSurface
  ---
1..3
```

Structured failure output matters more than usual here, because agents consume
it. A bare "FAILED" gives an agent nothing to act on; expected/actual/tolerance/
site gives it enough to diagnose without a human in the loop.

### 10.3 Tier 3 — Golden Corpus

A fixed set of models and operations with checksummed expected results. Cheap,
fast regression detection across the whole kernel.

**Corpus A — canonical solids (~60).** Box, cylinder, sphere, cone, torus; each
at multiple scales spanning 1e-3 to 1e6 mm; thin-wall shells; high-genus solids
(2, 3, 5 holes); solids with tangent face pairs; solids with coincident faces;
a 500-face and a 10,000-face model for scale.

**Corpus B — operation pairs (~250).** For each pair: the two solids, the
operation, and expected volume, surface area, face/edge/vertex counts, genus,
and a geometry hash. Chosen to cover the hard cases deliberately:

| Category | Count | Examples |
|---|---|---|
| Disjoint | 20 | no contact at all |
| Simple overlap | 40 | box∩box, cyl∩box |
| Coincident faces | 40 | pad exactly on a face, flush cut |
| Tangent contact | 40 | sphere tangent to plane, cylinder tangent to cylinder |
| Edge-on-edge | 25 | shared edge exactly |
| Vertex-on-vertex | 15 | corner touching corner |
| Through-holes | 25 | cut fully through, cut exactly to wall |
| Near-degenerate | 30 | offsets 1e-6 to 1e-12 from exact coincidence |
| High face count | 15 | performance and stability |

**Corpus C — feature models (~40).** Full parametric trees exercising
regeneration and persistent naming: parameter edits, feature reorder, feature
delete, suppression, reference breakage.

Geometry hash: quantize all vertex positions to `linear/100`, sort
canonically, hash. Insensitive to entity ordering, sensitive to actual geometric
change. Ordering-insensitivity is essential — otherwise every internal
refactoring produces spurious corpus failures and the corpus gets ignored.

### 10.4 Tier 4 — OCCT Oracle (Offline)

OpenCascade generates reference results **once, offline**, committed as
fixtures. The kernel never links or invokes OCCT. This is exactly the
"reference, not dependency" position from v2, made operational.

Generated per corpus-B case: volume, surface area, face/edge/vertex count,
genus, bounding box, centroid, and inertia tensor.

Comparison tolerances: volume and area within `1e-6` relative; counts exact
where topology is unambiguous. Where OCCT and this kernel legitimately differ
(different but valid face partitioning of the same solid), the case is annotated
with the reason and only the invariant quantities — volume, area, genus,
bounding box — are compared. Face count is not a correctness criterion; volume
is.

A disagreement is investigated, never auto-accepted. OCCT is sometimes wrong,
and finding one of those is a good day — but the null hypothesis is that the new
kernel is wrong.

### 10.5 Tier 5 — Adversarial Fuzzing

**This is where kernels actually die**, and it is the tier best suited to
agents, which can grind through millions of cases without boredom.

```
cadk fuzz --seed N --ops M --op-set booleans
```

Deterministic from seed via `Num_RandU64`, so every failure reproduces exactly
from a seed and case index. A crash reproduced by `--seed 88412 --case 1907` is
a bug report an agent can act on directly.

**Generators:**

- *Random solids.* Random primitives at random transforms and scales, then
  random boolean sequences. The volume-conservation identity holds throughout,
  so every step is checkable without a reference.
- *Degeneracy walk.* Take a clean configuration; move one parameter toward exact
  degeneracy in decreasing steps (1e-3, 1e-6, 1e-9, 1e-12, exactly 0). The
  kernel must produce a correct result or a clean error at every step. This
  generator finds more real bugs than random generation, because it targets
  exactly the region where tolerance logic breaks.
- *Coplanar and tangent families.* Systematic enumeration of coincident and
  tangent configurations at every relative orientation.
- *Parameter storms.* Feature models with parameters swept through ranges
  including values that invalidate downstream features, verifying loud failure
  and clean recovery when the parameter is restored.
- *Malformed input.* Bit-flipped and truncated STEP/STL/DXF files; corrupt PG payloads rejected cleanly.

**Acceptance criteria for a fuzz run:**

| Outcome | Verdict |
|---|---|
| Correct result | pass |
| Clean error code (`CAD_E_NOCONVERGE`, `CAD_E_DEGENERATE`, …) | pass |
| `CAD_E_INTERNAL` | **fail** — invariant violated |
| Crash / segfault | **fail** |
| Hang (exceeds time budget) | **fail** |
| Invalid result reported as success | **fail** — worst class |
| Non-deterministic result across runs | **fail** |

The last two are the ones that matter most. A kernel that fails cleanly is
usable; a kernel that silently returns a wrong solid produces wrong parts.

### 10.6 Continuous Verification

Every commit: Tiers 1 and 2, plus corpus A. Target under 60 seconds.
Every merge: all tiers, full corpus, 10,000 fuzz cases. Target under 15 minutes.
Nightly: 10 million fuzz cases across all generators, with new failures
minimized to reproducers automatically.

**Coverage requirement:** every documented error code must be *reached* by at
least one test. An unreachable error path is either dead code or an untested
failure mode; both need finding.

### 10.7 Performance Baselines

Tracked from the start, because performance regressions found late get
attributed to the wrong change.

| Operation | Model | Budget |
|---|---|---|
| Boolean, simple | 100-face solids | < 50 ms |
| Boolean, complex | 5,000-face solids | < 5 s |
| Sketch solve | 200 entities, 400 constraints | < 100 ms |
| Full rebuild | 100-feature tree | < 10 s |
| Incremental rebuild | last feature of 100 | < 200 ms |
| Tessellation | 1,000 faces at 0.01 mm | < 2 s |
| Document load | 10 MB with cache | < 500 ms |

### 10.8 External Corpora and Prior-Art Harnesses

Do not build a model corpus by hand. Substantial public corpora exist, and the
two major open kernels have documented harness designs worth borrowing from.

#### What OCCT does

OCCT's primary regression suite is <cite index="18-1">DRAW Test Harness — Tcl scripts under `tests/`</cite>, driven by a console
application built on a <cite index="15-1">Tcl interpreter extended with OCCT-specific commands</cite>. <cite index="15-1">Tests are organized in three levels: group, grid, and case, with each case a Tcl script that runs DRAW commands and emits messages that can be checked for validity</cite>. <cite index="18-1">A GoogleTest-based C++ unit runner was added more recently, enabled with `-DBUILD_GTEST=ON`</cite>.

Three things are worth taking:

1. **The three-level group/grid/case hierarchy**, which produces compact tabular
   result reports — exactly what an agent workflow needs for triage.
2. **`testdiff`.** <cite index="18-1">Some results depend on the workstation and cannot be checked against predefined values; OCCT instead compares runs against a baseline from before a change</cite>. This is the right model for
   performance baselines (§10.7) and for cases where face partitioning is
   legitimately non-unique.
3. **The honest scoping admission.** OCCT's own developers note that <cite index="17-1">a complete unit-test database would be enormous, so functional tests are used instead, with few exceptions</cite>. Our Tier 1 property tests are the
   answer to the same pressure: they cover behavior without enumerating cases.

One thing **not** to take: <cite index="12-1">many OCCT test input files come from customers, are confidential, and are not distributed</cite>. Their corpus is
therefore not fully reproducible externally. Ours must be.

#### What FreeCAD does

<cite index="24-1">Two mechanisms: a Python `unittest` suite hooked into the Test Workbench, which can only test Python and Python-wrapped C++, and standalone GoogleTest executables for direct C++ testing</cite>.

The relevant lesson is a negative one, and it is the same lesson as §7.3
`CAD.Feat`. FreeCAD's topological naming tests live in
`tests/src/Mod/PartDesign/PartDesignTests/TestTopologicalNamingProblem.py`, and
their own issue tracker records the underlying difficulty plainly: testing Part
and PartDesign requires analyzing the resulting topology, which <cite index="26-1">is a tremendous undertaking that cannot be handled on a per-test basis</cite>, prompting a proposal for reusable
"comparators" that diff a result against a stored reference.

That comparator is our geometry hash (§10.3) plus `cadk diff`. Building it in
from day one, rather than retrofitting it after 20 years of hand-written
per-test assertions, is one of the few real advantages of starting clean.

Also worth noting: FreeCAD's TNP fix falls back to <cite index="21-1">geometry-based element search when element names are lost or changed, recovering references even when element maps are incomplete</cite>. That is stage 3 of our
resolution ladder (§7.3 `CAD.Feat`). The difference is our stage 4 — we refuse
to guess when the match is ambiguous, rather than silently accepting the nearest
candidate.

#### Public model corpora

| Corpus | Size | Format | Use here |
|---|---|---|---|
| **ABC** | <cite index="38-1">~1 million CAD models, each a collection of explicitly parametrized curves and surfaces</cite> | STEP | Primary STEP import stress corpus. <cite index="33-1">Construction history is discarded — final B-rep only</cite>, so it exercises import/validate/heal/tessellate, not the feature tree. |
| **Fusion 360 Gallery — Reconstruction** | <cite index="34-1">8,625 human-authored CAD programs in a sketch+extrude DSL, with modeling sequences, geometric and constraint parameters, and final geometry as B-rep, mesh, and STEP</cite> | JSON + STEP + OBJ | **The corpus-C replacement.** Real human feature trees with ground-truth results — exactly what `CAD.Feat` regeneration and persistent naming need. <cite index="35-1">Licensed for non-commercial research</cite>; verify terms before use. |
| **Fusion 360 Gallery — Segmentation** | <cite index="34-1">35,858 B-rep bodies, ~390,000 faces, each labeled with the modeling operation that created it (extrude side/end, cut, fillet, chamfer, revolve)</cite> | B-rep | **Persistent-naming ground truth.** Per-face operation provenance is precisely what `Feat_Pid.origin_kind` encodes — this dataset can validate the naming scheme directly. |
| **DeepCAD** | <cite index="33-1">Synthetically scaled sequences, same narrow operation set</cite> | JSON | Bulk regeneration fuzzing. |
| **Thingi10K** | ~10k meshes | STL | STL import robustness only. Not B-rep. |

**Caveat on all of them:** these are machine-learning datasets, curated for
learning tasks, not adversarial test suites. They are heavily weighted toward
clean, well-formed, sketch-and-extrude geometry. They will *not* contain the
coincident-face, tangent-contact, and near-degenerate configurations that break
booleans — which is exactly why corpus B (§10.3) is hand-constructed and the
degeneracy-walk fuzzer (§10.5) exists.

The right division of labor:

- **Corpus A/B (hand-built, ~310 cases)** — adversarial and degenerate. Where
  bugs actually are.
- **ABC subset (~5,000 models)** — STEP import, healing, tessellation at scale.
- **Fusion 360 Reconstruction (~8,600)** — feature-tree regeneration and
  persistent naming against real human design sequences.
- **Fusion 360 Segmentation** — direct validation of the provenance-naming scheme.
- **Fuzzers** — unbounded, targeted at degeneracy.

A pragmatic sequencing note: the external corpora all arrive through
`IO_ImportSTEP`, which is Phase 8. They are therefore unavailable for Phases
0–7, when they would be most useful. Bringing a **minimal STEP reader** forward
into Phase 3 — analytic surfaces and planar faces only, no B-splines, no
healing — unlocks thousands of real test models months earlier, at maybe 800
lines. Strongly recommended.

---

## 11. Implementation Phases

Ordered by dependency and by risk. **Risk is front-loaded deliberately**: the
intersection and boolean work starts as early as its dependencies allow, because
that is where schedule uncertainty lives. Finding out in month five that
surface/surface intersection is harder than expected is survivable; finding out
in month nine is not.

| Phase | Libraries | Exit criterion |
|---|---|---|
| **0. Foundation** | Sys, Num, Store | File I/O round-trips; predicates match arbitrary-precision reference; slabs detect stale handles |
| **1. Geometry** | Geom | All curve/surface types evaluate; derivatives match finite differences; inversion round-trips |
| **2. Topology** | Topo | Euler operators maintain all 8 invariants over 500 random sequences; corpus A constructs and validates |
| **3. Intersection** | Isect | All 15 analytic pairs exact; general marching passes sampled-deviation on corpus B; hard-case table green |
| **3b. Minimal STEP reader** *(parallel)* | IO (subset) | Analytic surfaces + planar faces only; unlocks external corpora for Phases 4–7 (§10.8) |
| **4. Boolean** | Bool | Corpus B passes; all algebraic identities hold; 1M fuzz cases clean |
| **5. Sketch** *(parallel from Phase 1)* | Sketch | Sketch corpus solves with correct DOF; diagnostics identify redundant sets; drag-stable |
| **6. Features** | Feat | Incremental == full on corpus C; reference-breaking scenarios fail loudly |
| **7. Output** | Tess, Doc | Watertight on corpus A; volume converges; document round-trip byte-identical |
| **8. Exchange** | IO | STEP round-trip preserves volume/area/counts on a public corpus; ABC subset imports and validates |
| **9. Repository** *(optional)* | Repo | Document put/get round-trip; revision history |

Phases 3 and 4 dominate the schedule. Any estimate that does not reflect that is
wrong. v2's "Boolean Ops: 3–4 weeks" was optimistic by a wide margin —
surface/surface intersection alone is the largest single body of work in the
kernel, which is why §7.3 splits it into its own library with its own test
harness.

No calendar estimates appear in this document. Exit criteria are objective and
testable; velocity against them is measurable once Phase 0 is running, and an
estimate made then will be worth more than one made now.

---

## 12. Agent Workflow

### 12.1 Contract Freeze

Before implementation begins, each library's interface is extracted into
`contracts/<lib>.ailang` containing signatures and `LinkagePool` definitions
only — no bodies. These files are the API. Implementations satisfy them;
they do not change them.

Amending a frozen contract requires: a stated reason, an entry in §13, and
notification to every agent whose library appears in the amended library's
dependent set. This is deliberately heavyweight. Contract churn is what breaks
parallel work.

### 12.2 One Agent, One Library

Each agent owns one library and works against frozen contracts for its
dependencies. It never reads or edits another library's implementation. If a
dependency is not yet implemented, it works against a stub that satisfies the
contract and returns `CAD_E_UNSUPPORTED`.

### 12.3 Definition of Done

A library is done when all of the following hold:

1. Every function in the frozen contract is implemented.
2. Every invariant in its spec is asserted in code at `-D2`.
3. Tier 2 unit tests cover nominal, boundary, degenerate, and error cases for
   every public function.
4. Its Tier 1 property tests pass.
5. Its portion of the golden corpus passes.
6. `-D0` (release), `-D1`, and `-D2` builds all pass all tests.
7. The may-call audit reports no violations.
8. No `CAD_E_INTERNAL` in a 100,000-case fuzz run touching the library.

### 12.4 Automated Audits

Mechanical checks, run in CI:

- **may-call audit.** Parse each source file for calls to `<Lib>_*` symbols;
  verify every referenced library is in the declared may-call list. Catches
  layering violations immediately, which is the failure mode most likely to
  emerge from parallel agent work.
- **private call audit.** `Lib__private` called only from within `Lib`.
- **raw array audit.** `ArrayGet`/`ArraySet` outside `CAD.Store` is a failure.
- **magic number audit.** Numeric literals in geometric code outside the allowed
  set flagged for review.
- **tolerance audit.** Comparison against a literal, or any epsilon not sourced
  from `Num_Tol`, is a failure.
- **nesting audit.** Expression nesting beyond 3 levels flagged (§5.1).
- **recursion audit.** Self-referential or mutually recursive call cycles in
  traversal code flagged (§5.2).

### 12.5 Prompt Skeleton

```
You are implementing CAD.<Lib> for the AILang CAD kernel.

READ FIRST:
  docs/CAD_Kernel_Design_v3.md  §3 (language constraints)
                                §4 (conventions)
                                §5 (coding standard)
                                §6 (tolerance — normative)
                                §7.3 CAD.<Lib> (your contract)
  contracts/<lib>.ailang        your frozen interface
  contracts/<dep>.ailang        for each dependency

CONSTRAINTS:
  - You may call ONLY: <may-call list>
  - Max 6 parameters per function
  - Expression nesting max 3 levels; name every intermediate
  - No recursion in traversals; use explicit Arrays stacks
  - No ArrayGet/ArraySet — use CAD.Store accessors
  - All tolerance comparisons via the §6.4 vocabulary
  - All topological decisions via §6.5 exact predicates
  - Errors are return codes; never invent a new one

DELIVERABLES:
  src/<lib>/*.ailang
  test/unit/<lib>/*.ailang   nominal + boundary + degenerate + error per function
  Invariant assertions at -D2 for every invariant in your spec

DONE WHEN: §12.3 criteria all pass.

TOOLING:
  The runtime exposes analyzer.x/LSP and call-graph queries as tools. Run the
  layering audit and the integer-op audit yourself before declaring done — do
  not leave them to CI. See §12.6.

If you need a function not in your may-call list, STOP and report it as a
design escalation. Do not work around it.
```

---

### 12.6 Tooling — What Enforces What

The audits in §12.4 are specified as rules, not as implementations. Where a rule
actually runs matters, because it determines whether an agent finds out about a
violation while it can still fix it cheaply, or after it has built more code on
top of the mistake.

Three enforcement tiers are available:

| Tier | Mechanism | Feedback latency |
|---|---|---|
| **Analyzer** | `analyzer.x` / LSP — dataflow, memory analysis, type propagation | Immediate, at the edit |
| **Graph** | Call-graph query over the visual code graph | On demand, whole-repo |
| **CI** | Text/AST scan in the build pipeline | At merge |

Agents do not invoke the toolchain directly. The MCP-capable agent runtime does,
which means every tier below is reachable *by an agent, mid-task*, as a tool
call. Audits therefore belong in the agent's loop, not only in the merge gate.

**Audit-to-mechanism mapping:**

| Audit (§12.4) | Best mechanism | Why |
|---|---|---|
| **Integer ops on `Real`** (§3.2) | **Analyzer** | This is dataflow, not text. The analyzer knows a value originated from `Float_Sqrt` and flows into `Add`. Text matching on the `_r` suffix is an approximation of the same question and will both miss cases and produce false positives. |
| **may-call layering** | **Graph** | "Does any edge point upward in the layer graph" is a graph query, not a grep. Also the one result worth *rendering*: after ten agents work independently, a human should be able to see at a glance whether §7.1 is still acyclic. |
| **Private call (`Lib__x`)** | Graph | Same call-graph traversal, different predicate. |
| **Raw `ArrayGet`/`ArraySet` outside `CAD.Store`** | CI | Pure symbol scan; no analysis needed. |
| **Tolerance literals** | Analyzer, CI fallback | Analyzer can trace whether a comparison's threshold originates from `Num_Tol`; CI can only catch bare literals. |
| **Magic numbers** | CI | Lexical. |
| **Expression nesting depth** | CI | AST-shape check. |
| **Recursion in traversals** | Graph | Cycle detection over the call graph. |
| **Stack depth / allocation pairing** | Analyzer | The memory analysis already does this class of check; `Allocate`/`Deallocate` size-match (§3) is exactly its shape. |

**The `Real` case is the important one.** §3.2's `_r` naming convention and
integer-op audit exist to compensate for the absence of a distinct float type.
An analyzer doing dataflow closes that gap properly: the convention degrades
from *load-bearing discipline* to *readability aid*, and the highest-risk bug
class in the project becomes a diagnostic at the point of writing rather than a
CI failure hours later. If the analyzer can be made to carry this check, do
that first — it is worth more than the rest of the audit list combined.

**Shorthand mode and the canonical form.** The editor may render and accept a
denser shorthand. The **committed file is always the explicit form**. Agents
read the repository, not the rendering — a shorthand-normalized file would
strip exactly the redundancy that makes the code auditable and that makes
generated diffs reviewable. Shorthand is an input and display convenience;
canonicalization to explicit form happens before commit. If the plugin can
enforce that on save, it should.

**Definition-of-done addendum.** §12.3 item 7 ("may-call audit reports no
violations") should be read as: the agent has run the layering and integer-op
audits through the runtime's tooling and both are clean — not that CI will catch
it later.

---

### 12.7 Coordination Substrate

Parallel agents need somewhere to put state that is neither chat history nor a
file in the repo. Chat history does not survive a session and cannot be queried;
files drift and nobody notices. The project-scoped Postgres context store
(`hc_projects` / `hc_sessions` / `hc_context` / `hc_tasks`) is the right home for
all of it, and this section maps the kernel's coordination needs onto it.

**Contracts live in `hc_symbols`.** §7.3 defines ~240 signatures. An agent
implementing `CAD.Bool` depends on four libraries; reading all four contract
files pulls the entire interface surface into context before any work starts.
Syncing `contracts/*.ailang` into `hc_symbols` turns that into
`op=sym_get name=Isect_SurfaceSurface` at the call site — pay per signature
used, not per library depended on. The contract files remain canonical in the
repo; the table is an index over them.

**Amendments are rows, not a markdown table.** §13 is specified below as a table
in this document, which is the same pattern that produces stale design docs
everywhere else. A contract amendment is a `kind=decision, scope=persistent`
row: it has an author, a timestamp, a link to what it superseded via
`archived_by`, and — critically — it is *queryable by the agent that is about to
violate it*. The markdown table in §13 should be treated as a rendering of those
rows, regenerated, never hand-edited.

**Escalations are handoff rows.** §12.2 tells an agent that discovers a missing
dependency to STOP and report a design escalation. That report is a
`kind=handoff` row naming the requesting library, the needed function, and the
justification. The orchestrator picks it up, decides, and either amends the
contract (a `decision` row) or rejects it — without ever replaying the
sub-agent's conversation.

**Per-library findings are `kind=finding`, `scope=project`.** The hard-won facts
that turn up during implementation — a degenerate case the spec missed, a
tolerance interaction between two libraries, a marching seed that diverges on
tori — belong here rather than in code comments where the next agent will not
find them.

**Tier routing.** The difficulty spread across this kernel is unusually wide,
which makes cost routing worth doing deliberately rather than defaulting
everything to flagship:

| Work | Suggested `min_tier` | Rationale |
|---|---|---|
| `CAD.Isect` marching, degenerate cases, seed finding | 1 | The genuinely hard mathematics. Do not economize here. |
| `CAD.Bool` classification and stitching | 1 | Correctness is subtle; failures are silent. |
| `CAD.Feat` persistent naming resolution | 1 | Design-sensitive; the loud-failure discipline is easy to erode. |
| `CAD.Sketch` solver core | 1–2 | Newton + rank analysis is standard but fiddly. |
| `CAD.Geom` NURBS evaluation | 2 | Well-documented algorithms, clear reference values. |
| `CAD.Topo` Euler operators | 2 | Mechanical once the radial-edge invariants are fixed. |
| `CAD.Num` `V3`/`Xf` helpers, `CAD.Store` accessors, `CAD.Sys` wrappers | 3 | Mechanical, tightly specified, property-tested. Thousands of lines. |
| Unit-test generation from contracts | 3 | Nominal/boundary/degenerate/error per function is a template. |

`hc_tasks` records `input_tokens`, `output_tokens`, and `cost_usd` per task, so
the routing guesses above are checkable rather than permanent. The diagnostic
that matters most here is average input tokens by task kind: high input on a
tier-3 task means too much context is being passed to a worker that did not need
it — usually a sign the contract for that library is not tight enough to stand
alone.

**Session shape.** One session per library, `role='sub:cad-<lib>'`, parented to
the orchestrator session. Definition of done (§12.3) is checked by the
orchestrator reading parked rows and audit-tool results — not by reading the
implementation.

---

## 13. Amendment Log

Contract changes after freeze are recorded as `kind=decision, scope=persistent`
context rows (§12.7). **The table below is a rendering of those rows and should
be regenerated, not hand-edited** — a hand-maintained log in a design document
drifts, which is the exact failure this project is trying to avoid elsewhere.

Each entry: date, library, what changed, why, and which dependent libraries were
notified.

| Date | Library | Change | Reason | Notified |
|---|---|---|---|---|
| 2026-08-05 | Product model | §1.4 Sketch_0 root, plane recipes, PG ordered tree, TNP policy | Freeze coordinate/dependency model before Feat/Sketch grind | Feat, Sketch, Repo, Geom, Topo, IO |
| 2026-08-14 | View / Sketch | §1.4 local X/Y/Z (ISO 841), A/B/C rotary; host sends orbit/pan/zoom only | Sketch-on-face must share the 3D camera; no U/V product labels | CAD_View, App.Draw, App.Ipc, Gtk handle |
| 2026-08-14 | View | Orientation cube is host chrome; `cam.txt` + `view0`–`view7` | Fusion/FreeCAD-style cube without Gtk owning camera math | CAD_View, App.Ipc, Gtk cube |
| — | — | *(contracts not fully frozen)* | — | — |

---

## Appendix A — Changes from v2.0

| Area | v2.0 | v3.0 | Why |
|---|---|---|---|
| GUI | Qt bindings, QML, OpenGL, ~2,300 lines | Removed entirely | Out of scope; requires FFI |
| FFI | C shim for Qt | None anywhere | Pure AILang over syscalls |
| Persistence | SQLite as runtime state and file format | In-memory arena + **Postgres SoR** + STEP/STL/DXF interchange; no `.cadx` | SQLite needs FFI; query-per-lookup is fatal in boolean loops; proprietary files reinvent the DB |
| SQL schema | Full topology relationally, ~15 tables | 5-table repository schema; topology is a cached blob | Topology is derived data — version the source, not the IR |
| Topology | Half-edge | **Radial edge** | Half-edge cannot represent non-manifold boolean intermediates |
| Numeric layer | Absent | `CAD.Num`, 3,000–4,500 lines, exact predicates | Robustness foundation; did not exist in v2 |
| Tolerance | Not addressed | Normative §6, per-entity tolerance, widening rule | Nearly every hard kernel bug is a tolerance bug |
| Intersection | Inside `CAD.Boolean` | Separate `CAD.Isect`, 6,000–9,000 lines | Larger than Boolean; independently testable |
| Persistent naming | A table with no algorithm | Generative provenance + 4-stage resolution + loud failure | The reason parametric models break |
| File reading | Assumed available | `CAD.Sys` implements it over syscalls | `ReadTextFile` is unimplemented in the current build |
| Testing | Not addressed | 5 tiers, corpora, oracle, fuzzing | Required for parallel agent development |
| Error handling | Unspecified | 19 status codes + error context pool | Every fallible path needs a defined outcome |
| Traversal | Unspecified | Explicit stacks mandated | 8 MB stack; recursive traversal overflows in the field |
| Inline assembly | Not considered | Available, but not needed — `Float_FMA` covers exact two-product. Policy and guardrails in §5.6 if used later |
| Test corpora | Not addressed | External corpora identified (§10.8); minimal STEP reader pulled forward to Phase 3b |
| Audit enforcement | Not addressed | Mapped to analyzer / call-graph / CI, reachable by agents as MCP tools (§12.6) |
| Float semantics | `Real` assumed a type | `Real` is a documentation alias for an `Integer` bit pattern; `Float_*` call form mandatory; integer-op audit added (§3.2) |
| Timeline | 10–14 weeks | Phases with objective exit criteria, no calendar | v2 estimate understated Phases 3–4 by a large factor |

## Appendix B — Deferred

Explicitly out of v3 scope, listed so they are not silently forgotten and so
their eventual arrival does not require re-architecting:

- Fillet and chamfer (needs offset surfaces and variable-radius blending —
  substantial work; the feature type is reserved in `Feat_Type`)
- Draft and shell/hollow operations
- Assemblies and mates (`CAD.Repo` schema anticipates them via `reference`)
- Direct/synchronous modeling (push-pull on faces without a feature tree)
- Surface modeling (loft, sweep along path, boundary surface)
- Mesh-to-B-rep reverse engineering
- Multi-threading (design implication: no global mutable state outside
  `FixedPool` singletons that are explicitly documented as single-threaded, so
  this stays possible)
- GPU tessellation and display
- All GUI

## Appendix C — Reference Reading

Not dependencies. Sources for algorithms.

- Shewchuk, *Adaptive Precision Floating-Point Arithmetic and Fast Robust
  Geometric Predicates* — §6.5 predicates
- Weiler, *The Radial Edge Structure* — §7.3 CAD.Topo
- Hoffmann, *Geometric and Solid Modeling* — boolean classification
- Patrikalakis & Maekawa, *Shape Interrogation for Computer Aided Design and
  Manufacturing* — §7.3 CAD.Isect, the single most useful reference for surface
  intersection
- Piegl & Tiller, *The NURBS Book* — §7.3 CAD.Geom
- Mäntylä, *An Introduction to Solid Modeling* — Euler operators
- Shewchuk, *Delaunay Refinement Algorithms for Triangular Mesh Generation* —
  §7.3 CAD.Tess

---

*Document version 3.0 — Core Engine, GUI-free, FFI-free*
*Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering*
