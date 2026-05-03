# AILang Compiler — 05: Output Layer (ELF Construction)

## Overview

The output layer constructs a valid ELF64 executable from the code and data buffers produced by the emit layer. It writes an ELF header, program headers, code section, and data section — producing a binary that can be directly executed on Linux x86-64.

```
Emit.code (raw bytes) ──┐
                         ├──▶ ELF_Build() ──▶ ELF buffer ──▶ Output_WriteExecutable() ──▶ file.x
Emit.data (raw bytes) ──┘
```

---

## 1. CELFTYPES — ELF Constants (10KB)

### 1.1 ELF State
```
FixedPool.ELF {
    buffer, buffer_size, buffer_capacity   — output buffer
    base_addr, entry_addr, text_addr, data_addr
    text_offset, text_size, data_offset, data_size
    bss_size
    phdr_count, shdr_count
    shstrtab, shstrtab_size
    error, error_msg
}
```

### 1.2 Magic & Identification
```
ELFMagic: MAG0=0x7F, MAG1='E', MAG2='L', MAG3='F'
ELFClass: CLASS64=2
ELFData: LSB=1 (little-endian)
ELFVersion: CURRENT=1
ELFOSABI: NONE=0
```

### 1.3 Header Constants
```
ELFType: EXEC=2 (executable)
ELFMachine: X86_64=62 (0x3E)
ELFHdr.SIZE=64
PHdr.SIZE=56
SHdr.SIZE=64
```

### 1.4 Program Header Types & Flags
```
PHType: LOAD=1, DYNAMIC=2, INTERP=3, NOTE=4, PHDR=6
PHFlags: X=1, W=2, R=4, RX=5, RW=6
```

### 1.5 Defaults
```
ELFDefault.BASE_ADDR=0x400000  (4MB base)
ELFDefault.PAGE_SIZE=4096
```

---

## 2. CELFBuilder — ELF64 Construction (16KB)

### 2.1 Lifecycle
```
ELF_Init() → void
    Allocate output buffer (64KB initially)
    Set base address (0x400000)
    Allocate section header string table (256 bytes)

ELF_Free() → void
    Deallocate buffer and string table
```

### 2.2 Buffer Operations
```
ELF_WriteByte(b) → void
    Write byte to ELF buffer, auto-grow if needed

ELF_WriteWord(w) → void
    Little-endian 16-bit

ELF_WriteDWord(d) → void
    Little-endian 32-bit

ELF_WriteQWord(q) → void
    Little-endian 64-bit

ELF_WriteBytes(ptr, count) → void
    Copy raw bytes to buffer

ELF_WriteZeros(count) → void
    Write count zero bytes (padding)

ELF_Align(alignment) → void
    Pad to next alignment boundary with zeros
```

### 2.3 ELF Header (64 bytes)
```
ELF_WriteHeader(entry, phoff, shoff, phnum, shnum, shstrndx) → void
    Bytes 0-3:    Magic 7F 45 4C 46
    Byte 4:       Class = 2 (64-bit)
    Byte 5:       Data = 1 (little-endian)
    Byte 6:       Version = 1
    Byte 7:       OS/ABI = 0 (System V)
    Bytes 8-15:   Padding (zeros)
    Bytes 16-17:  Type = 2 (ET_EXEC)
    Bytes 18-19:  Machine = 62 (x86-64)
    Bytes 20-23:  Version = 1
    Bytes 24-31:  Entry point address
    Bytes 32-39:  Program header offset
    Bytes 40-47:  Section header offset (0 = none)
    Bytes 48-51:  Flags = 0
    Bytes 52-53:  ELF header size = 64
    Bytes 54-55:  Program header entry size = 56
    Bytes 56-57:  Program header count
    Bytes 58-59:  Section header entry size = 64
    Bytes 60-61:  Section header count = 0
    Bytes 62-63:  Section header string table index = 0
```

### 2.4 Program Headers (56 bytes each)
```
ELF_WriteProgramHeader(type, flags, offset, vaddr, filesz, align) → void
    Bytes 0-3:   Type
    Bytes 4-7:   Flags
    Bytes 8-15:  Offset in file
    Bytes 16-23: Virtual address
    Bytes 24-31: Physical address (= virtual)
    Bytes 32-39: File size
    Bytes 40-47: Memory size (= file size)
    Bytes 48-55: Alignment

Emitted headers:
    PT_LOAD for .text:  type=LOAD(1), flags=RX(5)
                         offset=text_offset, vaddr=base+text_offset
    PT_LOAD for .data:  type=LOAD(1), flags=RW(6)
                         offset=data_offset, vaddr=base+data_offset
```

