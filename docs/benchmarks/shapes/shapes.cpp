// Casey Muratori listings 22-27 and 32-36, plus the f64 layout AILANG uses.
// g++ -O3 -fno-devirtualize -fno-tree-vectorize -fno-unroll-loops
// so a virtual call stays indirect, a switch stays a switch, and the
// x4 kernels are the only unrolls. Inlining stays on.

#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <new>

using f32 = float;
using f64 = double;
using u32 = uint32_t;
using u64 = uint64_t;

static const f32 Pi32 = 3.14159265358979323846f;
static const f64 PI = 3.141592653589793;
static const f64 HALF = 0.5;
static const f64 ONE = 1.0;

enum { MAXN = 4096 };

static int g_n = 0;
static int g_reps = 1;
static int g_hot = 1;
static volatile u64 g_sink = 0;

static u64 nowns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (u64)ts.tv_sec * 1000000000ull + (u64)ts.tv_nsec;
}

// The row is written after the timed repetitions. The clock pair sits
// outside the shape loop, so the print is not part of the kernel time.
static void report(const char *name, u64 ns, u64 sum_bits) {
    const char *tier = g_hot ? "hot" : "cold";
    std::printf("ROW %s %d %s %llu %llu\n", tier, g_n, name,
                (unsigned long long)ns, (unsigned long long)sum_bits);
    g_sink += sum_bits;
}

static u64 bits64(f64 x) {
    u64 b = 0;
    std::memcpy(&b, &x, 8);
    return b;
}

static u64 bits32(f32 x) {
    u32 b = 0;
    std::memcpy(&b, &x, 4);
    return b;
}

// ---------------------------------------------------------------------------
// f64 record. 24 bytes. Same bytes AILANG stores.
// ---------------------------------------------------------------------------

struct Shape64 {
    u64 type;
    f64 w;
    f64 h;
};

static_assert(sizeof(Shape64) == 24, "AILANG record is 24 bytes");

static Shape64 g_s64[MAXN];

enum shape_type : u32 {
    Shape_Square = 0,
    Shape_Rectangle = 1,
    Shape_Triangle = 2,
    Shape_Circle = 3,
    Shape_Count = 4
};

struct shape_union {
    shape_type Type;
    f32 Width;
    f32 Height;
};

static_assert(sizeof(shape_union) == 12, "Casey record is 12 bytes");

static shape_union g_s32[MAXN];

// ---------------------------------------------------------------------------
// Listing 22. Virtual shapes. Objects live in a contiguous slab; the loop
// only has base pointers, which is the listing.
// ---------------------------------------------------------------------------

class shape_base {
public:
    shape_base() {}
    virtual f32 Area() = 0;
    virtual u32 CornerCount() = 0;
};

class square : public shape_base {
public:
    explicit square(f32 SideInit) : Side(SideInit) {}
    virtual f32 Area() { return Side * Side; }
    virtual u32 CornerCount() { return 4; }
private:
    f32 Side;
};

class rectangle : public shape_base {
public:
    rectangle(f32 WidthInit, f32 HeightInit) : Width(WidthInit), Height(HeightInit) {}
    virtual f32 Area() { return Width * Height; }
    virtual u32 CornerCount() { return 4; }
private:
    f32 Width, Height;
};

class triangle : public shape_base {
public:
    triangle(f32 BaseInit, f32 HeightInit) : Base(BaseInit), Height(HeightInit) {}
    virtual f32 Area() { return 0.5f * Base * Height; }
    virtual u32 CornerCount() { return 3; }
private:
    f32 Base, Height;
};

class circle : public shape_base {
public:
    explicit circle(f32 RadiusInit) : Radius(RadiusInit) {}
    virtual f32 Area() { return Pi32 * Radius * Radius; }
    virtual u32 CornerCount() { return 0; }
private:
    f32 Radius;
};

static shape_base *g_ptrs[MAXN];
static unsigned char g_slab[MAXN * 32];

static u32 g_rng = 1;

static u32 next_u32() {
    g_rng = g_rng * 1664525u + 1013904223u;
    return g_rng;
}

static void fill_all() {
    g_rng = 1;
    for (int i = 0; i < MAXN; i++) {
        u32 state = next_u32();
        u32 typ = (state >> 28) & 3u;
        u32 wint = 1u + ((state >> 16) & 15u);
        u32 hint = 1u + ((state >> 8) & 15u);
        if (typ == 0u || typ == 3u) hint = wint;

        g_s64[i].type = typ;
        g_s64[i].w = (f64)wint;
        g_s64[i].h = (f64)hint;

        g_s32[i].Type = (shape_type)typ;
        g_s32[i].Width = (f32)wint;
        g_s32[i].Height = (f32)hint;

        void *slot = g_slab + (size_t)i * 32;
        f32 w = (f32)wint;
        f32 h = (f32)hint;
        if (typ == 0u) g_ptrs[i] = new (slot) square(w);
        else if (typ == 1u) g_ptrs[i] = new (slot) rectangle(w, h);
        else if (typ == 2u) g_ptrs[i] = new (slot) triangle(w, h);
        else g_ptrs[i] = new (slot) circle(w);
    }
}

