#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Parser Diagnostics Module for AILANG - With Optional Roast Mode
================================================================
Professional error messages with optional savage commentary
"""

from typing import Dict, List, Tuple, Optional
import sys
import random
import datetime

class ParserDiagnostics:
    """Handles parsing warnings, errors, and validation with optional roast mode"""
    
    def __init__(self, strict_mode: bool = False, roast_mode: bool = False):
        self.strict_mode = strict_mode
        self.roast_mode = roast_mode
        self.warnings = []
        self.errors = []
        self.acronym_map = {}
        
        # Roast messages for acronym conflicts
        self.ACRONYM_ROASTS = [
            "You named a parameter the same as an acronym. That's like naming your dog 'Cat'.",
            "This parameter shadows an acronym. The confusion you're creating is legendary.",
            "Parameter vs Acronym conflict detected. Pick a side. We're at war here.",
            "You couldn't think of ANY other name for this parameter? Really?",
            "This naming conflict has the same energy as replying-all to company emails.",
            "Your parameter is cosplaying as an acronym. It's not fooling anyone.",
            "Acronym shadowing detected. This is why we can't have nice autocomplete.",
            "This parameter name conflict is giving everyone trust issues.",
            "You've created a quantum parameter - it's both an acronym and not an acronym.",
            "This shadowing situation is darker than your terminal theme.",
        ]
        
        self.DUPLICATE_ROASTS = [
            "You defined this twice. Once was already too many.",
            "Duplicate definition detected. Did you forget you already wrote this?",
            "This has been defined before. Alzheimer's or copy-paste gone wrong?",
            "You already defined this. The compiler remembers. Unlike you, apparently.",
            "Duplicate found. This is what happens when you don't use version control.",
        ]
        
        self.GENERIC_ROASTS = [
            "This code has more red flags than a communist parade.",
            "I've seen better syntax in ransomware.",
            "Your code quality is somewhere between 'intern's first day' and 'why did we deploy this'.",
            "This makes me nostalgic for segfaults.",
            "Error detected. In other news, water is wet.",
        ]
        
    def set_acronym_map(self, acronym_map: Dict[str, str]):
        """Set the acronym mappings for conflict checking"""
        self.acronym_map = acronym_map
    
    def _get_roast(self, error_type: str) -> str:
        """Get a random roast for the error type"""
        if not self.roast_mode:
            return ""
            
        # Check for Friday afternoon
        now = datetime.datetime.now()
        is_friday = now.weekday() == 4
        is_late = now.hour >= 16
        
        roast_pool = {
            'acronym': self.ACRONYM_ROASTS,
            'duplicate': self.DUPLICATE_ROASTS,
            'generic': self.GENERIC_ROASTS
        }.get(error_type, self.GENERIC_ROASTS)
        
        roast = "\n🔥 " + random.choice(roast_pool)
        
        if is_friday and is_late:
            roast += "\n⚠️  Also, it's Friday afternoon. What are you even doing here?"
            
        return roast
        
    def check_acronym_conflicts(self, ast) -> bool:
        """
        Check for parameter names that conflict with acronyms
        Returns True if conflicts found (warnings issued), False otherwise
        """
        conflicts_found = False
        
        # Import here to avoid circular dependency
        from .ailang_ast import Function, AcronymDefinitions
        
        if not self.acronym_map:
            return False
            
        print("\n" + "="*60)
        if self.roast_mode:
            print("🔥 ACRONYM CONFLICT ANALYSIS (ROAST MODE) 🔥")
        else:
            print("ACRONYM CONFLICT ANALYSIS")
        print("="*60)
        
        for decl in ast.declarations:
            if isinstance(decl, Function):
                func_conflicts = []
                
                # Check each parameter
                for param in decl.input_params:
                    param_name = param[0] if isinstance(param, tuple) else param
                    
                    if param_name in self.acronym_map:
                        func_conflicts.append({
                            'param': param_name,
                            'expansion': self.acronym_map[param_name]
                        })
                        conflicts_found = True
                
                # Report conflicts for this function
                if func_conflicts:
                    self._report_function_conflicts(decl.name, func_conflicts)
        
        if not conflicts_found:
            print("✅ No acronym conflicts detected")
            if self.roast_mode:
                print("🎉 Miracles do happen! Your naming doesn't suck!")
        else:
            print("\n⚠️  RECOMMENDATION: Consider renaming conflicting parameters")
            print("    to avoid confusion (e.g., prefix with 'param_' or use lowercase)")
            if self.roast_mode:
                print("🔥 Or don't. Keep living dangerously. YOLO.")
        
        print("="*60 + "\n")
        return conflicts_found
    
    def _report_function_conflicts(self, func_name: str, conflicts: List[Dict]):
        """Report conflicts for a specific function"""
        print(f"\n⚠️  WARNING: Function '{func_name}' has acronym conflicts:")
        
        for conflict in conflicts:
            param = conflict['param']
            expansion = conflict['expansion']
            
            print(f"    • Parameter '{param}' shadows acronym")
            print(f"      - Acronym '{param}' normally expands to: '{expansion}'")
            print(f"      - Inside this function, '{param}' refers to the parameter")
            
            if self.roast_mode:
                print(self._get_roast('acronym'))
            
            self.warnings.append({
                'type': 'acronym_conflict',
                'function': func_name,
                'parameter': param,
                'acronym_expansion': expansion,
                'message': f"Parameter '{param}' in function '{func_name}' shadows acronym '{param}' -> '{expansion}'"
            })
    
    def check_duplicate_declarations(self, ast) -> bool:
        """Check for duplicate function/pool/acronym declarations"""
        seen_functions = {}
        seen_pools = {}
        seen_acronyms = {}
        duplicates_found = False
        
        from .ailang_ast import Function, LinkagePoolDecl, AcronymDefinitions
        
        print("\n" + "="*60)
        if self.roast_mode:
            print("🔥 DUPLICATE DECLARATION CHECK (ROAST MODE) 🔥")
        else:
            print("DUPLICATE DECLARATION CHECK")
        print("="*60)
        
        for decl in ast.declarations:
            if isinstance(decl, Function):
                if decl.name in seen_functions:
                    print(f"\n❌ ERROR: Duplicate function '{decl.name}'")
                    print(f"    First defined at line {seen_functions[decl.name]}")
                    print(f"    Redefined at line {decl.line}")
                    if self.roast_mode:
                        print(self._get_roast('duplicate'))
                    duplicates_found = True
                else:
                    seen_functions[decl.name] = decl.line
                    
            elif isinstance(decl, LinkagePoolDecl):
                if decl.name in seen_pools:
                    print(f"\n❌ ERROR: Duplicate LinkagePool '{decl.name}'")
                    if self.roast_mode:
                        print(self._get_roast('duplicate'))
                    duplicates_found = True
                else:
                    seen_pools[decl.name] = decl.line
                    
            elif isinstance(decl, AcronymDefinitions):
                for acronym in decl.mappings:
                    if acronym in seen_acronyms:
                        print(f"\n⚠️  WARNING: Acronym '{acronym}' redefined")
                        if self.roast_mode:
                            print("🔥 You redefined an acronym. Make up your mind!")
                        duplicates_found = True
                    else:
                        seen_acronyms[acronym] = decl.line
        
        if not duplicates_found:
            print("✅ No duplicate declarations found")
            if self.roast_mode:
                print("🎉 You managed to name things uniquely. Gold star! ⭐")
        
        print("="*60 + "\n")
        return duplicates_found
    
    def run_all_checks(self, ast):
        """Run all diagnostic checks on the AST"""
        header = "="*70
        if self.roast_mode:
            print(f"\n{header}")
            print("🔥🔥🔥 PARSER DIAGNOSTICS - ROAST MODE ENABLED 🔥🔥🔥")
            print(header)
            print("Brace yourself. The parser has opinions about your code.")
        else:
            print(f"\n{header}")
            print("RUNNING PARSER DIAGNOSTICS")
            print(header)
        
        # Run each check
        has_conflicts = self.check_acronym_conflicts(ast)
        has_duplicates = self.check_duplicate_declarations(ast)
        
        # Summary
        print("\n" + "="*70)
        print("DIAGNOSTIC SUMMARY")
        print("="*70)
        
        if self.warnings:
            print(f"⚠️  Total warnings: {len(self.warnings)}")
        if self.errors:
            print(f"❌ Total errors: {len(self.errors)}")
            if self.strict_mode:
                print("Compilation aborted due to errors (strict mode)")
                if self.roast_mode:
                    print("🔥 Fix your code. The compiler has spoken.")
                return False
        
        if not self.warnings and not self.errors:
            print("✅ No issues detected")
            if self.roast_mode:
                print("🎉 Your code doesn't completely suck! Today is a good day!")
        elif self.roast_mode:
            if self.warnings and not self.errors:
                print("🔥 You have warnings. They're like errors, but for cowards.")
            elif self.errors:
                print("🔥 You have errors. The compiler is not angry, just disappointed.")
        
        print("="*70 + "\n")
        return True
    
    def clear(self):
        """Clear all diagnostics"""
        self.warnings.clear()
        self.errors.clear()
        
    def get_summary(self) -> Dict:
        """Get a summary of all diagnostics"""
        return {
            'warnings': self.warnings.copy(),
            'errors': self.errors.copy(),
            'warning_count': len(self.warnings),
            'error_count': len(self.errors),
            'roast_mode': self.roast_mode
        }