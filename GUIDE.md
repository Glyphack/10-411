# 10-411 Compilers for Machine Learning: Build Guide

A week by week plan for building an ML compiler from scratch, following the CMU course at [10-411.com](https://10-411.com/).

## Week 0: Setup

- [ ] Done

- Make the repo with a `tests/` folder of `.uir` files and a runner that runs all of them.
- Read the whole syllabus gist and the course page.
- Skim the tinygrad repo so you know where the key files are.

## Week 1: UOps, rewrites, interpreter

- [ ] Done

Code to write:

- `uop.py`: a UOp class with `op`, `src` (a tuple of UOps), and `arg`. Make it hash-consed (هش‌کانسینگ): build every node through a cache, so two equal nodes are the same object.
- Computed properties: `dtype` (void, bool, i32, f32), `shape`, `cost`, and `bounds` (کران‌ها: the smallest and largest value a node can have).
- Ops: CONST, PARAM, CALL, STACK, INDEX, CAST, RECIP, ADD, MUL, MAX, XOR, CMPLT, SHL, DIV, MOD, WHERE, ASSERT.
- `parse.py`: reads `.uir` text into UOps. A printer does the reverse.
- `rewrite.py`: a pattern matcher plus `graph_rewrite`, which rewrites bottom up and repeats until nothing changes.
- `symbolic.py`: constant folding, `x*1`, `x+0`, `x*0`, and bounds-based rules. For example, `x < 10` is always true if x is between 0 and 5.
- `interp.py`: runs a program by rewriting it until it becomes a single CONST. CALL works by replacing each PARAM with its argument.

Tests:

- Folding gives the right constant.
- ASSERT fails on wrong programs.
- CALL with PARAMs works.
- INDEX into a STACK works.
- DIV and MOD on negative numbers match C rules.

Read:

- [xl0: the pattern matcher, with examples](https://xl0.github.io/tinygrad-notes/patternmatcher.html)
- [mesozoic-egg: pattern matcher notes](https://mesozoic-egg.github.io/tinygrad-notes/20241112_pm.html)
- [mesozoic-egg: UOps overview](https://mesozoic-egg.github.io/tinygrad-notes/uops-doc.html)
- [Crafting Interpreters](https://craftinginterpreters.com/), if writing an interpreter is new to you

## Week 2: Memory, C renderer, runtime

- [ ] Done

Code to write:

- Ops: BUFFER, ALLOC, SHRINK, LOAD, STORE, AFTER.
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

Read:

- [Python ctypes docs](https://docs.python.org/3/library/ctypes.html)
- The machine code and memory chapters of "Computer Systems: A Programmer's Perspective" (the 15-213 book the course assumes you know)

## Week 3: Loops

- [ ] Done

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

Read:

- tinygrad `renderer/cstyle.py` and `runtime/ops_cpu.py`
- [Horace He: Making Deep Learning Go Brrrr](https://horace.io/brrr_intro.html), for why memory traffic matters

## Week 4: Rangeify, reduce, materialization

- [ ] Done

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

Read:

- [Lukasz Stafiniak: A Range Is Not Its Shape](https://lukstafi.github.io/notes/a-range-is-not-its-shape.html)
- [mesozoic-egg: kernel fusion](https://mesozoic-egg.github.io/tinygrad-notes/20250117_fusion.html)
- [The Halide paper](https://people.csail.mit.edu/jrk/halide12/halide12.pdf), on the choice between computing again and storing
- tinygrad `schedule/rangeify.py`

## Week 5: Movement ops

- [ ] Done

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

Code to write:

- `tensor.py`: a small Tensor class with `+`, `@`, `.sum()`, `.reshape()`, `.relu()`, `.softmax()`, and so on. Each method only builds UOps.
- Ops: GRADIENT and DETACH. `grad.py` walks backward from the loss and builds the gradient graph with one rule per op. It only works on pure shape graphs, not on STORE, CALL, AFTER, RANGE, or END.
- BUFFER gets `url=` and `sha256=`, so it can download weights and check them.
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

- [10-411 course page](https://10-411.com/): schedule, grading, rules.
- [Technical syllabus by geohot](https://gist.github.com/geohot/4768597d9dc536446ee2d5de1f29e89d): the exact ops for each week and the `.uir` text format. This is the spec.
- [tinygrad repo](https://github.com/tinygrad/tinygrad): the reference design. Key files are `uop/ops.py`, `uop/symbolic.py`, `schedule/rangeify.py`, and `renderer/cstyle.py`.

## Notes before starting

- The op names follow the syllabus, not tinygrad. Some differ: STACK, INDEX, PARAM, CALL, ALLOC, SHRINK, AFTER, END, STAGE.
- Week 1 needs an interpreter (مفسر: a program that runs the graph directly, without making C), not only graph simplification.
- On a Mac, weeks 1 to 7 run locally with clang. CUDA needs an NVIDIA GPU, so weeks 8 to 10 need a rented GPU, ideally an RTX 3080 class card like the course uses.
- The course page puts CPU speed in week 7 and GPUs in week 8. The gist has them the other way around. This guide follows the course page.

## How each week works

- Each week below is a starting outline, not the final task list. Before starting a week, chat with Claude to work out exactly what to build.
- Check the week's Done box when its tests pass.
- Write about 10 tests first, as `.uir` files that use ASSERT. The course does the same: tests are due Monday, the compiler on Wednesday.
- Then write compiler code until every old and new test passes.
- Check numbers against numpy inside the test runner only. Never use numpy inside the compiler.
- Keep the code small. The syllabus warns that messy code compounds (انباشته می‌شود) and you will not finish.
- Python is the easiest language for this, since every reference below is in Python.