### 2.5 Main Build Function
```
ELF_Build(code, code_size, data, data_size) → Integer
    Step 1: Calculate layout
        elf_hdr_size = 64
        phdr_offset = 64
        phdr_count = 2 (text + data)
        phdr_total = 2 * 56 = 112
        text_offset = 64 + 112 = 176
        text_offset_aligned = align16(176)
        data_offset = text_offset + code_size
        data_offset_aligned = page_align(data_offset)

    Step 2: Calculate virtual addresses
        text_vaddr = base + text_offset_aligned
        data_vaddr = base + data_offset_aligned
        entry_vaddr = text_vaddr

    Step 3: Apply data relocations
        Emit_SetBaseAddresses(text_vaddr, data_vaddr)
        Emit_ApplyDataRelocations()

    Step 4: Write ELF header
        ELF_WriteHeader(entry_vaddr, phdr_offset, 0, 2, 0, 0)

    Step 5: Write program headers
        ELF_WriteProgramHeader(LOAD, RX, text_offset, text_vaddr, code_size, 4096)
        ELF_WriteProgramHeader(LOAD, RW, data_offset, data_vaddr, data_size, 4096)

    Step 6: Pad to text offset with zeros

    Step 7: Write code bytes

    Step 8: Pad to data offset (page-aligned) with zeros

    Step 9: Write data bytes

    Returns 1 on success

ELF_BuildFromEmit() → Integer
    Convenience: calls ELF_Build(Emit.code, Emit.code_size, Emit.data, Emit.data_size)
```

### 2.6 Output Functions
```
ELF_GetBuffer() → Address
    Return ELF.buffer pointer

ELF_GetSize() → Integer
    Return ELF.buffer_size

ELF_WriteFile(filename) → Integer
    Open file for writing (O_WRONLY|O_CREAT|O_TRUNC=577, mode 0755=493)
    Write ELF.buffer contents
    Close file
    Return 1 on success

ELF_AddString(str) → Integer
    Add string to section header string table
    Return offset
```

---

## 3. COUTPUT — High-Level Output (7KB)

### 3.1 File Flags & Modes
```
FileFlags:
    O_RDONLY=0, O_WRONLY=1, O_RDWR=2
    O_CREAT=64, O_TRUNC=512, O_APPEND=1024
    WRITE_NEW=577 (O_WRONLY|O_CREAT|O_TRUNC)

FileMode:
    EXEC=493 (0755), RW=420 (0644), PRIVATE=384 (0600)
```

### 3.2 Output Functions
```
Output_WriteExecutable(filename) → Integer
    Open file with WRITE_NEW flags and EXEC mode
    Write ELF buffer to file
    Close file
    Return success

Output_WriteBinary(filename, code, code_size) → Integer
    Write raw code bytes (no ELF header)

Output_WriteData(filename, data, data_size) → Integer
    Write raw data bytes

Output_BuildAndWrite(filename) → Integer
    Convenience: ELF_Init() → ELF_BuildFromEmit() → Output_WriteExecutable() → ELF_Free()

Output_DumpCode(max_bytes) → void
    Print hex dump of Emit.code for debugging

Output_PrintStats() → void
    Print: code_size, data_size, labels, fixups, symbols, instructions
```

---

## 4. OUTPUT LAYOUT DIAGRAM

```
Final ELF file layout:
┌────────────────────────────────────────────┐  offset 0
│  ELF Header (64 bytes)                     │
├────────────────────────────────────────────┤  offset 64
│  Program Header 1: PT_LOAD .text (56 bytes)│
│    type=LOAD, flags=RX, vaddr=0x4000B0     │
├────────────────────────────────────────────┤  offset 120
│  Program Header 2: PT_LOAD .data (56 bytes)│
│    type=LOAD, flags=RW, vaddr=0x401000     │
├────────────────────────────────────────────┤  offset 176 (0xB0)
│  ...padding zeros to 16-byte align...      │
├────────────────────────────────────────────┤  offset 176+ (0xB0+)
│  .text section (code)                      │
│    [beginning at virtual 0x4000B0]         │
│    Raw x86-64 machine code                 │
├────────────────────────────────────────────┤  page-aligned
│  ...padding zeros to page boundary...      │
├────────────────────────────────────────────┤  page boundary (0x1000)
│  .data section (data)                      │
│    [beginning at virtual 0x401000]         │
│    String literals, constants              │
└────────────────────────────────────────────┘

Total file: 4096 + code_size + (padding) + data_size bytes
```

---

## 5. DATA RELOCATION FLOW

The compiler emits data section addresses as placeholder values (offset 0) when compiling string literals. These are patched after ELF layout is calculated.

```
1. Compile time: Emit_MovRsiImm64(0)     // placeholder
                 Emit_AddDataReloc(position, data_offset)

2. ELF build:    Emit_SetBaseAddresses(code_vaddr, data_vaddr)
                 Emit_ApplyDataRelocations()

3. Patching:     For each data reloc:
                   final_addr = data_vaddr + data_offset
                   PatchQWord(code_position, final_addr)
```

---

*Document 05 of 10 — Output Layer*