// ---------------------------------------------------------------------------
// Listing 23, 24, 26, 32-36. f32.
// ---------------------------------------------------------------------------

static f32 TotalAreaVTBL(u32 n, shape_base **shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) acc += shapes[i]->Area();
    return acc;
}

static f32 TotalAreaVTBL4(u32 n, shape_base **shapes) {
    f32 a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    u32 count = n / 4;
    while (count--) {
        a0 += shapes[0]->Area();
        a1 += shapes[1]->Area();
        a2 += shapes[2]->Area();
        a3 += shapes[3]->Area();
        shapes += 4;
    }
    return a0 + a1 + a2 + a3;
}

static f32 GetAreaSwitch(shape_union s) {
    f32 result = 0.0f;
    switch (s.Type) {
        case Shape_Square: result = s.Width * s.Width; break;
        case Shape_Rectangle: result = s.Width * s.Height; break;
        case Shape_Triangle: result = 0.5f * s.Width * s.Height; break;
        case Shape_Circle: result = Pi32 * s.Width * s.Width; break;
        case Shape_Count: break;
    }
    return result;
}

static f32 TotalAreaSwitch(u32 n, shape_union *shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) acc += GetAreaSwitch(shapes[i]);
    return acc;
}

static f32 TotalAreaSwitch4(u32 n, shape_union *shapes) {
    f32 a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    n /= 4;
    while (n--) {
        a0 += GetAreaSwitch(shapes[0]);
        a1 += GetAreaSwitch(shapes[1]);
        a2 += GetAreaSwitch(shapes[2]);
        a3 += GetAreaSwitch(shapes[3]);
        shapes += 4;
    }
    return a0 + a1 + a2 + a3;
}

static const f32 kAreaC[4] = {1.0f, 1.0f, 0.5f, Pi32};

static f32 GetAreaUnion(shape_union s) {
    return kAreaC[s.Type] * s.Width * s.Height;
}

static f32 TotalAreaTable(u32 n, shape_union *shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) acc += GetAreaUnion(shapes[i]);
    return acc;
}

static f32 TotalAreaTable4(u32 n, shape_union *shapes) {
    f32 a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    n /= 4;
    while (n--) {
        a0 += GetAreaUnion(shapes[0]);
        a1 += GetAreaUnion(shapes[1]);
        a2 += GetAreaUnion(shapes[2]);
        a3 += GetAreaUnion(shapes[3]);
        shapes += 4;
    }
    return a0 + a1 + a2 + a3;
}

static f32 CornerAreaVTBL(u32 n, shape_base **shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) {
        acc += (1.0f / (1.0f + (f32)shapes[i]->CornerCount())) * shapes[i]->Area();
    }
    return acc;
}

static u32 GetCornerCountSwitch(shape_type type) {
    u32 result = 0;
    switch (type) {
        case Shape_Square: result = 4; break;
        case Shape_Rectangle: result = 4; break;
        case Shape_Triangle: result = 3; break;
        case Shape_Circle: result = 0; break;
        case Shape_Count: break;
    }
    return result;
}

static f32 CornerAreaSwitch(u32 n, shape_union *shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) {
        acc += (1.0f / (1.0f + (f32)GetCornerCountSwitch(shapes[i].Type))) * GetAreaSwitch(shapes[i]);
    }
    return acc;
}

static const f32 kCornerC[4] = {
    1.0f / (1.0f + 4.0f),
    1.0f / (1.0f + 4.0f),
    0.5f / (1.0f + 3.0f),
    Pi32
};

static f32 CornerAreaTable(u32 n, shape_union *shapes) {
    f32 acc = 0.0f;
    for (u32 i = 0; i < n; i++) {
        acc += kCornerC[shapes[i].Type] * shapes[i].Width * shapes[i].Height;
    }
    return acc;
}

// ---------------------------------------------------------------------------
// f64 kernels. Names match the AILANG rows.
// ---------------------------------------------------------------------------

static f64 AreaIf(u64 typ, f64 w, f64 h) {
    if (typ == 0) return w * w;
    if (typ == 1) return w * h;
    if (typ == 2) return (HALF * w) * h;
    return (PI * w) * w;
}

