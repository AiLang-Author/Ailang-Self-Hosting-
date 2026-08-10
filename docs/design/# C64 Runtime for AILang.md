# C64 Runtime for AILang

## Design Document v1.0

---

## Overview

The C64 Runtime is a **functional emulation** of the Commodore 64 computer, written entirely in AILang. Unlike cycle-accurate emulators (VICE, etc.), this implementation focuses on **functional correctness** - programs see the same behavior without emulating exact hardware timing.

### Design Philosophy

1. **Functional, not cycle-accurate**: Captures behavior, not timing
2. **Modular architecture**: Each chip is an independent library
3. **Framebuffer-based display**: Direct pixel output, no terminal tricks
4. **Extensible**: Easy to add features beyond original C64
5. **Educational**: Clean, readable code over micro-optimization

### What Works
- ~80% of games and software that don't rely on timing tricks
- All BASIC programs
- Assembly programs using standard I/O

### What Won't Work
- Demo scene effects (raster tricks, FLI, VSP)
- Software relying on exact cycle timing
- Some copy protection schemes

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        C64 Runtime                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────────────────────────────┐    │
│  │   CPU6502   │───▶│          C64Memory                  │    │
│  │             │◀───│  (Memory Bus + Address Routing)     │    │
│  │  - Registers│    │                                     │    │
│  │  - Flags    │    │  ┌───────┐ ┌───────┐ ┌───────────┐ │    │
│  │  - Stack    │    │  │64K RAM│ │ ROMs  │ │Color RAM  │ │    │
│  │  - All ops  │    │  └───────┘ └───────┘ └───────────┘ │    │
│  └─────────────┘    │                                     │    │
│                     │  Address Routing:                   │    │
│                     │   $0000-$9FFF → RAM                 │    │
│                     │   $A000-$BFFF → BASIC ROM / RAM     │    │
│                     │   $D000-$DFFF → I/O Chips           │    │
│                     │   $E000-$FFFF → KERNAL ROM / RAM    │    │
│                     └──────────────┬──────────────────────┘    │
│                                    │                           │
│            ┌───────────────────────┼───────────────────────┐   │
│            │                       │                       │   │
│            ▼                       ▼                       ▼   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐  │
│  │    C64VIC       │    │    C64SID       │    │  C64CIA   │  │
│  │  (Video Chip)   │    │  (Sound Chip)   │    │ (I/O Chip)│  │
│  │                 │    │                 │    │           │  │
│  │ $D000-$D3FF     │    │ $D400-$D7FF     │    │$DC00-$DDFF│  │
│  │                 │    │                 │    │           │  │
│  │ - Text mode     │    │ - 3 voices      │    │- Keyboard │  │
│  │ - Bitmap mode   │    │ - Filters       │    │- Joystick │  │
│  │ - Sprites (8)   │    │ - ADSR          │    │- Timers   │  │
│  │ - Colors        │    │                 │    │- Serial   │  │
│  └────────┬────────┘    └────────┬────────┘    └─────┬─────┘  │
│           │                      │                   │        │
│           ▼                      ▼                   ▼        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐  │
│  │  Framebuffer    │    │   Audio Output  │    │  Keyboard │  │
│  │  (/dev/fb0)     │    │   (future)      │    │  Input    │  │
│  └─────────────────┘    └─────────────────┘    └───────────┘  │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Library Reference

### Library.C64Memory.ailang

**Purpose**: Memory bus, address routing, banking control

**Key Functions**:
| Function | Description |
|----------|-------------|
| `C64Mem_Init()` | Allocate 64KB RAM, ROM areas, Color RAM |
| `C64Mem_Read(addr)` | Read byte with banking/routing |
| `C64Mem_Write(addr, val)` | Write byte with banking/routing |
| `C64Mem_Read16(addr)` | Read 16-bit word (little-endian) |
| `C64Mem_LoadPRG(filename)` | Load .PRG file into RAM |
| `C64Mem_LoadKernalROM(file)` | Load KERNAL ROM image |
| `C64Mem_LoadBasicROM(file)` | Load BASIC ROM image |
| `C64Mem_LoadCharROM(file)` | Load Character ROM image |

