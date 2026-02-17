# AILANG File I/O Programming Manual

## Table of Contents
1. [Overview](#overview)
2. [File Writing Operations](#file-writing-operations)
3. [File Reading Operations](#file-reading-operations)
4. [File System Queries](#file-system-queries)
5. [Advanced File Operations](#advanced-file-operations)
6. [Examples and Patterns](#examples-and-patterns)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)

## Overview

AILANG provides a comprehensive set of file I/O operations that enable applications to read, write, and query files on the local file system. The file I/O system is designed for simplicity and safety, with automatic memory management and string integration.

### Supported File Operations
- **File Writing**: `WriteTextFile`, `AppendTextFile`
- **File Reading**: `ReadTextFile` (planned)
- **File Queries**: `FileExists`, `GetFileSize` (planned)
- **String Integration**: Works seamlessly with `StringConcat`, `NumberToString`
- **Dynamic Filenames**: Runtime filename generation from variables and expressions

## File Writing Operations

### WriteTextFile

The primary file writing function that creates or overwrites text files:

```ailang
WriteTextFile(filename, content)
```

**Parameters:**
- **filename**: String literal, variable, or expression containing the target file path
- **content**: String literal, variable, or expression containing the text data to write

**Behavior:**
- Creates new file if it doesn't exist
- Overwrites existing files completely
- Handles empty content (creates zero-byte file)
- Supports relative and absolute paths
- Automatically manages file handles and cleanup

**Examples:**

```ailang
// Basic literal usage
WriteTextFile("output.txt", "Hello, AILANG!")

// With variables
filename = "data.txt"
message = "Processing complete"
WriteTextFile(filename, message)

// Dynamic filename generation
counter = 42
filename = StringConcat("file_", NumberToString(counter))
filename = StringConcat(filename, ".txt")
WriteTextFile(filename, "Generated content")

// Empty file creation
WriteTextFile("empty.txt", "")
```

### String Integration with File Operations

File operations work seamlessly with AILANG's string functions:

```ailang
// Building complex filenames
prefix = "log"
timestamp = NumberToString(1234567890)
extension = ".txt"
filename = StringConcat(prefix, "_")
filename = StringConcat(filename, timestamp)
filename = StringConcat(filename, extension)
WriteTextFile(filename, "Log entry data")

// Content generation
header = "Report: "
data = NumberToString(999)
content = StringConcat(header, data)
WriteTextFile("report.txt", content)
```

## File System Queries

### FileExists

Checks whether a file exists on the file system:

```ailang
result = FileExists(filename)
```

**Parameters:**
- **filename**: String literal, variable, or expression containing the file path to check

**Return Value:**
- **1**: File exists and is accessible
- **0**: File does not exist or is not accessible

**Examples:**

```ailang
// Basic existence check
exists = FileExists("config.txt")
IfCondition EqualTo(exists, 1) ThenBlock {
    PrintMessage("Config file found")
} ElseBlock {
    PrintMessage("Config file missing")
}

// Dynamic filename checking
i = 0
WhileLoop LessThan(i, 10) {
    filename = StringConcat("data_", NumberToString(i))
    filename = StringConcat(filename, ".txt")
    exists = FileExists(filename)
    IfCondition EqualTo(exists, 1) ThenBlock {
        PrintMessage("Found file:")
        PrintMessage(filename)
    }
    i = Add(i, 1)
}

// Verification after write
WriteTextFile("test.txt", "content")
verify = FileExists("test.txt")
DebugAssert(EqualTo(verify, 1), "File should exist after write")
```

## Advanced File Operations

### Batch File Creation

Creating multiple files with systematic naming:

```ailang
// Create numbered series
i = 0
WhileLoop LessThan(i, 5) {
    filename = StringConcat("batch_", NumberToString(i))
    filename = StringConcat(filename, ".txt")
    content = StringConcat("File number: ", NumberToString(i))
    WriteTextFile(filename, content)
    i = Add(i, 1)
}
```

### File Overwrite Patterns

Safely overwriting files with backups:

```ailang
// Check before overwrite
original = "important.txt"
backup = StringConcat(original, ".backup")

exists = FileExists(original)
IfCondition EqualTo(exists, 1) ThenBlock {
    // Create backup (would need ReadTextFile when available)
    PrintMessage("Original file exists - creating backup recommended")
}

// Write new content
WriteTextFile(original, "New content")
```

### Conditional File Writing

Writing files based on runtime conditions:

```ailang
mode = "production"
IfCondition StringEquals(mode, "debug") ThenBlock {
    WriteTextFile("debug.log", "Debug information")
} ElseBlock {
    WriteTextFile("production.log", "Production data")
}
```

## Examples and Patterns

### Pattern 1: Log File Generation

```ailang
Function.Log.WriteEntry {
    Input: level: String, message: String
    Output: Integer
    Body: {
        timestamp = NumberToString(GetCurrentTime())
        logline = StringConcat("[", timestamp)
        logline = StringConcat(logline, "] ")
        logline = StringConcat(logline, level)
        logline = StringConcat(logline, ": ")
        logline = StringConcat(logline, message)
        logline = StringConcat(logline, "\n")
        
        WriteTextFile("application.log", logline)
        ReturnValue(1)
    }
}

// Usage
Log.WriteEntry("INFO", "Application started")
Log.WriteEntry("ERROR", "Database connection failed")
```

### Pattern 2: Data Export System

```ailang
Function.Export.SaveData {
    Input: dataset_id: Integer
    Output: Integer
    Body: {
        filename = StringConcat("export_", NumberToString(dataset_id))
        filename = StringConcat(filename, ".csv")
        
        header = "ID,Name,Value\n"
        data1 = StringConcat(NumberToString(dataset_id), ",Sample,")
        data1 = StringConcat(data1, NumberToString(100))
        data1 = StringConcat(data1, "\n")
        
        content = StringConcat(header, data1)
        WriteTextFile(filename, content)
        
        // Verify export
        verify = FileExists(filename)
        ReturnValue(verify)
    }
}

// Export multiple datasets
i = 1
WhileLoop LessThan(i, 6) {
    result = Export.SaveData(i)
    IfCondition EqualTo(result, 1) ThenBlock {
        PrintMessage("Export successful for dataset:")
        PrintNumber(i)
    }
    i = Add(i, 1)
}
```

### Pattern 3: Configuration File Management

```ailang
// Check for config file, create default if missing
config_file = "app.conf"
config_exists = FileExists(config_file)

IfCondition EqualTo(config_exists, 0) ThenBlock {
    // Create default configuration
    default_config = "debug=false\n"
    default_config = StringConcat(default_config, "max_users=100\n")
    default_config = StringConcat(default_config, "timeout=30\n")
    
    WriteTextFile(config_file, default_config)
    PrintMessage("Created default configuration file")
} ElseBlock {
    PrintMessage("Using existing configuration file")
}
```

### Pattern 4: Report Generation

```ailang
Function.Report.Generate {
    Input: report_type: String
    Output: Integer
    Body: {
        filename = StringConcat(report_type, "_report.txt")
        
        header = StringConcat("=== ", report_type)
        header = StringConcat(header, " REPORT ===\n\n")
        
        timestamp = NumberToString(GetTimestamp())
        dateline = StringConcat("Generated: ", timestamp)
        dateline = StringConcat(dateline, "\n\n")
        
        content = StringConcat(header, dateline)
        content = StringConcat(content, "Report data goes here...\n")
        
        WriteTextFile(filename, content)
        
        verify = FileExists(filename)
        ReturnValue(verify)
    }
}

// Generate different report types
Report.Generate("daily")
Report.Generate("weekly")
Report.Generate("monthly")
```

## Error Handling

### Common File I/O Errors

1. **Permission Denied**: Writing to protected directories
2. **Disk Full**: Insufficient storage space
3. **Invalid Paths**: Malformed or inaccessible file paths
4. **Null Content**: Passing null pointers or uninitialized variables

### Best Practices

1. **Verify After Write**: Always check with `FileExists` after `WriteTextFile`
2. **Use Absolute Paths**: When possible, construct full paths for clarity
3. **Handle Empty Content**: Test edge cases with empty strings
4. **Validate Filenames**: Ensure variables contain valid path strings
5. **Clean Up**: Remove temporary files when done

### Safe File Operations

```ailang
// Safe file writing with verification
Function.Safe.WriteFile {
    Input: path: String, data: String
    Output: Integer
    Body: {
        // Attempt write
        WriteTextFile(path, data)
        
        // Verify success
        exists = FileExists(path)
        IfCondition EqualTo(exists, 1) ThenBlock {
            PrintMessage("File written successfully:")
            PrintMessage(path)
            ReturnValue(1)
        } ElseBlock {
            PrintMessage("File write failed:")
            PrintMessage(path)
            ReturnValue(0)
        }
    }
}

// Usage with error handling
result = Safe.WriteFile("output.txt", "important data")
IfCondition EqualTo(result, 0) ThenBlock {
    PrintMessage("ERROR: Critical file write failed")
    // Take corrective action
}
```

## Performance Considerations

### Optimization Tips

1. **Minimize File Operations**: Batch multiple writes when possible
2. **Reuse Filename Variables**: Don't rebuild identical paths repeatedly
3. **String Concatenation Efficiency**: Build strings incrementally
4. **Avoid Unnecessary Checks**: Don't call `FileExists` unless needed

### Memory Management

```ailang
// Efficient: Reuse variables
filename = "base"
i = 0
WhileLoop LessThan(i, 100) {
    // Reuse filename variable
    filename = StringConcat("data_", NumberToString(i))
    filename = StringConcat(filename, ".txt")
    WriteTextFile(filename, "content")
    i = Add(i, 1)
}

// Less efficient: Create new variables each time
i = 0
WhileLoop LessThan(i, 100) {
    new_name = StringConcat("data_", NumberToString(i))
    new_name = StringConcat(new_name, ".txt")
    WriteTextFile(new_name, "content")
    i = Add(i, 1)
}
```

### File System Considerations

1. **Directory Limits**: Some file systems limit files per directory
2. **Filename Length**: Keep paths under system limits (typically 255 chars)
3. **Case Sensitivity**: Consider target file system case handling
4. **Special Characters**: Avoid problematic characters in filenames

## Compiler Implementation Notes

The AILANG file I/O system uses system calls for efficient file operations:

- **WriteTextFile**: Uses `open()`, `write()`, `close()` system calls
- **FileExists**: Uses `access()` system call for existence checking
- **String Integration**: Seamless pointer passing between string and file functions
- **Memory Safety**: Automatic cleanup of file handles and buffers

### Error Code Handling

```python
def compile_write_text_file(self, node):
    # Compile arguments
    # ...
    
    # System call with error checking
    self.asm.emit_syscall_write()
    
    # Check return value in RAX
    # Negative values indicate errors
    # Zero/positive values indicate success
```

### Path Resolution

The compiler handles different path types:

- **Relative Paths**: Resolved relative to working directory
- **Absolute Paths**: Used as-is
- **Dynamic Paths**: Runtime concatenation and resolution
- **String Variables**: Dereferenced to get actual path string

This manual provides comprehensive coverage of AILANG's file I/O capabilities, enabling developers to build applications that effectively interact with the file system while maintaining code safety and performance.