__attribute__((noinline))
static f64 AreaIfCall(u64 typ, f64 w, f64 h) {
    if (typ == 0) return w * w;
    if (typ == 1) return w * h;
    if (typ == 2) return (HALF * w) * h;
    return (PI * w) * w;
}

static f64 AreaSwitch(const Shape64 &s) {
    switch (s.type) {
        case 0: return s.w * s.w;
        case 1: return s.w * s.h;
        case 2: return (HALF * s.w) * s.h;
        default: return (PI * s.w) * s.w;
    }
}

__attribute__((noinline))
static f64 AreaSwitchCall(const Shape64 &s) {
    switch (s.type) {
        case 0: return s.w * s.w;
        case 1: return s.w * s.h;
        case 2: return (HALF * s.w) * s.h;
        default: return (PI * s.w) * s.w;
    }
}

static const f64 kAreaD[4] = {1.0, 1.0, 0.5, PI};

static f64 AreaTable(const Shape64 &s) {
    return (kAreaD[s.type] * s.w) * s.h;
}

__attribute__((noinline))
static f64 AreaTableCall(const Shape64 &s) {
    return (kAreaD[s.type] * s.w) * s.h;
}

static u32 CornersOf(u64 typ) {
    switch (typ) {
        case 0: return 4;
        case 1: return 4;
        case 2: return 3;
        default: return 0;
    }
}

__attribute__((noinline))
static u32 CornersCall(u64 typ) {
    switch (typ) {
        case 0: return 4;
        case 1: return 4;
        case 2: return 3;
        default: return 0;
    }
}

static const f64 kCornerD[4] = {1.0 / 5.0, 1.0 / 5.0, 0.5 / 4.0, PI};

__attribute__((noinline))
__attribute__((noinline))
static f64 pass_loop_int(int n) {
    u64 acc = 0;
    for (int i = 0; i < n; i++) acc += g_s64[i].type;
    // Stash the integer in the bit slot by returning it through a side channel.
    return (f64)acc;
}

static u64 g_int_acc = 0;

__attribute__((noinline))
static f64 pass_loop_fadd(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + g_s64[i].w;
    return acc;
}

__attribute__((noinline))
static f64 pass_loop_fmul(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) {
        f64 prod = g_s64[i].w * g_s64[i].h;
        acc = acc + prod;
    }
    return acc;
}