**Memory Map**:
```
$0000-$0001  6510 CPU Port (banking control)
$0002-$9FFF  RAM
$A000-$BFFF  BASIC ROM (banked) or RAM
$C000-$CFFF  RAM
$D000-$D3FF  VIC-II registers (mirrored)
$D400-$D7FF  SID registers
$D800-$DBFF  Color RAM (1K × 4 bits)
$DC00-$DCFF  CIA1 (keyboard, joystick)
$DD00-$DDFF  CIA2 (serial, VIC bank)
$DE00-$DFFF  I/O expansion
$E000-$FFFF  KERNAL ROM (banked) or RAM
```

**Banking** (controlled by $0001):
- Bit 0 (LORAM): BASIC ROM visible
- Bit 1 (HIRAM): KERNAL ROM visible  
- Bit 2 (CHAREN): I/O visible (vs Char ROM)

---

### Library.CPU6502.ailang

**Purpose**: MOS 6502/6510 CPU interpreter

**Key Functions**:
| Function | Description |
|----------|-------------|
| `CPU_Init()` | Reset all registers to default |
| `CPU_Reset()` | Read reset vector, jump to it |
| `CPU_SetPC(addr)` | Set program counter directly |
| `CPU_Step()` | Execute one instruction, return cycles |
| `CPU_Run(cycles)` | Execute until cycle count reached |
| `CPU_DumpState()` | Print register state for debugging |
| `CPU_StepTrace()` | Execute with disassembly output |

**Registers** (in `CPU` FixedPool):
- `A` - Accumulator (8-bit)
- `X` - X Index Register (8-bit)
- `Y` - Y Index Register (8-bit)
- `SP` - Stack Pointer (8-bit, stack at $0100-$01FF)
- `PC` - Program Counter (16-bit)

**Flags**:
- `F_CARRY` - Carry/Borrow
- `F_ZERO` - Result was zero
- `F_IRQ` - IRQ disable
- `F_DECIMAL` - BCD mode
- `F_OVERFLOW` - Signed overflow
- `F_NEGATIVE` - Result bit 7 set

**Addressing Modes Implemented**:
- Immediate (`LDA #$42`)
- Zero Page (`LDA $FB`)
- Zero Page,X/Y (`LDA $FB,X`)
- Absolute (`LDA $1234`)
- Absolute,X/Y (`LDA $1234,X`)
- Indirect (`JMP ($1234)`)
- Indexed Indirect (`LDA ($FB,X)`)
- Indirect Indexed (`LDA ($FB),Y`)
- Relative (branches)

**All 56 Official Opcodes**: ✓ Implemented

---

### Library.C64VIC.ailang

**Purpose**: VIC-II video chip functional emulation

**Key Functions**:
| Function | Description |
|----------|-------------|
| `VIC_Init()` | Initialize registers, allocate state |
| `C64VIC_Read(reg)` | Read VIC register (called by memory bus) |
| `C64VIC_Write(reg, val)` | Write VIC register |
| `VIC_RenderFrame()` | Render complete frame to framebuffer |
| `VIC_SetBorder(color)` | Set border color (helper) |
| `VIC_SetBackground(color)` | Set background color (helper) |
| `VIC_PrintAt(col, row, ch, color)` | Print char at position |
| `VIC_PrintString(col, row, str, color)` | Print string |
| `VIC_ClearScreen(ch, color)` | Clear screen memory |

