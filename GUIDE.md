# 10-411 Compilers for Machine Learning: Build Guide

A week by week plan for building an ML compiler from scratch, following the CMU course at [10-411.com](https://10-411.com/).

## How to follow along

This follows the same steps as [letsbuildacompiler's TUTORIAL.md](https://github.com/eliben/letsbuildacompiler/blob/main/TUTORIAL.md). Starting with week 1:

1. Read the week N assignment PDF from the course page. It is the reference for the week. Save a copy in `assignments/`. The [technical syllabus](https://gist.github.com/geohot/4768597d9dc536446ee2d5de1f29e89d) gives background.
2. Read the week N section in this guide. Start with its example: a small program and what it should turn into.
3. Write the tests and the code, as described in "How each week works" at the end of this guide.
4. Add your own lines under the week's Notes (make the heading if the week has none): where each idea lives in your code, where you left the spec, and gaps you found in the spec. Each part section in Eli's TUTORIAL.md has this kind of note.

## Week 0: Setup

- [ ] Done

- Make the repo with a `tests/week1/` folder for `.uir` test files.
- Make a runner that calls `./compile` on every test and checks each outcome against the file name prefix. Week 1 describes `./compile` and the prefixes.
- Read the week 1 assignment, the course page, and the syllabus gist.
- Skim the tinygrad repo so you know where the key files are.

## Week 1: UOps, rewrites, interpreter

- [ ] Done

The reference for this week is the [week 1 assignment](assignments/week1.pdf) ([online copy](https://10-411.com/assignments/week1.pdf)). When this guide and the PDF disagree, the PDF wins. The course page calls it a draft, so check for a newer version before you start.

Example from the assignment:

```
%x = param [] slot=0 dtype=i32 addrspace=ALU
%s = add %x %x
%v = call %s 3
%t = assert %v 6
```

`%x` is the input in slot 0. `%s` is a function body that uses it. The call binds slot 0 to 3, so the body computes 3 + 3 = 6. The assert compares 6 with 6, so `./compile` prints `MATCH` for this file.

### What the grader sees

- The command is `./compile [<file> ...]`. For each file it prints one line, `<outcome> <file>`, with one space and the path exactly as given.
- MATCH: the program ran and its value equals the expected value.
- MISMATCH: the program ran and the values differ.
- REJECTED: the program is invalid. This is found before running.
- OVERBUDGET: the program hits a size or cost limit, so it never runs.
- The file name prefix gives the expected outcome. No prefix means MATCH. The others are `mismatch_`, `rejected_` and `overbudget_`.
- A file can break more than one rule, so run the checks in this order:
  1. More than 4096 bytes: OVERBUDGET. Check this before parsing.
  2. Parse the file.
  3. 100 or more nodes, or 300 or more source edges: OVERBUDGET.
  4. Check dtypes, shapes, bounds and the test file rules. Any failure is REJECTED.
  5. Static cost (ایستا: known before running) of 1,000,000 or more: OVERBUDGET.
  6. Run the program and compare: MATCH or MISMATCH.

### The language

- A program is a graph. Each UOp is a triple (op, src, arg): the operation, the ordered sources, and data that is not a node.
- Matching triples are the same node. So `%y = add %x %x` is the same node as `%s` above. This is hash-consing (هش‌کانسینگ): build every node through a cache, so two equal nodes are the same object.
- DEF token: `%x=` or `%x =`. Both forms are one token.
- REF token: `%` then one or more ASCII letters, digits or underscores, like `%x` or `%0`.
- INT token: decimal `-?[0-9]+` or hex `0x[0-9a-fA-F]+`. Leading zeros are fine.
- BOOL token: `true` or `false`.
- OP token: a lowercase op name from the op list below.
- ATTR token: one `key=value` with no spaces inside.
- The other tokens are `[`, `]` and EOF.
- The grammar:

```
file    := binding+ EOF
binding := DEF rhs
rhs     := OP atom* ATTR* | atom
atom    := REF | INT | BOOL | '[' atom* ']'
```

- A newline is just whitespace. A binding ends where the next DEF or EOF starts, not at the end of a line.
- There are no nested `(op ...)` forms and no `{ ... }` blocks. A source is a name, a literal, or a `[...]` stack.
- A constant is written as its literal, like `7` or `true`. Never as `const 7`.
- Attributes come after all sources. Keys are unique and can come in any order.
- `[1 2]` and `stack 1 2` build the same node.
- `[]` with nothing inside is the scalar shape marker. Its dtype is void.
- `%y = %x` fits the grammar, since rhs can be a single atom. It gives a second name to the same node.
- Everything is case-sensitive ASCII. `#` starts a comment that runs to the end of the line.
- Each name is defined once. Defining a name twice is REJECTED.

### Test file rules

- The file ends with exactly one `assert`. Nothing may use the assert as a source.
- The assert's left side is the program's return value. In week 1 it must be a scalar.
- The right side is a literal, or a stack of literals, with the same dtype and shape as the left side. Since the left side is a scalar in week 1, it is one literal.
- Every node must be reachable (دسترس‌پذیر) from the assert. The walk goes into call bodies and through unused call arguments. A node that the walk never reaches makes the file REJECTED.

### Dtypes and shapes

- Week 1 has two dtypes, i32 and bool. Void is only for `[]`.
- Shapes have rank 0 (a scalar) or rank 1 (a vector). Only `stack` makes a vector.
- ALU ops (cast to where in the list below) take scalars only. So `add [1 2] [3 4]` is REJECTED.
- "Same dtype" below means all inputs and the result share the dtype.
- i32 math wraps on overflow (سرریز), as 32-bit two's complement (مکمل دو). So 2147483647 + 1 is -2147483648.

### The ops

- `const`: a literal. Its dtype is the literal's type. Its shape is scalar.
- `param`: a function input, written `param [] slot=k dtype=t addrspace=ALU`. Week 1 needs `addrspace=ALU` and the scalar shape `[]`. `slot` is an unsigned decimal.
- `param` can take optional limits as a second source: `param [] [0 2] slot=0 dtype=i32 addrspace=ALU`. The limits are literals of dtype t, with the low one not above the high one.
- `call`: `call %f a0 a1 ...`. The body f comes first, then the arguments for slot 0, slot 1, and so on. Extra unused slots are fine.
- Inside f there is one param node per used slot. Each used slot needs an argument that matches the param's dtype, shape and address space (all ALU in week 1). The argument's bounds must fit inside the param's limits.
- Call arguments and the return value are scalars. The call's result has the dtype, shape and bounds of f.
- `stack`: adds a leading axis. All inputs share dtype and shape. In week 1 the inputs are scalars, so the result is a vector of length n.
- `index`: `index %v %i`. v is a vector and i is a scalar i32. The result has v's dtype and is a scalar. The PDF allows one index per axis. In week 1 a vector has one axis, so there is one index.
- `index` must be safe: the bounds of i must fit inside [0, n - 1]. Otherwise the file is REJECTED.
- `cast`: `cast %x dtype=t`. i32 to bool gives true for any value that is not 0. bool to i32 gives 0 or 1.
- `add`, `mul`, `max`: same dtype.
- `div`: i32 only. Floor division (تقسیم رو به پایین: the answer is rounded down, toward minus infinity). So `div -7 2` is -4, not -3 as in C. Dividing by 0 gives -1.
- `mod`: i32 only. It is x - y * floor(x / y). So `mod -7 2` is 1 and `mod 7 -2` is -1. The result takes the sign of y. Mod by 0 gives x.
- `xor`: bitwise exclusive or. Same dtype.
- `shl`: i32 only. Shift x left by y mod 32. So `shl 1 33` is 2.
- `cmplt`: x < y. x and y share a dtype. The result is bool.
- `where`: `where %p %x %y`. p is bool. The result is x when p is true, else y. x and y share a dtype.
- `assert`: see the test file rules above.
- Python's `//` and `%` already round down, so they match `div` and `mod`. You only need to handle 0 and wrap the result to 32 bits.

### Bounds

- Every node has bounds (کران‌ها): the smallest and largest value it can have. Below, x is in [a, b] and y is in [c, d], ends included.
- A hull (پوش: the smallest range that covers a set of numbers) of {2, 5, 3} is [2, 5].
- I is the full i32 range. i32 bounds that overflow widen to I.
- bool bounds are [0, 0] if the value is always 0, [1, 1] if it is never 0, else [0, 1].
- `const` v: [v, v].
- `param`: its limits, or I when it has none.
- `call`: the bounds of the body f, worked out with the param limits.
- `stack`: the hull of the element bounds. `[]` has bounds I.
- `index`: the bounds of the whole vector v, not of the one element.
- `cast`: the bounds of x, turned into bool bounds when casting to bool.
- `add`: [a + c, b + d].
- `mul`: the hull of ac, ad, bc and bd.
- `max`: [max(a, c), max(b, d)].
- `div`: when y is fixed (c = d), the hull of the quotients of a and b. Else I.
- `mod`: when y can vary, I. When y is fixed at 0, the bounds of x. When y is fixed and not 0, the hull of the remainders of a and b if a and b have the same floor quotient. Else [0, y - 1] for a positive y, or [y + 1, 0] for a negative y.
- `xor`: exact when both sides have a single value. Else I.
- `shl`: the hull of a * 2^k and b * 2^k over every possible k.
- `cmplt`: [1, 1] if b < c. [0, 0] if a >= d. Else [0, 1].
- `where`: the bounds of the chosen side when p has a single value. Else the hull of both sides.
- `assert`: I.
- Bounds drive two checks: an index must fit its vector, and a call argument must fit its param limits.
- The PDF's example: in `index [10 20 30] %i`, bounds of [0, 2] for `%i` are safe. Bounds of [0, 3] make the file REJECTED, even if the only call passes 1.

### Cost

- `const`, `param` and `assert` cost 0.
- `index` and `[]` cost 1.
- `stack` and the ALU ops cost N, the number of elements in the result. In week 1 that is 1 for an ALU op and n for a stack of n.
- `call` costs 1 + C(f), where C(f) is the cost of its body.
- To get the cost, start at the assert and add up each node once. Follow call arguments, but do not go into call bodies. C(f) pays for the body. The `[]` and limit stacks under a param are nodes too, so they count.
- Work out the cost on the parsed graph, before any rewrite. The PDF's example: with `%a = add 2 4` and `%b = add 3 3`, `mul %a %a` costs 2 (one shared add), but `mul %a %b` costs 3 (two adds). Both are 36.
- Save C(f) for each body the first time you work it out (یادسپاری, memoization). Nested calls can make the cost grow 2 times per level. Without saving, working out the cost would take as long as running the program.

### Running a program

- Run a program only after all checks pass. Since every index is proven safe and every op has a defined result, nothing can fail while running.
- Run it by rewriting: apply rules to the graph again and again until the assert's left side is a single const. Folding `add 2 3` into `5` is one such rule.
- A call is substitution (جایگذاری): replace each param in the body with its argument. The call node becomes the new body. This is the lambda calculus part of the week.
- Do not substitute inside a nested call's body. Rewrite the nested call's arguments, but leave its body as it is. The params in that body belong to the inner call.
- This rule matters because of hash-consing. `param [] slot=0 dtype=i32 addrspace=ALU` in two different bodies is the same node. Stopping at bodies is the only thing that keeps them apart.
- So there are two ways to walk the graph. The full walk goes into call bodies. Use it for the reachability rule. The scoped walk follows call arguments but stops at call bodies. Use it to find the params of a body, to work out cost, and to substitute.

### Code to write

- `uop.py`: the UOp class with `op`, `src` (a tuple of UOps) and `arg`, built through a cache. Computed properties: `dtype`, `shape`, `bounds` and `cost`.
- `parse.py`: a tokenizer and a parser for the grammar above. Keep a table from each `%name` to its UOp.
- `check.py`: every REJECTED rule. Each failure raises an error with a clear message, and `./compile` turns it into REJECTED.
- `rewrite.py`: a pattern matcher plus `graph_rewrite`, which rewrites bottom up and repeats until nothing changes.
- `interp.py`: the folding rules for each op, and call substitution with the scoped walk.
- `compile`: the command. It reads each file, runs the checks in the order above, and prints the outcome line. Make it a uv script with `#!/usr/bin/env -S uv run --script` as its first line, so `./compile` runs as it is.
- Optional: a printer that turns a graph back into UIR text. It helps with debugging and with checking what a rewrite did. The grader does not use it.
- Optional: simplify rules such as `x * 1` to `x`, `x + 0` to `x`, and `cmplt` with bounds [1, 1] to `true`. The grader only sees the outcome, so these are for learning and for later weeks.

### Tests

Write these as `.uir` files in `tests/week1/` before the compiler code. Each file has one assert, so each check below is its own file.

MATCH:

- `add_fold.uir`: `%sum = add 2 3`, then `%t = assert %sum 5`.
- The call example at the top of this week.
- A body that calls another body with a different argument for the same slot. If substitution goes into the inner body, you get 12 instead of 28:

```
%x = param [] slot=0 dtype=i32 addrspace=ALU
%g = mul %x %x
%inner = call %g 5
%f = add %x %inner
%v = call %f 3
%t = assert %v 28
```

- A safe index:

```
%i = param [] [0 2] slot=0 dtype=i32 addrspace=ALU
%e = index [10 20 30] %i
%v = call %e 1
%t = assert %v 20
```

- `div -7 2` is -4. `mod -7 2` is 1. `mod 7 -2` is -1.
- `div 5 0` is -1. `mod 5 0` is 5.
- `add 2147483647 1` is -2147483648. `div -2147483648 -1` is -2147483648.
- `shl 1 33` is 2.
- `cast 5 dtype=bool` is true. `cmplt` and `where` pick the right side.
- `%y = add %x %x` next to `%s = add %x %x` is one node, so the file still passes the reachability rule.

MISMATCH:

- `mismatch_add.uir`: `%s = add 2 3`, then `%t = assert %s 6`.

REJECTED:

- `rejected_assert_dtype_mismatch.uir`: `%t = assert 3 true`.
- `add` of an i32 and a bool.
- `add [1 2] [3 4]`, since ALU ops take scalars.
- `[[1 2] [3 4]]`, since it has rank 2.
- The safe index test above, with limits `[0 3]` instead of `[0 2]`.
- A call whose argument does not fit the param limits.
- A name that is used but never defined. A name that is defined twice.
- A binding that nothing reaches.
- An assert that is not last, or that is used as a source.
- `const 7` written as an op.

OVERBUDGET:

- A file over 4096 bytes. A long comment is enough.
- 100 nodes, for example a stack of 99 different numbers.
- 300 source edges with few nodes, for example a stack of 300 copies of `1`.
- A cost of 1,000,000 or more. Make each body add two calls to the body before it, with different arguments so hash-consing does not merge them. The cost doubles at each level, so about 20 levels pass the limit while staying under 100 nodes. A small script can write this file for you.

Run them all with `./compile tests/week1/*.uir` and check each outcome against its file name prefix.

### Gaps in the spec

The PDF does not answer these. Pick an answer, write it under Notes, and check EdStem once it opens.

- Which outcome a syntax error gets. REJECTED fits "invalid before execution".
- What `add`, `mul`, `max` and `xor` mean on bool. One reading: treat false as 0 and true as 1, compute, then any result that is not 0 is true. Then `add` is OR and `mul` is AND.
- Whether an INT literal outside the i32 range, like `0xffffffff`, wraps to a negative number or is REJECTED.
- Whether the 100 node limit counts nodes after hash-consing. The PDF says matching triples share a node, so after seems right.
- Whether a name can be used before the binding that defines it. Treat it as REJECTED for now.
- What a param that no call binds should give, like `%t = assert %x 5` with `%x` a param. REJECTED seems right, since it has no value. The scoped walk from the assert finds these params.
- Whether a node used both inside a body and outside it is counted twice in the cost.

### Notes

- The parser is a small recursive descent parser (تجزیه‌گر بازگشتی نزولی: one function for each kind of thing, and the functions call each other for nested parts). This is the main topic of Eli's parts 2 and 3. The only nesting in week 1 is `[...]`, so the atom function calls itself when it sees `[`.
- Cut the text into tokens first, like the scanner in Eli's part 7. Then the parser never looks at single characters. When the tokenizer reads `%name`, it looks past any spaces for `=`. If it finds one, the token is a DEF. Otherwise it is a REF.
- The interpreter is the idea of Eli's part 4: keep the same front end, but compute values instead of making code. Here it is even simpler, since running is just more rewrite rules on the same graph.
- Eli's part 14 shows how hard types get when code is made while parsing. Here every node knows its dtype before anything runs, and mixed dtypes are simply REJECTED.

Read:

- [letsbuildacompiler](https://github.com/eliben/letsbuildacompiler) parts 2, 3, 7 and 13: the code, the tests, and the matching sections of its TUTORIAL.md, for the parser and the name table.
- [xl0: the pattern matcher, with examples](https://xl0.github.io/tinygrad-notes/patternmatcher.html)
- [mesozoic-egg: pattern matcher notes](https://mesozoic-egg.github.io/tinygrad-notes/20241112_pm.html)
- [mesozoic-egg: UOps overview](https://mesozoic-egg.github.io/tinygrad-notes/uops-doc.html)
- [Crafting Interpreters](https://craftinginterpreters.com/), if writing an interpreter is new to you

## Week 2: Memory, C renderer, runtime

- [ ] Done

Example from the course page:

```
%buf = extern [] slot=0 dtype=i32
%write = store %buf 7
%ready = after %buf %write
%value = load %ready
%test = assert %value 7
```

The STORE becomes `buf0[0] = 7;` and the LOAD reads it back. AFTER is what says the load must come after the store.

Code to write:

- Ops: BUFFER, ALLOC, SHRINK, LOAD, STORE, AFTER. The course page examples write BUFFER as `extern` (an external buffer). The gist still calls it BUFFER.
- New properties: `addrspace` (GLOBAL or ALU), `accesses` (which nodes touch a buffer), and `storage_base` (which buffer a view really points to).
- A checker that rejects bad programs. Loads and stores on the same buffer must have a fixed order through AFTER, and every access must be in bounds. Use the bounds from week 1 to prove this.
- `toposort.py`: orders the graph so every node comes after its inputs (مرتب‌سازی توپولوژیک).
- `render_c.py`: turns the sorted list into one C function with no loops.
- `runtime_cpu.py`: writes the C to a file, builds it with `clang -shared -O2`, loads it with Python ctypes, and calls it on real memory.

Tests:

- Copy one buffer to another.
- Add two buffers into a third.
- Reject a load that could happen before its store.
- Reject an out of bounds index.
- Output test: the C for the example above matches the expected text line by line.
- Run every week 1 test both in the interpreter and as C. When the two disagree, one of them has a bug.

Notes:

- Eli's test harness gives the WASM program its input and output from the outside, as imported functions (part 10). Memory works the same way here. The runtime makes the memory for each BUFFER slot and passes a pointer to the C function.
- In part 6 Eli went back to running the output as soon as the code got complex, because checking the text alone did not prove the code works. Get the C running early in the week, before you add all six ops.

Read:

- [Python ctypes docs](https://docs.python.org/3/library/ctypes.html)
- The machine code and memory chapters of "Computer Systems: A Programmer's Perspective" (the 15-213 book the course assumes you know)

## Week 3: Loops

- [ ] Done

Example from the course page:

```
%buf = extern 3 slot=0 dtype=i32
%i = range 3 slot=0
%write = store (index %buf %i) %i
%done = end %write %i
%test = assert (after %buf %done) [0 1 2]
```

The C for this could look like:

```c
for (int i = 0; i < 3; i++) {
  buf0[i] = i;
}
```

Code to write:

- Ops: RANGE (src is the end, arg is the name) and END (srcs are the passthrough value and the range).
- New properties: `ranges` (which loops a node is inside) and `ended_ranges`.
- A rewrite pass that puts ranges in a valid order, so the renderer knows where each loop opens and closes.
- Make the renderer print a `for` loop for each RANGE and close it at END.
- Write a 256x256 matmul and a 2D convolution by hand, as graphs with ranges.

Tests:

- Matmul and conv match numpy.
- A loop of length 0 does nothing.
- Nested loops work.
- Output test: the C for the example above.

Notes:

- Eli's part 5 makes loops before his language has real conditions, only to learn how each kind of loop looks in the output. Do the same here. Get one RANGE with a constant end printing as a `for` loop before you start on matmul.
- In part 5 Eli has to declare loop variables at the top of the function, because a WASM value cannot cross into a block. C has a softer form of this: a value made inside a loop is gone once the loop closes. Anything needed after END, such as a running sum, must be declared before the loop or stored in memory. Next week's REDUCE is built on this.

Read:

- tinygrad `renderer/cstyle.py` and `runtime/ops_cpu.py`
- [Horace He: Making Deep Learning Go Brrrr](https://horace.io/brrr_intro.html), for why memory traffic matters

## Week 4: Rangeify, reduce, materialization

- [ ] Done

Example from the course page:

```
%values = add [1 2 3] (expand 1 3)
%sum = reduce %values op=add pop=1
%test = assert %sum 9
```

EXPAND turns the single 1 into `[1 1 1]`, so `%values` is `[2 3 4]` and the sum is 9.

Code to write:

- Allow rank 1 shapes on ALU ops, so one node can mean a whole vector.
- Ops: REDUCE (an op and how many axes to reduce), STAGE (a temporary buffer), EXPAND.
- `rangeify.py`: start from the outputs, make one RANGE per output axis, and push ranges backward through every op. At the end no op has a shape, and the program is in the week 3 form.
- REDUCE becomes a loop with an accumulator (انباشتگر: a variable that adds up values as the loop runs).
- A materialization rule (مادی‌سازی: deciding which middle results are written to memory). Start simple: write a result to a STAGE buffer if more than one consumer uses it or if it is a reduce output. Each cut starts a new kernel, so the output is now a list of kernels.

Tests:

- Sum and max over a vector.
- Broadcasting with EXPAND.
- A result used twice is computed once.
- The gemm example from the syllabus works.

Notes:

- In part 13 Eli could not count a call's arguments ahead of time, because the code for each argument was already written out while parsing. Materialization has the same trap: you cannot decide to STAGE a node until you know all of its consumers. First count the consumers of every node in one pass over the whole graph, then decide.

Read:

- [Lukasz Stafiniak: A Range Is Not Its Shape](https://lukstafi.github.io/notes/a-range-is-not-its-shape.html)
- [mesozoic-egg: kernel fusion](https://mesozoic-egg.github.io/tinygrad-notes/20250117_fusion.html)
- [The Halide paper](https://people.csail.mit.edu/jrk/halide12/halide12.pdf), on the choice between computing again and storing
- tinygrad `schedule/rangeify.py`

## Week 5: Movement ops

- [ ] Done

Example from the course page:

```
%matrix = reshape [1 2 3 4] [2 2]
%transposed = permute %matrix [1 0]
%test = assert (index %transposed 1 0) 2
```

`%matrix` is `[[1 2] [3 4]]`. After the permute it is `[[1 3] [2 4]]`, so row 1, column 0 is 2.

Code to write:

- Allow rank 2 and higher.
- Ops: RESHAPE, PERMUTE, PAD. STACK now takes any input, and SHRINK can take STACKs.
- Each op is an index rule in rangeify, not a copy. RESHAPE splits or joins index math with DIV and MOD. PERMUTE swaps ranges. PAD adds a WHERE that gives 0 outside the valid area.
- Build FLIP from the other ops.
- Rebuild matmul and conv from movement ops plus MUL and REDUCE. Compare with your week 3 versions.
- SIN, LOG2, EXP2, SQRT built from ADD and MUL with Taylor series (سری تیلور: writing a function as a sum of powers).

Tests:

- Transpose, pad, and reshape after permute.
- Conv made from movement ops.
- SIN accuracy over a range of inputs.

Read:

- [MiniTorch](https://minitorch.github.io/), the modules on strides and broadcasting
- tinygrad `uop/decompositions.py`, for how they approximate SIN and EXP2

## Week 6: Autodiff and the Tensor API

- [ ] Done

Example from the course page:

```
# raw f32 data in data/x.bin: 1.0 2.0 3.0 4.0
%result = {
  %x = extern [2 2] slot=0 dtype=f32 url=data/x.bin
  # broadcast to [2 2] and promote i32 to f32
  %loss = reduce (mul (mul %x %x) [42 27]) op=add pop=2
  %out = after %x (store %x (gradient %loss %x))
}
%test = assert %result [[84.0 108.0] [252.0 216.0]]
```

`data/x.bin` holds four raw f32 numbers, so `%x` is `[[1 2] [3 4]]`. `[42 27]` is an i32 array. It is copied to every row to make `[[42 27] [42 27]]`, and turned into f32. The loss is the sum of `x * x * w`, so the gradient for each x is `2 * x * w`. That gives 2*1*42 = 84, 2*2*27 = 108, 2*3*42 = 252, and 2*4*27 = 216. The STORE writes the gradient back into `%x`. The block `{ ... }` seems to take the value of its last line, so `%result` is `%x` after the store.

Code to write:

- `tensor.py`: a small Tensor class with `+`, `@`, `.sum()`, `.reshape()`, `.relu()`, `.softmax()`, and so on. Each method only builds UOps.
- Ops: GRADIENT and DETACH. `grad.py` walks backward from the loss and builds the gradient graph with one rule per op. It only works on pure shape graphs, not on STORE, CALL, AFTER, RANGE, or END.
- BUFFER gets `url=` and `sha256=`, so it can load weights and check them. In the example `url=data/x.bin` is a file on disk with raw f32 bytes, so `url=` must take a local path too.
- Syntactic sugar (شکر نحوی: shorter ways to write the same thing) and lexical scopes (حوزه‌ی واژگانی: names that only exist inside their block). The example shows a `{ ... }` block with its own names, `mul` on two different shapes with no EXPAND, and i32 mixed with f32 with no CAST. Turn each one into the plain ops you already have, so the rest of the compiler does not change.
- FLOPS counting, to measure speed.
- Train MNIST. Then run a small Qwen model with safetensors weights.

Tests:

- Gradients match a finite difference check (nudge an input a tiny bit and see how the output changes).
- MNIST accuracy goes above 95%.
- Qwen gives the same tokens as the reference.

Read:

- [Karpathy: micrograd](https://github.com/karpathy/micrograd) and his video "The spelled-out intro to neural networks and backpropagation"
- tinygrad `gradient.py` and `nn/`
- [Qwen models on Hugging Face](https://huggingface.co/Qwen)

## Week 7: Fast CPU code

- [ ] Done

Code to write:

- Ranges get an axis type: LOOP, UPCAST, or THREAD.
- `opt.py`: rewrites that change loop shape but not results. Tiling splits a loop into blocks that fit in cache. Upcasting unrolls a small loop so clang can use vector instructions. THREAD runs an outer loop on many cores. On a Mac use pthreads, since Apple clang has no OpenMP by default.
- A timer and a small search that tries a few options per kernel and keeps the fastest.

Tests:

- Results are the same before and after every optimization.
- Matmul reaches a fair share of your CPU's peak speed.

Read:

- [Simon Boehm: Fast matrix multiply on CPU](https://siboehm.com/articles/22/Fast-MMM-on-CPU)
- [tinygrad docs: speed](https://docs.tinygrad.org/developer/speed/)
- [mesozoic-egg: upcast notes](https://github.com/mesozoic-egg/tinygrad-notes/blob/main/upcast2.md)

## Week 8: GPUs

- [ ] Done

Code to write:

- Axis types GLOBAL and LOCAL. The renderer prints `blockIdx` and `threadIdx` for these instead of `for` loops.
- Address space LOCAL, which becomes `__shared__` memory.
- `render_cuda.py`, reusing most of the C renderer.
- `runtime_cuda.py`: compile with NVRTC, load and launch with the CUDA driver API through [cuda-python](https://pypi.org/project/cuda-python/).

Tests:

- Every old test also passes on the GPU.
- GPU matmul matches CPU matmul.

Notes:

- Eli kept Crenshaw's whole front end and only changed what it makes, from 68000 assembly to WASM. Week 8 is the same move. Nothing above the renderer and the runtime should need to change. If something does, write down why.

Read:

- [Simon Boehm: How to optimize a CUDA matmul kernel](https://siboehm.com/articles/22/CUDA-MMM)
- "Programming Massively Parallel Processors" by Hwu, Kirk, and El Hajj, chapters 1 to 6

## Week 9: Fast GPU kernels

- [ ] Done

Code to write:

- Tensor cores (هسته‌های تنسوری). Detect a matmul shape inside a kernel and replace the inner loops with a WMMA op that the renderer prints as the special instruction.
- Shared memory tiling and upcasting for GEMM and conv on the GPU.
- Flash attention: attention as one kernel that never writes the full attention matrix.

Tests:

- Matmul speed compared to torch, in the test script only.
- Attention output matches the slow version.

Read:

- [The FlashAttention paper](https://arxiv.org/abs/2205.14135)
- The WMMA section of the NVIDIA CUDA C++ Programming Guide

## Week 10: Many GPUs

- [ ] Done

Code to write:

- A device field on BUFFER and a copy op between devices.
- Sharding (تقسیم‌بندی: splitting one tensor along an axis across devices). Each op runs on each piece. A reduce over the split axis becomes a copy plus a reduce.
- No changes in the kernel compiler, only in scheduling.
- Test with two fake CPU devices first, before renting two GPUs.

Read:

- tinygrad `multi.py`
- [Hugging Face: The Ultra-Scale Playbook](https://huggingface.co/spaces/nanotron/ultrascale-playbook), the parts on data and tensor parallelism

## Week 11: Real models

- [ ] Done

- Run a real LLM fast on GPU.
- Train a small model from scratch with autodiff across GPUs.
- Read tinygrad `examples/` and [Karpathy's nanoGPT](https://github.com/karpathy/nanoGPT) as models to copy.

## Weeks 12 to 14: Final project

- [ ] Done

- Extend the compiler with something of your own, such as implementing a paper or porting to Apple Metal.

***

## What you build

By the end you have a small ML framework with a compiler inside it, like a mini tinygrad.

- From the outside it looks like PyTorch: a Tensor class, `x @ w + b`, `.relu()`, `.softmax()`, and backward for gradients.
- Under the hood it turns the model into a graph of UOps, simplifies it with a rewrite engine, splits it into kernels, writes C or CUDA for each kernel, compiles it, and runs it on CPU or one or more NVIDIA GPUs.
- Final targets: train MNIST, run a real LLM like Qwen on GPU, get matmul, conv, and attention close to PyTorch and cuBLAS speed, and train a small LLM across several GPUs.

## Key sources

- [10-411 course page](https://10-411.com/): schedule, grading, rules, and the weekly assignment PDFs.
- The weekly assignment PDFs: the spec for each week. Copies are in `assignments/`. When a PDF and anything else disagree, the PDF wins.
- [Technical syllabus by geohot](https://gist.github.com/geohot/4768597d9dc536446ee2d5de1f29e89d): background on the ops for each week and the `.uir` text format.
- [tinygrad repo](https://github.com/tinygrad/tinygrad): the reference design. Key files are `uop/ops.py`, `uop/symbolic.py`, `schedule/rangeify.py`, and `renderer/cstyle.py`.

## Notes before starting

- The op names follow the syllabus, not tinygrad. Some differ: STACK, INDEX, PARAM, CALL, ALLOC, SHRINK, AFTER, END, STAGE.
- Week 1 needs an interpreter (مفسر: a program that runs the graph directly, without making C), not only graph simplification.
- On a Mac, weeks 1 to 7 run locally with clang. CUDA needs an NVIDIA GPU, so weeks 8 to 10 need a rented GPU, ideally an RTX 3080 class card like the course uses.
- The course page puts CPU speed in week 7 and GPUs in week 8. The gist has them the other way around. This guide follows the course page.

## How each week works

- Each week below is a starting outline, not the final task list. Before starting a week, chat with Claude to work out exactly what to build.
- Check the week's Done box when its tests pass.
- Write about 10 tests first, as `.uir` files that end with an assert and are named by their expected outcome. The course does the same: tests are due Monday, the compiler on Wednesday.
- Then write compiler code until every old and new test passes.
- Check numbers against numpy inside the test runner only. Never use numpy inside the compiler.
- Keep the code small. The syllabus warns that messy code compounds (انباشته می‌شود) and you will not finish.
- Python is the easiest language for this, since every reference below is in Python.
