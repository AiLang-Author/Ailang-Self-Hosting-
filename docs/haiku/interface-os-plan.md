# Plan: Haiku as an interface OS

Status: draft, 2026-11-05. Direction only. A proper evaluation of the
system (phase 1) will settle the details this plan leaves out on
purpose.

Prerequisite: HalCode runs natively on Haiku
(`HalCode-Haiku/docs/haiku-native-plan.md`). It is the working tool for
everything below.

## 1. Goal

Turn Haiku into a system of interfaces instead of linked libraries:

- No dynamic linking for system code. Every program talks to system
  services through defined interfaces, not by loading shared libraries
  into its own address space.
- The Be API stays. It becomes a published interface, not a machine
  linked into every app. Existing apps keep working.
- System modules are rewritten in AILang one at a time. Each module is
  replaced only when it matches the original's behavior.
- Geometry and UI move from floating point to one 64-bit fixed-point
  integer format.
- The result is smaller and easier to audit. The size target is
  measured against the phase 1 baseline, not assumed.

## 2. Principles

1. **One module at a time.** At every point the system boots and runs,
   with a mix of old and new parts.
2. **Parity first.** Before a module is rewritten, it gets a test suite
   that the original passes. The replacement must pass the same suite.
3. **Each module is touched once.** Floats are removed, interfaces
   adopted and linking dropped in the same rewrite, not in separate
   passes over the C++ code.
4. **Generate the code, don't hand-write it.** Interface code, ABI
   layouts and boundary stubs are generated from one definition, and
   facts about Haiku are extracted from Haiku itself. This is how the
   syscall layer already works.
5. **Measure before cutting.** Size and code-count claims are checked
   against the phase 1 numbers.

## 3. Target architecture

```
  legacy C++ app            new AILang app
        │                          │
  compat libbe (C++ ABI)           │  static binary, no loader
        │                          │
        └──────────┬───────────────┘
                   ▼
        interface layer (generated)
   in-process: LinkagePool slot tables
   cross-process: port messages
                   │
                   ▼
   system services (AILang, integer-only)
   app_server, registrar, input, media, ...
                   │
                   ▼
              Haiku kernel
```

### 3.1 Interfaces

- One definition per interface, written as AILang `LinkagePool`s.
  - Slot order is the ABI: append only, never reorder.
  - `Direction=Input` and `Direction=Output` fields define what a
    request carries and what its reply carries.
- From that definition the generator produces:
  1. slot pools and dispatch code for AILang callers;
  2. message encoding over kernel ports for calls between processes;
  3. C++-compatible vtables and object layouts (Itanium ABI) for the
     compat layer;
  4. boundary stubs for C++ callers, including the float conversion
     (section 4);
  5. layout tests that check the generated offsets and sizes against
     Haiku's real headers.
- The generator is the only "runtime". Each app carries a thin,
  generated client stub, not a shared library.

### 3.2 Dynamic linking

- New and rewritten programs are static AILang binaries. They need no
  `runtime_loader`, no library search path and no symbol resolution.
- Prebuilt legacy apps still expect `libbe.so` and `libroot.so`. A
  compatibility libbe keeps the C++ layouts and forwards every call to
  the interfaces. These apps keep using the loader until they are
  rebuilt or replaced.
- The end state is a loader used only by legacy apps, which can be
  removed from a system that has none.
- Removing the loader rules out whole classes of attack: library
  preloading, search-path hijacking, symbol interposition, and one
  patched copy of a library while another vulnerable copy is still
  loaded. Every call through an interface also has a single place
  where its arguments are checked.

## 4. Numeric model

- **Geometry and UI use 64-bit integers with 16 fractional bits
  ("48.16").** This covers coordinates, rectangles, transforms, pen
  sizes, font metrics and layout.
  - Precision is 1/65536 of a unit, and the range is about ±1.4×10^14.
  - Add, subtract and compare are integer instructions. A multiply is
    `imul` followed by a shift. The pixel index is `x >> 16`.
  - Results are exact and repeatable, with no rounding drift between
    machines or builds.