**Register Map** ($D000-$D02E):
| Address | Name | Description |
|---------|------|-------------|
| $D000-$D00F | Sprite coords | X/Y for sprites 0-7 |
| $D010 | MSIGX | Sprite X MSB |
| $D011 | SCROLY | Y scroll, screen height, mode |
| $D012 | RASTER | Raster line counter |
| $D015 | SPENA | Sprite enable |
| $D016 | SCROLX | X scroll, screen width, multicolor |
| $D018 | VMCSB | Memory pointers |
| $D020 | EXTCOL | Border color |
| $D021-$D024 | BG colors | Background colors 0-3 |
| $D025-$D026 | SPMC | Sprite multicolor |
| $D027-$D02E | SP0COL-SP7COL | Sprite colors |

**Display Modes**:
- Text Mode (40×25 characters)
- Bitmap Mode (320×200 hi-res)
- Multicolor Mode (160×200)
- Extended Color Mode

**Sprite Support**:
- 8 hardware sprites
- 24×21 pixels each
- X/Y expansion (double size)
- Per-sprite colors
- Multicolor sprites (3 colors + transparent)

---

### Library.Framebuffer.ailang

**Purpose**: Direct Linux framebuffer access for graphics output

**Key Functions**:
| Function | Description |
|----------|-------------|
| `FB_Init()` | Open /dev/fb0, mmap display memory |
| `FB_InitDouble()` | Init with double buffering |
| `FB_Close()` | Cleanup and close |
| `FB_Clear(color)` | Fill screen with color |
| `FB_SetPixel(x, y, color)` | Set single pixel |
| `FB_Line(x1, y1, x2, y2, color)` | Bresenham line |
| `FB_Rect(x, y, w, h, color)` | Rectangle outline |
| `FB_FillRect(x, y, w, h, color)` | Filled rectangle |
| `FB_Circle(cx, cy, r, color)` | Circle outline |
| `FB_FillCircle(cx, cy, r, color)` | Filled circle |
| `FB_Blit(src, w, h, x, y)` | Copy image to screen |
| `FB_BlitScaled(src, w, h, x, y, scale)` | Scaled blit |
| `FB_FlipFast()` | Copy back buffer to screen |
| `FB_RGB(r, g, b)` | Create color value |
| `FB_C64Color(index)` | Get C64 palette color |
| `FB_DrawString(x, y, str, fg, bg)` | Draw text |

**Requirements**:
- Linux with `/dev/fb0` 
- Must run from console (Ctrl+Alt+F2), not X11
- User must be in `video` group or run as root

**Color Support**:
- 32-bit BGRA (most common)
- 24-bit BGR
- 16-bit RGB565

---

## Execution Flow

### Main Loop (Typical)

```ailang
SubRoutine.Main {
    // Initialize subsystems
    C64Mem_Init()
    CPU_Init()
    VIC_Init()
    FB_InitDouble()
    
    // Load C64 program
    load_addr = C64Mem_LoadPRG("game.prg")
    CPU_SetPC(load_addr)
    
    // Main loop
    running = 1
    WhileLoop EqualTo(running, 1) {
        // Execute ~20000 cycles (roughly 1 frame at 1MHz)
        CPU_Run(20000)
        
        // Render frame
        VIC_RenderFrame()
        
        // Handle input (check keyboard)
        // ... (via CIA1)
        
        // Check for quit condition
        // ...
    }
    
    // Cleanup
    FB_Close()
    VIC_Shutdown()
    C64Mem_Shutdown()
}
```

### Instruction Execution Flow

```
1. CPU_Step() called
2. Fetch opcode from Memory[PC]
3. PC incremented
4. Decode addressing mode
5. Fetch operands (may read memory)
6. Execute operation
7. Update flags
8. Return cycle count
```

### Memory Access Flow

