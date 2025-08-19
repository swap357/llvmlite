#!/usr/bin/env python3
"""
STUDY 1: Pure IR Generation (No LLVM Runtime Required)
This demonstrates the IR layer - the TRUE core of llvmlite
"""

import llvmlite.ir as ir

# Simple function: int foo(int a, int b) { return a + b; }
print("=== STUDY 1: IR Generation Core ===")

# 1. Create types
i32 = ir.IntType(32)
func_type = ir.FunctionType(i32, [i32, i32])

# 2. Create module and function
module = ir.Module(name="foo_module")
foo_func = ir.Function(module, func_type, name="foo")

# 3. Build the function body
entry = foo_func.append_basic_block(name="entry")
builder = ir.IRBuilder(entry)

# Get function arguments
a, b = foo_func.args
a.name = "a"
b.name = "b"

# Generate add instruction
result = builder.add(a, b, name="sum")
builder.ret(result)

# 4. Print the generated LLVM IR
print("Generated LLVM IR:")
print(str(module))
print("\n" + "="*50)

# Key insight: This runs ANYWHERE - no LLVM installation needed!
# This is the core - pure Python IR generation
