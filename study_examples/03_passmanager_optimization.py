#!/usr/bin/env python3
"""
STUDY 3: PassManager's Role - The Optimization Specialist
Shows before/after optimization to understand PassManager's purpose
"""

import llvmlite.binding as llvm
from llvmlite.binding import passmanagers

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

print("=== STUDY 3: PassManager Optimization Role ===")

# Deliberately inefficient LLVM IR with redundant operations
unoptimized_ir = """
define i32 @inefficient_foo(i32 %a, i32 %b) {
entry:
  ; Redundant operations that PassManager can optimize
  %temp1 = add i32 %a, 0           ; Adding zero (redundant)
  %temp2 = mul i32 %temp1, 1       ; Multiplying by one (redundant)
  %temp3 = add i32 %temp2, %b      ; The actual useful operation
  %temp4 = add i32 %temp3, 0       ; More redundant adding zero
  ret i32 %temp4
}
"""

print("BEFORE optimization:")
print(unoptimized_ir)

# Parse the unoptimized IR
module_before = llvm.parse_assembly(unoptimized_ir)
print("✓ Unoptimized module parsed")

# Clone for comparison
module_after = llvm.parse_assembly(unoptimized_ir)

# Create and configure PassManager
pm = passmanagers.create_module_pass_manager()
pm.add_instruction_combining_pass()  # Combines redundant instructions
pm.add_constant_merge_pass()         # Merges duplicate constants
pm.add_dead_code_elimination_pass()  # Removes dead code

print("\n🔧 Running PassManager optimizations...")
pm.run(module_after)
print("✓ Optimization complete")

print("\nAFTER optimization:")
print(str(module_after))

print("\n" + "="*50)
