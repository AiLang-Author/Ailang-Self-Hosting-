# AILang Coreutils

POSIX-compliant reimplementation of core Unix utilities in AILang. Drop-in replacements for GNU coreutils with competitive performance, smaller binary sizes, and explicit memory management.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/AiLang-Author/CoreUtils-.git
cd CoreUtils-

# Install utilities to ~/.local/bin
./install_ailang_utils.sh

# Test performance against GNU equivalents
./bench_all_utils.sh
```

All utilities are pre-compiled and available in the `dist/` folder, organized as `{utility}_util/` directories containing both source code and executables.

## Project Status

**50+  utilities completed** - Production ready with full POSIX compliance and comprehensive testing.

** SEE DIST FOLDER FOR COMPLETE LIST CHANGING DAILY !!!! **
---

## Available Utilities

### File Operations
- **cat** - Concatenate and display files
- **cp** - Copy files and directories
- **rm** - Remove files and directories
- **ln** - Create links between files
- **touch** - Change file timestamps
- **mkdir** - Create directories
- **file** - Determine file type

### Text Processing
- **grep** - Search for patterns in files
- **head** - Output first part of files
- **tail** - Output last part of files
- **wc** - Count lines, words, and bytes
- **cut** - Remove sections from lines
- **tr** - Translate or delete characters
- **sort** - Sort lines of text
- **uniq** - Report or filter repeated lines
- **nl** - Number lines of files
- **rev** - Reverse lines characterwise
- **tac** - Concatenate and print files in reverse
- **fold** - Wrap text to specified width
- **diff** - Compare files line by line
- **tee** - Read from stdin and write to stdout and files

### Output & Display
- **echo** - Display a line of text
- **seq** - Generate sequences of numbers
- **yes** - Repeatedly output a string

### System Information
- **ls** - List directory contents
- **find** - Search for files in directory hierarchy
- **pwd** - Print working directory
- **whoami** - Print effective user name
- **logname** - Print user's login name
- **id** - Print user and group information
- **uname** - Print system information
- **env** - Print or set environment variables
- **printenv** - Print environment variables
- **date** - Display or set system date and time

### Path Manipulation
- **basename** - Strip directory and suffix from filenames
- **dirname** - Strip last component from file name

### Control Flow
- **true** - Exit with success status
- **false** - Exit with failure status
- **sleep** - Delay for a specified time

## Key Features

- **Small Binaries**: 50-71% smaller than GNU equivalents (8KB-40KB range)
- **Fast Performance**: Competitive with or exceeding GNU coreutils in many use cases
- **POSIX Compliant**: Full adherence to POSIX specifications
- **Memory Safe**: Explicit memory management, leak-free verified
- **Self-Contained**: Minimal dependencies, direct syscalls
- **Simple Installation**: Single script to install all utilities

## Installation

The `install_ailang_utils.sh` script handles everything:

```bash
./install_ailang_utils.sh
```

This will:
1. Copy all 39 utilities to `~/.local/bin`
2. Create symlinks with `_ailang` suffix
3. Auto-enable utilities in your PATH
4. Create the `ailang-utils` management tool

### Managing Utilities

Use the `ailang-utils` command to manage your installation:

```bash
ailang-utils status              # Check enabled utilities
ailang-utils enable <utility>    # Enable specific utility
ailang-utils disable <utility>   # Disable specific utility
ailang-utils enable all          # Enable all utilities
ailang-utils disable all         # Revert to GNU versions
ailang-utils benchmark <utility> # Test performance vs GNU
```

## Benchmarking

Run comprehensive performance tests:

```bash
# Test all utilities
./bench_all_utils.sh

# Test specific utility
ailang-utils benchmark grep
```

Benchmarks compare installed AILang utilities against GNU equivalents using realistic workloads.

## Building from Source

If you want to rebuild the utilities:

```bash
# Build all utilities
./build_all_utils.sh

# Build outputs to dist/{utility}_util/ directories
```

Requires the AILang compiler: https://github.com/AiLang-Author/AiLang

## Repository Structure

```
CoreUtils-/
├── dist/                      # All packaged utilities
│   ├── cat_util/
│   │   ├── cat.ailang        # Source code
│   │   ├── cat_exec          # Compiled binary
│   │   └── README.md         # Utility-specific docs
│   ├── grep_util/
│   ├── ls_util/
│   └── ...                   # 39 total utilities
├── install_ailang_utils.sh   # Installation script
├── bench_all_utils.sh        # Benchmarking tool
├── build_all_utils.sh        # Build script
└── README.md                 # This file
```

Each utility directory contains:
- Source code (`.ailang`)
- Compiled executable (`_exec`)
- Documentation and examples

## Design Principles

1. **POSIX First** - Specification is authoritative
2. **GNU Compatible** - Byte-identical output where GNU matches POSIX
3. **Explicit Memory** - No hidden allocations, bounded buffers
4. **Direct Syscalls** - Minimal abstraction for performance
5. **Streaming** - Fixed memory usage regardless of input size
6. **Clear Errors** - Fail-fast with diagnostic messages

## Performance Philosophy

The goal is competitive real-world performance with readable, maintainable code. Measurements guide optimization decisions. AILang utilities achieve GNU-level performance or better in common use cases while maintaining significantly smaller binary sizes.

## Platform Support

- **Linux x86_64** - Primary platform (full support)
- Argument parsing uses `/proc/self/cmdline` (Linux-specific)
- System calls are x86_64 Linux
- Windows/macOS support not currently available

## Contributing

Contributions welcome for:
- Bug fixes and performance improvements
- Additional utilities matching project criteria
- Documentation and examples
- Platform support expansion

### Requirements
- Match or exceed GNU performance in typical use cases
- 100% test pass rate
- POSIX compliance
- Memory safety verification
- Follow existing code patterns

## Documentation

Each utility includes comprehensive documentation in its respective `dist/{utility}_util/README.md` file with:
- Feature comparison with GNU equivalent
- Usage examples
- Implementation notes
- Known limitations

## Testing

All utilities include comprehensive test suites verifying:
- Functional correctness (byte-for-byte GNU compatibility)
- POSIX compliance
- Edge cases and error handling
- Memory safety
- Performance characteristics

## License

MIT

## References

- **AILang Compiler**: https://github.com/AiLang-Author/AiLang
- **POSIX.1-2017**: https://pubs.opengroup.org/onlinepubs/9699919799/
- **GNU Coreutils**: https://www.gnu.org/software/coreutils/

---

**Quality over quantity** - Each utility is carefully implemented with full testing and documentation.
