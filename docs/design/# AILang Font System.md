# AILang Font System

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Library.Font.ailang                      │
│              (Unified Interface + Registry)                 │
├─────────────────────────────────────────────────────────────┤
│  Font_Init()          Font_Load(file)                       │
│  Font_DrawString()    Font_DrawChar()                       │
│  Font_GetHeight()     Font_GetCharWidth()                   │
│  Font_GetStringWidth()                                      │
└────────────┬──────────────┬─────────────────┬───────────────┘
             │              │                 │
             ▼              ▼                 ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ FontBitmap     │ │ FontBDF        │ │ FontTTF        │
│ (Built-in 8x8) │ │ (Text format)  │ │ (Vector)       │
│                │ │                │ │                │
│ ✅ Complete    │ │ ✅ Complete    │ │ ⚠️ Stub        │
└────────────────┘ └────────────────┘ └────────────────┘
                           │
                   ┌───────┴───────┐
                   │ FontPSF       │
                   │ (Linux fonts) │
                   │ 📋 Planned    │
                   └───────────────┘
```

## File Summary

| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `Library.Font.ailang` | ~400 | ✅ Complete | Main interface, registry, dispatch |
| `Library.FontBDF.ailang` | ~350 | ✅ Complete | BDF parser and renderer |
| `Library.FontTTF.ailang` | ~400 | ⚠️ Stub | TTF loader, rendering TODO |
| `Library.FontPSF.ailang` | ~200 | 📋 Planned | Linux console fonts |
| `Library.FontBitmap.ailang` | ~150 | 📋 Planned | Built-in bitmap fonts |

## Usage

### Basic Usage
```ailang
LibraryImport.Font
LibraryImport.FontBDF
LibraryImport.Framebuffer

SubRoutine.Main {
    FB_Init()
    Font_Init()
    
    // Load a BDF font
    font = Font_Load("terminus-16.bdf")
    
    // Draw text
    white = FB_RGB(255, 255, 255)
    Font_DrawString(font, 100, 100, "Hello, World!", white)
    
    // Cleanup
    Font_Unload(font)
    Font_Shutdown()
    FB_Close()
}
```

### Multiple Fonts
```ailang
title_font = Font_Load("terminus-32.bdf")
body_font = Font_Load("terminus-16.bdf")
code_font = Font_Load("fixed-8x16.psf")

Font_DrawString(title_font, x, y1, "Title", color)
Font_DrawString(body_font, x, y2, "Body text here", color)
Font_DrawString(code_font, x, y3, "monospace code", color)
```

### Measuring Text
```ailang
width = Font_GetStringWidth(font, "Hello")
height = Font_GetHeight(font)

// Center text
screen_width = FB_GetWidth()
x = Divide(Subtract(screen_width, width), 2)
Font_DrawString(font, x, y, "Centered", color)
```

## Font Formats

### BDF (Bitmap Distribution Format)
- **Status**: ✅ Fully implemented
- **File extension**: `.bdf`
- **Type**: Text-based bitmap
- **Sizes**: Any (8x8 to 32x32+ common)
- **Good for**: Development, readable format
- **Sources**: 
  - https://github.com/fcambus/spleen
  - https://terminus-font.sourceforge.net/

### PSF (PC Screen Font)
- **Status**: 📋 Planned
- **File extension**: `.psf`, `.psfu`
- **Type**: Binary bitmap
- **Sizes**: Usually 8×8, 8×16, 8×32
- **Good for**: System fonts, Linux compatibility
- **Sources**: `/usr/share/consolefonts/`

### TTF/OTF (TrueType/OpenType)
- **Status**: ⚠️ Stub (loads file, no rendering)
- **File extension**: `.ttf`, `.otf`
- **Type**: Vector (Bezier curves)
- **Sizes**: Scalable to any size
- **Good for**: High quality text, UI
- **Requires**: Rasterizer implementation (~1000 lines)

## API Reference

### Initialization
```ailang
Font_Init()                          // Initialize font system
Font_Shutdown()                      // Free all resources
```

### Loading
```ailang
handle = Font_Load(filename)         // Auto-detect format
handle = Font_LoadTyped(filename, FontType.BDF)  // Explicit format
handle = Font_CreateBuiltin(8)       // Built-in 8x8 font
Font_Unload(handle)                  // Free font
```

### Queries
```ailang
height = Font_GetHeight(handle)
width = Font_GetWidth(handle)        // 0 = proportional
baseline = Font_GetBaseline(handle)
char_w = Font_GetCharWidth(handle, ch)
str_w = Font_GetStringWidth(handle, str)
is_prop = Font_IsProportional(handle)
```

### Rendering
```ailang
Font_DrawChar(handle, x, y, ch, color)
Font_DrawString(handle, x, y, str, color)
Font_DrawStringBg(handle, x, y, str, fg, bg)
Font_DrawStringCentered(handle, y, str, color, screen_width)
Font_DrawStringScaled(handle, x, y, str, color, scale)  // Bitmap only
```

### TTF-Specific
```ailang
FontTTF_SetSize(handle, point_size)  // Set rendering size
```

## Implementation Notes

### Font Registry
- Maximum 16 fonts loaded simultaneously
- Each font gets a handle (0-15)
- Parallel arrays store metadata (type, height, width, data_ptr)

### BDF Implementation
- Parses entire file on load
- Stores glyph bitmaps in memory
- Supports variable-width glyphs
- ASCII 0-255 supported

### TTF Implementation (TODO)
Full TTF rendering requires:
1. **cmap parsing** - Map Unicode to glyph IDs
2. **glyf parsing** - Load glyph outlines
3. **Bezier evaluation** - Convert curves to points
4. **Rasterization** - Scan-convert to bitmap
5. **Caching** - Store rasterized glyphs

Estimated: 1000-1500 lines for basic support

### Memory Management
- Font data allocated on load
- Glyph bitmaps allocated per-character (BDF)
- Glyph cache for TTF (size × size × 256)
- All freed on unload

## Integration with C64 Runtime

The VIC-II could use this for:
- Extended text modes beyond 8×8
- Better looking BASIC output
- GUI overlays

```ailang
// In VIC_RenderTextMode, optionally use Font system
IfCondition EqualTo(VIC.use_system_font, 1) ThenBlock: {
    Font_DrawChar(VIC.font_handle, screen_x, screen_y, char_code, fg_color)
} ElseBlock: {
    // Use C64 character ROM
    VIC_RenderChar(...)
}
```

## Future Enhancements

1. **Anti-aliasing** for TTF
2. **Kerning** support
3. **Unicode** beyond ASCII
4. **Font fallback** chains
5. **Subpixel rendering** (LCD)
6. **Text shaping** (RTL, ligatures)