__attribute__((noinline))
static f64 pass_area_if(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaIf(g_s64[i].type, g_s64[i].w, g_s64[i].h);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_if_call(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaIfCall(g_s64[i].type, g_s64[i].w, g_s64[i].h);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_switch(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaSwitch(g_s64[i]);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_switch_call(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaSwitchCall(g_s64[i]);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_table(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaTable(g_s64[i]);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_table_call(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) acc = acc + AreaTableCall(g_s64[i]);
    return acc;
}

__attribute__((noinline))
static f64 pass_area_table_x4(int n) {
    f64 a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    int groups = n / 4;
    for (int g = 0; g < groups; g++) {
        const Shape64 *s = g_s64 + g * 4;
        a0 = a0 + ((kAreaD[s[0].type] * s[0].w) * s[0].h);
        a1 = a1 + ((kAreaD[s[1].type] * s[1].w) * s[1].h);
        a2 = a2 + ((kAreaD[s[2].type] * s[2].w) * s[2].h);
        a3 = a3 + ((kAreaD[s[3].type] * s[3].w) * s[3].h);
    }
    return (a0 + a1) + (a2 + a3);
}

__attribute__((noinline))
static f64 pass_corner_call(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) {
        u32 corners = CornersCall(g_s64[i].type);
        f64 area = AreaSwitchCall(g_s64[i]);
        f64 weight = ONE / (f64)(corners + 1);
        acc = acc + (weight * area);
    }
    return acc;
}

__attribute__((noinline))
static f64 pass_corner_two(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) {
        u32 corners = CornersOf(g_s64[i].type);
        f64 area = AreaSwitch(g_s64[i]);
        f64 weight = ONE / (f64)(corners + 1);
        acc = acc + (weight * area);
    }
    return acc;
}

__attribute__((noinline))
static f64 pass_corner_one(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) {
        u64 typ = g_s64[i].type;
        f64 w = g_s64[i].w;
        f64 h = g_s64[i].h;
        u32 corners = 0;
        f64 area = 0;
        switch (typ) {
            case 0: corners = 4; area = w * w; break;
            case 1: corners = 4; area = w * h; break;
            case 2: corners = 3; area = (HALF * w) * h; break;
            default: corners = 0; area = (PI * w) * w; break;
        }
        f64 weight = ONE / (f64)(corners + 1);
        acc = acc + (weight * area);
    }
    return acc;
}

__attribute__((noinline))
static f64 pass_corner_table(int n) {
    f64 acc = 0;
    for (int i = 0; i < n; i++) {
        acc = acc + ((kCornerD[g_s64[i].type] * g_s64[i].w) * g_s64[i].h);
    }
    return acc;
}

__attribute__((noinline))
static f32 pass_f32_vtbl(int n) { return TotalAreaVTBL((u32)n, g_ptrs); }
__attribute__((noinline))
static f32 pass_f32_vtbl4(int n) { return TotalAreaVTBL4((u32)n, g_ptrs); }
__attribute__((noinline))
static f32 pass_f32_switch(int n) { return TotalAreaSwitch((u32)n, g_s32); }
__attribute__((noinline))
static f32 pass_f32_switch4(int n) { return TotalAreaSwitch4((u32)n, g_s32); }
__attribute__((noinline))
static f32 pass_f32_table(int n) { return TotalAreaTable((u32)n, g_s32); }
__attribute__((noinline))
static f32 pass_f32_table4(int n) { return TotalAreaTable4((u32)n, g_s32); }
__attribute__((noinline))
static f32 pass_f32_corner_vtbl(int n) { return CornerAreaVTBL((u32)n, g_ptrs); }
__attribute__((noinline))
static f32 pass_f32_corner_switch(int n) { return CornerAreaSwitch((u32)n, g_s32); }
__attribute__((noinline))
static f32 pass_f32_corner_table(int n) { return CornerAreaTable((u32)n, g_s32); }

template <typename Fn>
static void time_f64(const char *name, Fn fn) {
    f64 sum = 0;
    u64 t0 = nowns();
    for (int r = 0; r < g_reps; r++) sum = sum + fn(g_n);
    u64 t1 = nowns();
    report(name, t1 - t0, bits64(sum));
}

static void time_int() {
    u64 acc = 0;
    u64 t0 = nowns();
    for (int r = 0; r < g_reps; r++) {
        for (int i = 0; i < g_n; i++) acc += g_s64[i].type;
    }
    u64 t1 = nowns();
    g_int_acc = acc;
    report("loop-int", t1 - t0, acc);
}

template <typename Fn>
static void time_f32(const char *name, Fn fn) {
    f32 sum = 0;
    u64 t0 = nowns();
    for (int r = 0; r < g_reps; r++) sum = sum + fn(g_n);
    u64 t1 = nowns();
    report(name, t1 - t0, bits32(sum));
}

static void scrub() {
    constexpr size_t N = 32u * 1024u * 1024u;
    static unsigned char *buf = nullptr;
    if (!buf) buf = (unsigned char *)std::malloc(N);
    for (size_t i = 0; i < N; i += 64) {
        volatile unsigned char *p = buf + i;
        *p = (unsigned char)i;
    }
}

static void run_all() {
    time_int();
    time_f64("loop-fadd", pass_loop_fadd);
    time_f64("loop-fmul", pass_loop_fmul);
    time_f64("area-if", pass_area_if);
    time_f64("area-if-call", pass_area_if_call);
    time_f64("area-switch", pass_area_switch);
    time_f64("area-switch-call", pass_area_switch_call);
    time_f64("area-table", pass_area_table);
    time_f64("area-table-call", pass_area_table_call);
    time_f64("area-table-x4", pass_area_table_x4);
    time_f64("corner-call", pass_corner_call);
    time_f64("corner-two", pass_corner_two);
    time_f64("corner-one", pass_corner_one);
    time_f64("corner-table", pass_corner_table);
    time_f32("f32-vtbl", pass_f32_vtbl);
    time_f32("f32-vtbl4", pass_f32_vtbl4);
    time_f32("f32-switch", pass_f32_switch);
    time_f32("f32-switch4", pass_f32_switch4);
    time_f32("f32-table", pass_f32_table);
    time_f32("f32-table4", pass_f32_table4);
    time_f32("f32-corner-vtbl", pass_f32_corner_vtbl);
    time_f32("f32-corner-switch", pass_f32_corner_switch);
    time_f32("f32-corner-table", pass_f32_corner_table);
    (void)pass_loop_int;
}

int main() {
    fill_all();

    g_hot = 1;
    g_n = 256;
    g_reps = 200;
    run_all();
    g_n = 4096;
    g_reps = 200;
    run_all();

    scrub();
    g_hot = 0;
    g_n = 4096;
    g_reps = 1;
    run_all();
    return (int)(g_sink & 255u);
}
