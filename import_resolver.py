#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Import System for AILANG with Automatic Namespace Conflict Resolution
Fixed to handle Library.XYZ.ailang naming convention
"""

import re
import random
import string
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import json
import glob

@dataclass
class ImportedModule:
    """Represents an imported module/library"""
    name: str
    path: Path
    content: str
    symbols: Set[str]
    namespace_prefix: Optional[str] = None
    is_library: bool = False

class ImportResolver:
    """
    Resolves imports and handles namespace conflicts automatically
    during the compilation process
    """
    
    def __init__(self, library_path: str = "Librarys", project_root: str = ".", seed: int = None):
        self.library_path = Path(library_path)
        self.project_root = Path(project_root)
        
        if seed:
            random.seed(seed)
        
        # Track loaded modules and their symbols
        self.loaded_modules: Dict[str, ImportedModule] = {}
        self.global_symbols: Dict[str, List[str]] = defaultdict(list)  # symbol -> [module_names]
        self.namespace_prefixes: Dict[str, str] = {}  # module -> prefix
        
        # Import patterns for AILANG - more flexible
        self.import_patterns = [
            (r'^LibraryImport\.(\S+)', 'library'),      # LibraryImport.RESP or LibraryImport.Library
            (r'^Import\.(\w+)', 'file'),                # Import.fileName
            (r'^from\s+(\w+)\s+import\s+(.+)', 'from'), # from module import symbols
        ]
        
        # Symbol extraction patterns
        self.symbol_patterns = [
            r'(\w+(?:\.\w+)+)',  # Qualified names like Time.Unix
            r'^(\w+)\s*=',        # Variable assignments
            r'Function\.(\w+)',   # Function definitions
            r'class\s+(\w+)',     # Class definitions
            r'def\s+(\w+)',       # Method definitions
        ]
        
        # Track import resolution for debugging
        self.resolution_log = []
        
        # Cache available libraries
        self._library_cache = None
    
    def get_available_libraries(self) -> Dict[str, Path]:
        """Get all available library files - supports nested folders"""
        if self._library_cache is None:
            self._library_cache = {}
            if self.library_path.exists():
                # Find all Library.*.ailang files recursively (including subdirs)
                # Use ** for recursive glob
                for lib_file in self.library_path.glob("**/Library.*.ailang"):
                    # Extract the library name from filename
                    # Library.RESP.ailang -> RESP
                    # Library.CLexerTypes.ailang -> CLexerTypes
                    name = lib_file.stem.replace("Library.", "")
                    self._library_cache[name] = lib_file
                    
                    # Also store with full "Library" prefix for backward compat
                    self._library_cache[f"Library.{name}"] = lib_file
                
                # ALSO support dotted path imports that map to directory structure
                # e.g., LibraryImport.Compiler.Frontend.Lexer.CLexerTypes
                # looks for: Librarys/Compiler/Frontend/Lexer/Library.CLexerTypes.ailang
                # This is handled in load_module, but we can also pre-cache
                
                # Find ALL .ailang files and create dotted path mappings
                for lib_file in self.library_path.glob("**/*.ailang"):
                    # Skip non-Library files
                    if not lib_file.stem.startswith("Library."):
                        continue
                    
                    # Get relative path from library root
                    rel_path = lib_file.relative_to(self.library_path)
                    
                    # Build dotted module name from path
                    # Compiler/Frontend/Lexer/Library.CLexerTypes.ailang
                    # -> Compiler.Frontend.Lexer.CLexerTypes
                    parts = list(rel_path.parent.parts)  # ['Compiler', 'Frontend', 'Lexer']
                    lib_name = lib_file.stem.replace("Library.", "")  # 'CLexerTypes'
                    
                    if parts:
                        # Has subdirectory path
                        dotted_name = ".".join(parts + [lib_name])
                        self._library_cache[dotted_name] = lib_file
                    
        return self._library_cache
    
    def generate_prefix(self) -> str:
        """Generate unique namespace prefix"""
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"NS{chars}"
    
    def extract_imports(self, content: str, current_file: str) -> List[Tuple[str, str, int]]:
        """
        Extract all import statements from source code
        Returns: [(module_name, import_type, line_number), ...]
        """
        imports = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue
            
            for pattern, import_type in self.import_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    if import_type == 'from':
                        module_name = match.group(1)
                    else:
                        module_name = match.group(1)
                    
                    imports.append((module_name, import_type, line_num))
                    self.resolution_log.append({
                        'file': current_file,
                        'line': line_num,
                        'import': module_name,
                        'type': import_type
                    })
        
        return imports
    
    def extract_symbols(self, content: str) -> Set[str]:
        """Extract all defined symbols from module content"""
        symbols = set()
        
        for pattern in self.symbol_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                symbol = match.group(1) if match.lastindex else match.group(0)
                symbols.add(symbol)
        
        return symbols
    def load_module(self, module_name: str, import_type: str) -> ImportedModule:
        """Load a module (library or local file) and extract its symbols"""
        
        # Check if already loaded
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        # Determine path based on import type
        module_path = None
        is_library = False
        
        if import_type == 'library':
            # Get available libraries
            available = self.get_available_libraries()
            
            # Try different name variations
            possible_names = [
                module_name,                              # CLexerTypes or Compiler.Frontend.Lexer.CLexerTypes
                f"Library.{module_name}",                 # Library.CLexerTypes
                module_name.replace("Library.", ""),      # Strip Library. prefix if present
            ]
            
            for name in possible_names:
                if name in available:
                    module_path = available[name]
                    is_library = True
                    break
            
            # If still not found, try converting dots to path
            if not module_path and "." in module_name:
                # LibraryImport.Compiler.Frontend.Lexer.CLexerTypes
                # -> Librarys/Compiler/Frontend/Lexer/Library.CLexerTypes.ailang
                parts = module_name.split(".")
                lib_name = parts[-1]  # CLexerTypes
                dir_parts = parts[:-1]  # ['Compiler', 'Frontend', 'Lexer']
                
                # Build path
                search_path = self.library_path
                for part in dir_parts:
                    search_path = search_path / part
                
                candidate = search_path / f"Library.{lib_name}.ailang"
                if candidate.exists():
                    module_path = candidate
                    is_library = True
                    # Cache it for next time
                    self._library_cache[module_name] = candidate
            
            if not module_path:
                # Special case: if "Library" is imported, list available libraries
                if module_name == "Library":
                    libs = list(available.keys())
                    libs = [l for l in libs if not l.startswith("Library.") and "." not in l]
                    raise ImportError(f"Cannot import 'Library' directly. Available libraries: {', '.join(sorted(libs))}")
                else:
                    # Show helpful error with available options
                    flat_libs = [l for l in available.keys() if "." not in l and not l.startswith("Library.")]
                    raise ImportError(f"Library not found: {module_name}. Available: {', '.join(sorted(flat_libs))}")
                    
        else:  # 'file' or 'from'
            module_path = self.project_root / f"{module_name}.ailang"
            is_library = False
        
        # Load the module
        if not module_path or not module_path.exists():
            raise ImportError(f"Module not found: {module_path}")
        
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract symbols
        symbols = self.extract_symbols(content)
        
        # Create module object
        module = ImportedModule(
            name=module_name,
            path=module_path,
            content=content,
            symbols=symbols,
            is_library=is_library
        )
        
        # Track symbols globally
        for symbol in symbols:
            self.global_symbols[symbol].append(module_name)
        
        # Store module
        self.loaded_modules[module_name] = module
        
        # Check for recursive imports
        sub_imports = self.extract_imports(content, str(module_path))
        for sub_module_name, sub_import_type, _ in sub_imports:
            self.load_module(sub_module_name, sub_import_type)
        
        return module
    
    def detect_conflicts(self) -> Dict[str, List[str]]:
        """Detect symbol conflicts across all loaded modules"""
        conflicts = {}
        
        for symbol, modules in self.global_symbols.items():
            if len(modules) > 1:
                conflicts[symbol] = modules
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: Dict[str, List[str]]) -> Dict[str, str]:
        """Generate prefixes for modules with conflicts"""
        modules_needing_prefix = set()
        
        for symbol, modules in conflicts.items():
            modules_needing_prefix.update(modules)
        
        prefixes = {}
        for module in modules_needing_prefix:
            if module not in self.namespace_prefixes:
                prefix = self.generate_prefix()
                self.namespace_prefixes[module] = prefix
                prefixes[module] = prefix
                
                # Update module object
                if module in self.loaded_modules:
                    self.loaded_modules[module].namespace_prefix = prefix
        
        return prefixes
    
    def apply_namespace_resolution(self, content: str, importing_file: str) -> str:
        """
        Apply namespace prefixes to resolve conflicts in the given content
        This is called when compiling each file
        """
        modified_content = content
        
        # Get all conflicts
        conflicts = self.detect_conflicts()
        
        if not conflicts:
            return content
        
        # PATCH: Filter out false conflicts (pool names)
        # Pool definitions are NOT symbols that can conflict
        pool_types = ['FixedPool', 'DynamicPool', 'TemporalPool', 
                    'NeuralPool', 'KernelPool', 'ActorPool', 
                    'SecurityPool', 'ConstrainedPool', 'FilePool']
        
        # Find all pool names in ALL loaded modules
        all_pool_names = set()
        for module_name, module in self.loaded_modules.items():
            for pool_type in pool_types:
                pool_pattern = rf'{pool_type}\.(\w+)\s*\{{'
                for match in re.finditer(pool_pattern, module.content):
                    all_pool_names.add(match.group(1))
        
        # Filter conflicts to remove pool names
        real_conflicts = {}
        for symbol, modules in conflicts.items():
            if symbol not in all_pool_names:
                real_conflicts[symbol] = modules
        
        if not real_conflicts:
            # No real conflicts, return unchanged
            return modified_content
        
        # Resolve only real conflicts
        prefixes = self.resolve_conflicts(real_conflicts)
        
        # Apply prefixes to real conflicting symbols
        for symbol, modules in real_conflicts.items():
            if len(modules) <= 1:
                continue
                
            for module in modules:
                if module not in self.namespace_prefixes:
                    continue
                
                prefix = self.namespace_prefixes[module]
                prefixed_symbol = f"{prefix}_{symbol}"
                
                # Apply prefixing patterns for real function conflicts
                if self.is_symbol_imported(content, module, symbol):
                    # Function calls
                    function_call_pattern = rf'\b{re.escape(symbol)}\s*\('
                    modified_content = re.sub(
                        function_call_pattern,
                        f'{prefixed_symbol}(',
                        modified_content,
                        flags=re.MULTILINE
                    )
                    
                    # Function definitions
                    function_def_pattern = rf'(Function\.){re.escape(symbol)}\b'
                    modified_content = re.sub(
                        function_def_pattern,
                        rf'\1{prefixed_symbol}',
                        modified_content,
                        flags=re.MULTILINE
                    )
        
        return modified_content
    
    def is_symbol_imported(self, content: str, module: str, symbol: str) -> bool:
        """Check if a symbol is imported from a specific module in the content"""
        # Check for library imports
        if re.search(rf'LibraryImport\.{re.escape(module)}', content):
            return True
        # Check for file imports
        if re.search(rf'Import\.{re.escape(module)}', content):
            return True
        # Check for from imports
        if re.search(rf'from\s+{re.escape(module)}\s+import.*{re.escape(symbol)}', content):
            return True
        return False
    
    def compile_with_imports(self, main_file: str) -> Tuple[str, Dict]:
        """
        Main entry point: compile a file with automatic import resolution
        Returns: (resolved_content, debug_info)
        
        FIX: Now inlines file imports (Import.X) just like LibraryImport handles libraries
        """
        print(f"Resolving imports for {main_file}...")
        
        # Load main file
        main_path = Path(main_file)
        
        # Set source directory for relative imports
        self.current_source_dir = main_path.parent
        
        with open(main_path, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # Extract and load all imports recursively
        imports = self.extract_imports(main_content, main_file)
        
        # List available libraries if we have library imports
        if any(t == 'library' for _, t, _ in imports):
            available = self.get_available_libraries()
            if available:
                print(f"  Available libraries: {', '.join([k for k in available.keys() if not k.startswith('Library.')])}")
        
        for module_name, import_type, line_num in imports:
            print(f"  Loading {import_type}: {module_name}")
            try:
                self.load_module(module_name, import_type)
            except ImportError as e:
                print(f"  Error at line {line_num}: {e}")
                raise
        
        # Detect conflicts
        conflicts = self.detect_conflicts()
        
        if conflicts:
            print(f"\nFound {len(conflicts)} symbol conflicts")
            for symbol, modules in list(conflicts.items())[:5]:
                print(f"    {symbol}: {', '.join(modules)}")
            
            # Resolve conflicts
            prefixes = self.resolve_conflicts(conflicts)
            print(f"\nGenerated {len(prefixes)} namespace prefixes")
        
        # === BUILD COMBINED CONTENT ===
        # This is the key fix: inline file imports just like library imports are handled
        combined_parts = []
        
        # 1. Collect all LibraryImport statements from ALL sources (deduplicated)
        all_library_imports = set()
        
        # From file-imported modules (helpers, myutils, etc.)
        for module in self.loaded_modules.values():
            if module.is_library:
                continue  # Don't extract LibraryImport lines from actual library files
            for line in module.content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('LibraryImport.'):
                    all_library_imports.add(stripped)
        
        # From main file
        for line in main_content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('LibraryImport.'):
                all_library_imports.add(stripped)
        
        # 2. Emit deduplicated library imports at top
        for lib_import in sorted(all_library_imports):
            combined_parts.append(lib_import)
        if all_library_imports:
            combined_parts.append('')
        
        # 3. Inline file-imported modules (NOT library modules)
        #    This is what was missing - the actual concatenation
        for module_name, module in self.loaded_modules.items():
            if module.is_library:
                continue  # Libraries are handled via LibraryImport statements
            
            # Strip import lines from module content to avoid duplication
            module_lines = []
            for line in module.content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('LibraryImport.') or stripped.startswith('Import.'):
                    continue
                module_lines.append(line)
            
            module_code = '\n'.join(module_lines)
            if module_code.strip():
                combined_parts.append(f'// === Inlined from {module_name} ===')
                combined_parts.append(module_code)
                combined_parts.append('')
        
        # 4. Emit main file content (strip all import statements)
        main_lines = []
        for line in main_content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('Import.') or stripped.startswith('LibraryImport.'):
                continue
            main_lines.append(line)
        
        combined_parts.append('// === Main module ===')
        combined_parts.append('\n'.join(main_lines))
        
        # 5. Combine and apply namespace resolution
        combined_content = '\n'.join(combined_parts)
        resolved_content = self.apply_namespace_resolution(combined_content, main_file)
        
        # Build debug info
        inlined = [m for m, mod in self.loaded_modules.items() if not mod.is_library]
        debug_info = {
            'main_file': main_file,
            'loaded_modules': list(self.loaded_modules.keys()),
            'inlined_modules': inlined,
            'conflicts': conflicts,
            'prefixes': self.namespace_prefixes,
            'resolution_log': self.resolution_log
        }
        
        # Save debug info
        debug_file = main_path.with_suffix('.import_debug.json')
        with open(debug_file, 'w') as f:
            json.dump(debug_info, f, indent=2, default=str)
        
        print(f"Import resolution complete")
        print(f"  Inlined {len(inlined)} file imports: {', '.join(inlined)}")
        print(f"Debug info saved to {debug_file}")
        
        return resolved_content, debug_info


def integrate_with_compiler(source_file: str, library_path: str = "Librarys") -> str:
    """
    Integration point for the compiler
    Call this instead of directly reading the source file
    """
    resolver = ImportResolver(library_path=library_path)
    resolved_content, debug_info = resolver.compile_with_imports(source_file)
    
    # Return the resolved content for compilation
    return resolved_content


# Hook to replace file reading in main.py
def enhanced_load_source(filepath: str) -> str:
    """
    Enhanced source loader that resolves imports and conflicts
    Replace your current file reading with this
    """
    # Check if file has imports
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Quick check for imports
    has_imports = (
        'LibraryImport.' in content or 
        'Import.' in content or 
        'from ' in content
    )
    
    if has_imports:
        # Use import resolver
        print("Detected imports, resolving dependencies...")
        return integrate_with_compiler(filepath)
    else:
        # No imports, return as-is
        return content


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python import_resolver.py <source_file.ailang>")
        sys.exit(1)
    
    source_file = sys.argv[1]
    
    # Test the import resolution
    resolver = ImportResolver()
    resolved_content, debug_info = resolver.compile_with_imports(source_file)
    
    # Save resolved content for inspection
    output_file = Path(source_file).with_suffix('.resolved.ailang')
    with open(output_file, 'w') as f:
        f.write(resolved_content)
    
    print(f"\nResolved source saved to {output_file}")
    print(f"Statistics:")
    print(f"   Modules loaded: {len(debug_info['loaded_modules'])}")
    print(f"   Conflicts found: {len(debug_info['conflicts'])}")
    print(f"   Prefixes generated: {len(debug_info['prefixes'])}")

# Fixed version that returns mappings
_original_enhanced_load_source = enhanced_load_source

def enhanced_load_source(filepath):
    """Enhanced version that also returns alias mappings"""
    processed_source = _original_enhanced_load_source(filepath)
    
    # Extract alias mappings from processed source
    import re
    alias_mappings = {}
    
    # Find all RANDOM_Module patterns (ONLY library calls with dots)
    # This pattern matches: NS64KZ1X_XArrays.XCreate
    # But NOT: ESCAL056_0000_MAINLINE_CONTROL
    pattern = r'([A-Z0-9]{6,8})_([A-Z][a-zA-Z]+)\.'
    for match in re.finditer(pattern, processed_source):
        alias = f"{match.group(1)}_{match.group(2)}"  # e.g., "NS64KZ1X_XArrays"
        original = match.group(2)  # e.g., "XArrays"
        
        # Only add if not already present (first occurrence wins)
        if alias not in alias_mappings:
            alias_mappings[alias] = original
    
    return processed_source, alias_mappings
