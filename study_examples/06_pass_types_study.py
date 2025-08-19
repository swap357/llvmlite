#!/usr/bin/env python3
"""
STUDY 6: PassManager Types and Their Roles
Demonstrates different pass types and what they optimize
"""

import llvmlite.binding as llvm
from llvmlite.binding import passmanagers

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()

print("=== STUDY 6: Pass Types Study ===")

# Complex IR with various optimization opportunities
complex_ir = """
declare i32 @external_func(i32)

define i32 @test_all_passes(i32 %input) {
entry:
  ; Dead code
  %dead1 = add i32 %input, 0        ; Adding zero (InstCombine can fix)
  %dead2 = mul i32 %dead1, 1        ; Multiplying by one (InstCombine)

  ; Redundant computation
  %calc1 = add i32 %dead2, 10
  %calc2 = add i32 %dead2, 10       ; Same computation (GVN can fix)

  ; Control flow that can be simplified
  %cmp = icmp eq i32 %calc1, %calc2  ; Always true! (CFG simplification)
  br i1 %cmp, label %always_taken, label %never_taken

never_taken:                         ; Dead basic block (DCE can remove)
  %never = add i32 %input, 999
  br label %exit

always_taken:
  %result = add i32 %calc1, 5
  br label %exit

exit:
  %final = phi i32 [ %result, %always_taken ], [ %never, %never_taken ]
  ret i32 %final
}
"""

def test_passes(pass_name, add_pass_func):
    print(f"\n--- Testing {pass_name} ---")
    module = llvm.parse_assembly(complex_ir)

    # Count instructions before
    before_lines = str(module).count('\n')

    # Apply specific pass
    pm = passmanagers.create_module_pass_manager()
    add_pass_func(pm)
    pm.run(module)

    # Count instructions after
    after_lines = str(module).count('\n')
    reduction = before_lines - after_lines

    print(f"Lines before: {before_lines}")
    print(f"Lines after:  {after_lines}")
    print(f"Reduction:    {reduction} lines")

    if reduction > 0:
        print(f"✓ {pass_name} successfully optimized the code!")
    else:
        print(f"~ {pass_name} didn't change this particular code")

# Test individual passes
print("Testing individual optimization passes:")

test_passes("Instruction Combining",
           lambda pm: pm.add_instruction_combining_pass())

test_passes("Global Value Numbering",
           lambda pm: pm.add_gvn_pass())

test_passes("Dead Code Elimination",
           lambda pm: pm.add_dead_code_elimination_pass())

test_passes("CFG Simplification",
           lambda pm: pm.add_cfg_simplification_pass())

# Test combined optimization
print(f"\n--- Testing Combined Optimization ---")
module = llvm.parse_assembly(complex_ir)
before_lines = str(module).count('\n')

pm = passmanagers.create_module_pass_manager()
pm.add_instruction_combining_pass()  # Fix redundant operations
pm.add_gvn_pass()                   # Remove duplicate computations
pm.add_cfg_simplification_pass()    # Simplify control flow
pm.add_dead_code_elimination_pass() # Remove unreachable code

pm.run(module)
after_lines = str(module).count('\n')

print(f"Lines before all passes: {before_lines}")
print(f"Lines after all passes:  {after_lines}")
print(f"Total reduction: {before_lines - after_lines} lines")

print("\n" + "="*60)
# KEY INSIGHTS:
# - Each pass type targets specific optimization patterns
# - InstCombine: Simplifies arithmetic (x+0, x*1, etc.)
# - GVN: Eliminates redundant computations
# - CFG: Simplifies control flow (removes dead branches)
# - DCE: Removes completely unreachable code
# - PassManager orchestrates multiple passes for maximum effect