```
1. CPU calls C64Mem_Read(addr) or C64Mem_Write(addr, val)
2. Memory bus checks address range
3. Routes to appropriate handler:
   - $0000-$9FFF: Direct RAM access
   - $A000-$BFFF: Check banking → ROM or RAM
   - $D000-$D3FF: VIC_Read/Write()
   - $D400-$D7FF: SID_Read/Write()
   - $D800-$DBFF: Color RAM
   - $DC00-$DCFF: CIA1_Read/Write()
   - $DD00-$DDFF: CIA2_Read/Write()
   - $E000-$FFFF: Check banking → ROM or RAM
4. Return value (read) or commit write
```

### Frame Rendering Flow

```
1. VIC_RenderFrame() called
2. Draw border color (full screen)
3. If display enabled:
   a. Draw background color (320×200 area)
   b. If text mode: VIC_RenderTextMode()
      - Loop 25 rows × 40 cols
      - Read screen RAM for character code
      - Read Color RAM for color
      - Read character bitmap from Char ROM/RAM
      - Draw 8×8 character scaled to framebuffer
   c. If bitmap mode: VIC_RenderBitmapMode()
      - Loop 25×40 cells
      - Read bitmap data (8 bytes per cell)
      - Read color data from screen RAM
      - Draw pixels scaled to framebuffer
   d. Render sprites (7 down to 0)
      - Check enable bit
      - Read sprite pointer from screen RAM
      - Read sprite data (63 bytes)
      - Draw 24×21 sprite scaled
4. FB_FlipFast() - copy back buffer to display
```

---

## C64 Color Palette

| Index | Color | RGB |
|-------|-------|-----|
| 0 | Black | (0, 0, 0) |
| 1 | White | (255, 255, 255) |
| 2 | Red | (136, 57, 50) |
| 3 | Cyan | (103, 182, 189) |
| 4 | Purple | (139, 63, 150) |
| 5 | Green | (85, 160, 73) |
| 6 | Blue | (64, 49, 141) |
| 7 | Yellow | (191, 206, 114) |
| 8 | Orange | (139, 84, 41) |
| 9 | Brown | (87, 66, 0) |
| 10 | Light Red | (184, 105, 98) |
| 11 | Dark Grey | (80, 80, 80) |
| 12 | Grey | (120, 120, 120) |
| 13 | Light Green | (148, 224, 137) |
| 14 | Light Blue | (120, 105, 196) |
| 15 | Light Grey | (159, 159, 159) |

---

## Future Enhancements

### CIA1 (Keyboard/Joystick)
- Keyboard matrix scanning
- Joystick port reading
- Timer interrupts

### CIA2 (System Control)
- VIC bank selection
- Serial bus (disk drive)
- User port

### SID (Sound)
- 3 oscillators (saw, triangle, pulse, noise)
- ADSR envelopes
- Filter
- Ring modulation

### Timing Improvements
- Use Linux `timerfd` or `nanosleep` for frame pacing
- Optional cycle-accurate mode using high-res timers

### Extended Features (Beyond C64)
- Higher resolutions
- More colors
- Larger sprites
- More RAM
- Enhanced BASIC commands

---

## Testing

### Console Tests (No Framebuffer)
```bash
./cpu_test.x    # Test CPU and memory
```

### Framebuffer Tests
```bash
# Switch to console: Ctrl+Alt+F2
sudo ./fb_test.x       # Test framebuffer drawing
sudo ./vic_test.x      # Test VIC rendering
sudo ./c64_run.x game.prg  # Run actual C64 program
```

---

## File Formats

### .PRG Format
Standard C64 program file:
- Bytes 0-1: Load address (little-endian)
- Bytes 2+: Program data

### ROM Files
- `basic.rom` - 8192 bytes, BASIC interpreter
- `kernal.rom` - 8192 bytes, KERNAL operating system
- `chargen.rom` - 4096 bytes, character bitmaps

---

## Dependencies

- AILang compiler (self-hosting)
- Linux x86-64
- `/dev/fb0` for graphics (console mode only)
- Optional: C64 ROM files for full compatibility

---

## License

Part of the AILang project.
Sean Collins Software License (SCSL)