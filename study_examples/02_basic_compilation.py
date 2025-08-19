#!/usr/bin/env python3
"""
STUDY 2: Basic Compilation without PassManager
This shows the ExecutionEngine core functionality
"""

import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

print("=== STUDY 2: Basic Compilation (No Optimization) ===")

# Our simple LLVM IR (from Study 1)
llvm_ir = """
define i32 @foo(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  ret i32 %sum
}
"""

print("Input LLVM IR:")
print(llvm_ir)

# 1. Parse IR to create module
llvm_module = llvm.parse_assembly(llvm_ir)
print("✓ Module parsed successfully")

# 2. Create target machine
target = llvm.Target.from_default_triple()
target_machine = target.create_target_machine()
print(f"✓ Target: {target_machine.triple}")

# 3. Create execution engine (JIT compiler)
engine = llvm.create_mcjit_compiler(llvm_module, target_machine)
engine.finalize_object()
print("✓ JIT compilation complete")

# 4. Get function pointer and execute
func_ptr = engine.get_function_address("foo")
foo_func = CFUNCTYPE(c_int, c_int, c_int)(func_ptr)

# Test the compiled function
result = foo_func(5, 7)
print(f"✓ foo(5, 7) = {result}")

print("="*50)
# Key insight: This compiled and ran WITHOUT any PassManager optimization!