- **Floats stay where the problem is floating point:**
  - audio samples and DSP (the Media Kit's float32 format);
  - JavaScript numbers (doubles by definition);
  - OpenGL and Mesa;
  - libm and applications' own math.
- **At the legacy boundary,** C++ callers still pass floats. The
  generated stub converts them to 48.16 once on the way in, and back
  on the way out. Nothing behind the boundary sees a float.
- **A native integer API** is published alongside the float API for new
  apps. The float API remains for compatibility.
- **Fixed-point math library.** Multiply and divide with correct
  rounding, square root, and trigonometry for rotations, transforms and
  arcs (lookup tables or CORDIC). AILang's fixed-point backend is the
  starting point.

## 5. Phases

Each phase ends when its gate passes. Phase 1 can change the order or
scope of the later phases.

### Phase 1: evaluate the system

Measure the installed system and the source tree:

- code size and binary size per component: kernel core, drivers,
  filesystems, network stack, kits, servers, bundled third-party
  libraries, apps;
- the shared-library dependency graph, and which exported symbols each
  app actually uses;
- where floats appear: public APIs, internal protocols (such as the
  `app_server` `AS_*` messages), and internal code;
- the existing protocols between apps and servers, and how complete
  each one is;
- how stable the syscall numbering is across Haiku builds, and whether
  the fork can freeze it.

Gate: an evaluation report with a baseline size table, a ranked list of
modules to replace, and the decisions this plan defers.

### Phase 2: interface definition and generator

1. Define the interface format on top of `LinkagePool`.
2. Build the generator described in section 3.1.
3. Proof test: a two-slot interface implemented in AILang and called
   from a small C++ program on Haiku through its vtable. One slot takes
   a `BRect` by value, to prove the float boundary stub.

Gate:
- the proof test passes on Haiku;
- the generated layout tests match Haiku's headers;
- the cross-process form of the same interface passes the same tests.

### Phase 3: shared contracts and numbers

1. Fix the 48.16 format and its rounding rules system-wide.
2. Build the fixed-point math library.
3. Define version 2 of the `app_server` client protocol in 48.16 as an
   interface definition. Version 1 stays supported through the
   boundary.
4. Define interface definitions for the other servers that phase 1
   ranked first.

Gate:
- the math library agrees with a float reference within a stated
  tolerance across a fixed test set;
- the protocol definitions compile through the generator.

### Phase 4: compatibility layer

Build the compat libbe:
- C++ class layouts and vtables come from the generator.
- Every method forwards to an interface.
- Float conversion happens in its boundary stubs.

Gate:
- a set of unmodified legacy Haiku apps (chosen in phase 1) runs on the
  compat layer with no visible change;
- the layout tests pass for every class in it.

### Phase 5: replace modules one at a time

Order: leaf services first, then kits, then the core servers. Phase 1
ranks the modules. For each module:

1. Write the parity suite and run it against the original.
2. Write the AILang replacement: integer-only, interface-based, static.
3. Swap it in, then run its own parity suite, the system regression
   suite and the legacy app set.
4. Keep the original available to roll back to until the next module
   is done.

Gate per module: all three test sets pass, and its size is recorded
against the baseline.

### Phase 6: window system

Rebuild `app_server` last among the servers, using the AOS display
design (`docs/display/`):
- a fixed-point rasterizer in place of AGG;
- protocol version 2 for native apps, and version 1 through the
  boundary for legacy apps.

Gate:
- the legacy app set renders correctly, compared against screenshots
  from the old server at the pixel level, within the stated
  anti-aliasing tolerance;
- native apps run on protocol version 2.

### Phase 7: remove dynamic linking from the system

- All system components are static AILang binaries.
- `runtime_loader` and the shared libraries remain only for legacy apps.
- They can be left out of a build that has no legacy apps.

Gate: a system image with no legacy apps boots and runs with no loader
and no shared libraries.

### Phase 8: shrink the kernel

- Use the phase 1 numbers to decide what moves out of the kernel:
  drivers, filesystems and network pieces become user-space services
  behind interfaces, where that saves code or reduces risk.
- Rewrite core kernel parts in AILang last, one subsystem at a time,
  with the same parity rule.
- Report the kernel and system size reduction against the phase 1
  baseline.

Gate: each moved or rewritten subsystem passes its parity suite, and
the system passes the full regression suite.

## 6. Verification throughout

- **Parity suites** per module, kept permanently as regression tests.
- **Layout tests** from the generator, run against every Haiku header
  update.
- **Legacy app set:** chosen in phase 1, run after every swap.
- **Size table:** updated after every phase and compared with the
  baseline.
- **Toolchain checks:** the compiler byte sweep and the self-host check
  (from the native HalCode plan) stay green throughout.

## 7. Risks

| Risk | Mitigation |
|---|---|
| C++ ABI details: layouts, reserved slots, virtual destructors, by-value floats | Generated layouts and stubs, checked against real headers by layout tests |
| Fixed-point rendering differs from float rendering | Stated tolerance, pixel comparison against the old server in phase 6 |
| Legacy apps rely on undocumented behavior | Real legacy app set as a gate, not only API tests |
| Syscall numbers drift between Haiku builds | Keep extracting from `libroot.so`, or freeze the numbering in the fork (decided in phase 1) |
| The rewrite stalls with the system half converted | Every phase leaves a working system; the original stays available until its replacement passes |
| Upstream Haiku keeps moving | Decide in phase 1 whether to track upstream or freeze on a fork baseline |

## 8. Decisions deferred to phase 1

- The order of module replacement.
- Which kernel subsystems move to user space, and which stay.
- Whether to track upstream Haiku or freeze on a fork.
- Whether the syscall numbering gets frozen.
- The legacy app set used as a gate.
- Where the 48.16 rounding rules need exceptions, if anywhere.
