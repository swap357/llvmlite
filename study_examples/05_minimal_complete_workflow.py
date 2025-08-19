#!/usr/bin/env python3
"""
STUDY 5: Minimal Complete Workflow
Shows the entire pipeline: IR → Compilation → Optimization → Execution
"""

import llvmlite.ir as ir
import llvmlite.binding as llvm
from llvmlite.binding import passmanagers
from ctypes import CFUNCTYPE, c_int

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

print("=== STUDY 5: Complete Minimal Workflow ===")

# STEP 1: Generate IR (Core functionality)
print("Step 1: IR Generation...")
module = ir.Module(name="complete_example")
i32 = ir.IntType(32)

# Simple function: multiply by 2
func_type = ir.FunctionType(i32, [i32])
multiply_func = ir.Function(module, func_type, name="multiply_by_2")

entry = multiply_func.append_basic_block(name="entry")
builder = ir.IRBuilder(entry)

x = multiply_func.args[0]
x.name = "x"
two = ir.Constant(i32, 2)
result = builder.mul(x, two, name="result")
builder.ret(result)

print(f"✓ Generated function: {multiply_func.name}")

# STEP 2: Parse to binding layer
print("\nStep 2: Parsing IR...")
llvm_module = llvm.parse_assembly(str(module))
print("✓ Module parsed to binding layer")

# STEP 3: Apply optimizations (PassManager)
print("\nStep 3: Applying optimizations...")
pm = passmanagers.create_module_pass_manager()
pm.add_instruction_combining_pass()
pm.add_cfg_simplification_pass()
changed = pm.run(llvm_module)
print(f"✓ Optimizations applied (changed: {changed})")

# STEP 4: Compile to machine code
print("\nStep 4: JIT compilation...")
target = llvm.Target.from_default_triple()
target_machine = target.create_target_machine()
engine = llvm.create_mcjit_compiler(llvm_module, target_machine)
engine.finalize_object()
print("✓ Machine code generated")

# STEP 5: Execute
print("\nStep 5: Execution...")
func_ptr = engine.get_function_address("multiply_by_2")
multiply_func = CFUNCTYPE(c_int, c_int)(func_ptr)

test_value = 21
result = multiply_func(test_value)
print(f"✓ multiply_by_2({test_value}) = {result}")

print("\n" + "="*60)
# COMPLETE WORKFLOW SUMMARY:
# 1. IR Layer:       Generate LLVM IR (CORE)
# 2. Binding Layer:  Parse and manage (RUNTIME CORE)
# 3. PassManager:    Optimize (SPECIALIST)
# 4. ExecutionEngine: Compile (COMPILER)
# 5. Native Code:    Execute (RESULT)
#
# PassManager is just ONE step in the pipeline!
