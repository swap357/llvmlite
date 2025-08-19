#!/usr/bin/env python3
"""
STUDY 4: IR Builder - The True Workhorse
Demonstrates step-by-step IR construction
"""

import llvmlite.ir as ir

print("=== STUDY 4: IR Builder Deep Dive ===")

# Create module
module = ir.Module(name="builder_study")

# Types
i32 = ir.IntType(32)
i1 = ir.IntType(1)  # boolean

# Function: int bar(int x) with conditional logic
func_type = ir.FunctionType(i32, [i32])
bar_func = ir.Function(module, func_type, name="bar")

# Create basic blocks for conditional flow
entry_bb = bar_func.append_basic_block(name="entry")
then_bb = bar_func.append_basic_block(name="then")
else_bb = bar_func.append_basic_block(name="else")
exit_bb = bar_func.append_basic_block(name="exit")

# Build entry block
builder = ir.IRBuilder(entry_bb)
x = bar_func.args[0]
x.name = "x"

print("Step 1: Creating comparison...")
# Compare: if (x > 10)
ten = ir.Constant(i32, 10)
condition = builder.icmp_signed('>', x, ten, name="x_gt_10")

print("Step 2: Creating conditional branch...")
builder.cbranch(condition, then_bb, else_bb)

# Build 'then' block: return x * 2
builder.position_at_end(then_bb)
two = ir.Constant(i32, 2)
then_result = builder.mul(x, two, name="x_times_2")
builder.branch(exit_bb)

print("Step 3: Building 'then' branch...")

# Build 'else' block: return x + 1
builder.position_at_end(else_bb)
one = ir.Constant(i32, 1)
else_result = builder.add(x, one, name="x_plus_1")
builder.branch(exit_bb)

print("Step 4: Building 'else' branch...")

# Build exit block with PHI node
builder.position_at_end(exit_bb)
phi = builder.phi(i32, name="result")
phi.add_incoming(then_result, then_bb)
phi.add_incoming(else_result, else_bb)
builder.ret(phi)

print("Step 5: Creating PHI node for result merging...")

print("\nGenerated conditional function:")
print(str(module))

print("\n" + "="*50)
