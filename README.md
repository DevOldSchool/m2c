# `m2c` Decompiler
`m2c` ("*Machine code to C*") is a decompiler for 32-bit MIPS, ARM, PowerPC and SuperH assembly that produces C code, with partial support for C++.

This project, initially named `mips_to_c`, has the goal to support decompilation projects, which aim to write source code that yields byte-identical output when compiled with a particular build system.
It originally targeted popular compilers of the late 1990's, but it also works well with newer compilers or hand-written assembly.

`m2c` is often used in decompilation workflows with [`splat`](https://github.com/ethteck/splat), [`asm-differ`](https://github.com/simonlindholm/asm-differ), and [`decomp-permuter`](https://github.com/simonlindholm/decomp-permuter).
Its focus on finding "matching" C source differentiates it from other decompilation suites, such as IDA or Ghidra.
Right now the decompiler is fairly functional, though it sometimes generates suboptimal code (especially for loops).

The input is expected to match the GNU `as` assembly format, produced by tools like [`spimdisasm`](https://github.com/Decompollaborate/spimdisasm).
See the `tests/` directory for some example input and output.

[An online version is also available](https://simonsoftware.se/other/m2c.html).

## Usage

```bash
python3 m2c.py [options] [-t <target>] [--context <context file>] [-f <function name>] <asmfile>...
```

Run with `--help` to see which options are available.

Context files provided with `--context` are parsed and cached, so subsequent runs with the same file are faster. The cache for `foo/bar.c` is stored in `foo/bar.m2c`. These files can be ignored (added to `.gitignore`), and are automatically regenerated if context files change. Caching can be disabled with the `--no-cache` argument.

### Target Architecture / Compiler / Language

`m2c` has support for MIPS, ARM, PowerPC and SuperH assembly.
It also has some compiler-specific heuristics and language-specific behavior.
For example, it can demangle C++ symbol names as used by CodeWarrior.

Collectively, the output's platform, compiler, and source language are referred to as a *target*.
They can be passed to m2c with the `-t` (or `--target` flag), as such: `--target mips-ido-c`.

The following platforms are supported:
- `mips`: MIPS (with O32 ABI)
- `mipsel`: MIPS (with O32 ABI, little endian)
- `mipsee`: MIPS (with eabi64, little endian)
- `ppc`: PowerPC (big endian)
- `arm`: ARM (little endian)
- `gba`: ARM (with APCS, little endian)
- `sh2`: SuperH (big endian)

The following compilers are supported:
- `ido`: Integrated Development Option (MIPS compiler from SGI)
- `gcc`: GNU C Compiler
- `mwcc`: MetroWerks CodeWarrior toolchain (`mwccecpp.exe`)

Supported languages are `c` and `c++`.

### Multiple functions

By default, `m2c` decompiles all functions in the text sections from the input assembly files.
`m2c` is able to perform a small amount of cross-function type inference, if the functions call each other.

You can limit the function(s) that decompiled by providing the `-f <function name>` flags (or the "Function" dropdown on the website).

### Global Declarations & Initializers

When provided input files with `data`, `rodata`, and/or `bss` sections, `m2c` can generate the initializers for variables it knows the types of.

Qualifier hints such as `const`, `static`, and `extern` are based on which sections the symbols appear in, or if they aren't provided at all.
The output also includes prototypes for functions not declared in the context.

`m2c` cannot generate initializers for structs with bitfields (e.g. `unsigned foo: 3;`) or for symbols that it cannot infer the type of.
For the latter, you can provide a type for the symbol the context.

This feature is controlled with the `--globals` option (or "Global declarations" on the website):

- `--globals=used` is the default behavior, global declarations are emitted for referenced symbols. Initializers are generated when the data/rodata sections are provided.
- `--globals=none` disables globals entirely; only function definitions are emitted.
- `--globals=all` includes all of the output in `used`, but also includes initializers for unreferenced symbols. This can be used to convert data/rodata files without decompiling any functions.

### Struct Field Inference

By default, `m2c` can use type information from decompiled functions to help fill in unknown struct fields.
This behavior can be disabled with `--no-unk-inference` ("Disable unknown struct/type inference" on the website).

For structs in the context, the following fields treated as "unknown" space that can be inferred:

- `char` arrays with a name starting with `unk_`, e.g. `char unk_10[4];`
- any field with a type that starts with `UNK_` or `M2C_UNK`, e.g. `UNK_TYPE4 foo;`

Currently, struct field inference only works on structs without bitfields or [unnamed union fields](https://gcc.gnu.org/onlinedocs/gcc/Unnamed-Fields.html).

The output will include declarations for any struct with at least one inferred field.

### Specifying stack variables

By default, `m2c` infers the types of stack (local) variables, and names them with the `sp` prefix based on their offset.

Internally, the stack is represented as a struct, so it is possible to manually specify the names & types of stack variables by providing a struct declaration in the context. `m2c` looks in the context for a struct with the tag name `_m2c_stack_<function name>` (e.g. `struct _m2c_stack_test` for a function `test()`).

The size of the stack must exactly match the detected frame size, or `m2c` will return an error.
If you run `m2c` with the `--stack-structs` option ("Stack struct templates" on the website), the output will include the inferred stack declaration, which can then be edited and provided as context by re-running `m2c`.

#### Example

Here is an example for specifying the stack for the `custom_stack` end-to-end test.

First, run `m2c` with the `--stack-structs` option to get the inferred struct for the `test()` function:

<details>
    <summary><code>python3 m2c.py tests/end_to_end/custom_stack/irix-o2.s -f test --stack-structs</code></summary>

```c
struct _m2c_stack_test {
    /* 0x00 */ char pad0[0x20];
    /* 0x20 */ s8 sp20;                             /* inferred */
    /* 0x21 */ char pad21[0x3];                     /* maybe part of sp20[4]? */
    /* 0x24 */ s32 sp24;                            /* inferred */
    /* 0x28 */ s32 sp28;                            /* inferred */
    /* 0x2C */ s8 sp2C;                             /* inferred */
    /* 0x2D */ char pad2D[0x3];                     /* maybe part of sp2C[4]? */
    /* 0x30 */ s8 sp30;                             /* inferred */
    /* 0x31 */ char pad31[0x3];                     /* maybe part of sp30[4]? */
    /* 0x34 */ s8 sp34;                             /* inferred */
    /* 0x35 */ char pad35[0x2];                     /* maybe part of sp34[3]? */
    /* 0x37 */ s8 sp37;                             /* inferred */
};                                                  /* size = 0x38 */

? func_00400090(s8 *);                              /* static */
s32 test(void *arg0);                               /* static */

s32 test(void *arg0) {
    s8 sp37;
    s8 sp34;
    s8 sp30;
    s8 sp2C;
    s32 sp28;
    s32 sp24;
    s8 sp20;
    s32 temp_t4;

    func_00400090(&sp37);
    func_00400090(&sp34);
    func_00400090(&sp30);
    func_00400090(&sp2C);
    func_00400090(&sp20);
    sp37 = arg0->unk0 + arg0->unk4;
    sp34 = arg0->unk0 + arg0->unk8;
    temp_t4 = arg0->unk4 + arg0->unk8;
    sp30 = temp_t4;
    sp20 = arg0->unk0 * sp37;
    sp24 = arg0->unk4 * (s16) sp34;
    sp28 = arg0->unk8 * temp_t4;
    if (sp37 != 0) {
        sp2C = arg0;
    } else {
        sp2C = &sp20;
    }
    return sp37 + (s16) sp34 + (s32) sp30 + *(s32 *) sp2C + sp24;
}
```
</details>

Now, based on the body of the `test()` function, we can make some guesses about the types of these variables, and give them more descriptive names:

```c
// Save this file as `test_context.c`
struct Vec {
    s32 x, y, z;
};

struct _m2c_stack_test {
    char pad0[0x20];
    struct Vec vec;
    struct Vec *vec_ptr;
    s32 scale_z;
    s16 scale_y;
    char pad36[1];
    s8 scale_x;
}; /* size 0x38 */

int test(struct Vec *vec_arg);
```

Finally, re-run `m2c` with our custom stack as part of the `--context`. The `--context` option can be specified multiple times to combine files.

<details>
    <summary><code>python3 m2c.py tests/end_to_end/custom_stack/irix-o2.s -f test --context test_context.c</code></summary>

```c
? func_00400090(s8 *);                              /* static */

s32 test(struct Vec *vec_arg) {
    s8 scale_x;
    s16 scale_y;
    s32 scale_z;
    struct Vec *vec_ptr;
    struct Vec vec;
    s32 temp_t4;

    func_00400090(&scale_x);
    func_00400090((s8 *) &scale_y);
    func_00400090((s8 *) &scale_z);
    func_00400090((s8 *) &vec_ptr);
    func_00400090((s8 *) &vec);
    scale_x = vec_arg->x + vec_arg->y;
    scale_y = vec_arg->x + vec_arg->z;
    temp_t4 = vec_arg->y + vec_arg->z;
    scale_z = temp_t4;
    vec = vec_arg->x * scale_x;
    vec.y = vec_arg->y * scale_y;
    vec.z = vec_arg->z * temp_t4;
    if (scale_x != 0) {
        vec_ptr = vec_arg;
    } else {
        vec_ptr = &vec;
    }
    return scale_x + scale_y + scale_z + vec_ptr->x + vec.y;
}
```
</details>

### Formatting

The following options control the formatting details of the output, such as braces style or numeric format. See `./m2c.py --help` for more details. 

(The option name on the website, if available, is in parentheses.)

- `--valid-syntax`
- `--allman` ("Allman braces")
- `--knr` ("K&R braces")
- `--pointer-style` ("`*` to the left")
- `--unk-underscore`
- `--hex-case`
- `--comment-style {multiline,oneline,none}` ("Comment style")
- `--comment-column N` ("Comment style")
- `--no-casts`
- `--zfill-constants` ("0-fill constants")
- `--deterministic-vars`
- `--descending-regs`
- `--backwards-bss`

Note: `--valid-syntax` is used to produce output that is less human-readable, but is likely to directly compile without edits. This can be used to go directly from assembly to the permuter without human intervention.

### Debugging poor results (Advanced)

There are several options to `m2c` which can be used to troubleshoot poor results. Many of these options produce more "primitive" output or debugging information.

- `--no-andor` ("Disable &&/||"): Disable complex conditional detection, such as `if (a && b)`. Instead, emit each part of the conditional as a separate `if` statement. Ands, ors, nots, etc. are usually represented with `goto`s.
- `--no-switches` ("Disable irregular switch detection"): Disable "irregular" `switch` statements, where the compiler emits a single `switch` as a series of branches and/or jump tables. By default, these are coalesced into a single `switch` and marked with an `/* irregular */` comment.
- `--no-unk-inference` ("Disable unknown struct/type inference"): Disable attempting to infer struct fields/types in unknown struct sections and global symbols. See the [_Struct Field Inference_](#struct-field-inference) section above.
- `--gotos-only` ("Use gotos for everything"): Do not detect loops or complex conditionals. This format is close to a 1-1 translation of the assembly.
    - Note: to use a goto for a single branch, don't use this flag, but add `# GOTO` to the assembly input.
- `--debug` ("Debug info"): include debug information inline with the code, such as basic block boundaries & labels.
- `--void` ("Force void return type"): assume that the decompiled function has return type `void`. Alternatively: provide the function prototype in the context.

#### Visualization

`m2c` can generate an SVG representation of the control flow of a function, which can sometimes be helpful to untangle complex loops or early returns.

Pass `--visualize` on the command line, or use the "Visualize" button on the website. The output will be an SVG file.

Example to produce C & assembly visualizations of `my_fn()`:

```sh
python3 ./m2c.py --visualize=c --context ctx.c -f my_fn my_asm.s > my_fn_c.svg
python3 ./m2c.py --visualize=asm --context ctx.c -f my_fn my_asm.s > my_fn_asm.svg
```

### Preprocessing

There currently is a pseudo-macro in lieu of a full preprocessor that allows for the conditional switching of code in a context file. This allows for both m2c and e.g. a compiler to use the same context file if both need to define e.g. structs or typedefs slightly differently.

```c
#ifdef M2C
...
#else
...
#endif
```

Any other macros besides `#ifdef M2C` currently will fail, and you also need the `#else` between `#ifdef M2C` and `#endif` for the pattern to match.

## Contributing

There is much low-hanging fruit still. Take a look at the issues if you want to help out.

We use `black` to auto-format our code, `mypy` for type checking and `coverage` for unit tests. We recommend using `pre-commit` to ensure only auto-formatted code is committed. To set these up, run:
```bash
pip install pre-commit black mypy coverage
pre-commit install
```

Your commits will then be automatically formatted per commit. You can also manually run `black` on the command-line.

Type annotations are used for all Python code. `mypy` should pass without any errors.

To get pretty graph visualizations, install `graphviz` using `pip` and globally on your system (e.g. `sudo apt install graphviz`), and pass the `--visualize` flag.

## Tests

### Conker fork matching improvements

The local IDO first-pass change keeps an unknown register parameter word-sized
when it is used by a byte or halfword store. A store establishes the width of
the destination, not the original parameter. Known narrow parameter types from
context remain supported; the GCC target retains its existing inference.

The 2026-10-04 pilot used 20 short Conker functions with narrow argument stores
and 10 short controls, without source context, at baseline commit `708d2d2`.
With Conker's pinned IDO 5.3 toolchain and its compilation flags, 29 of 30
starters compiled. Complete reference `.text` and relocation matches increased
from 12 to 16; 13 functions had fewer differing instruction words, and none
regressed. The remaining compile failure was an unresolved pointer expression
in `func_1507EB80`. The sample was selected for this failure family and does not
estimate the match rate across the whole project.

Pilot inputs, compiler output, disassembly, and results are saved locally under
ignored `build/conker-first-pass/`. Generated field macros were used only in
this experiment. These object comparisons do not record Conker matches or
replace its independent full-span `CURRENT (0)` and integration gates.

Run the regression checks with the development dependencies installed:

```bash
python3 run_tests.py -j 4
mypy
black --check m2c/evaluate.py tests/unit/test_mips.py
git diff --check
```

The new regression fixture was generated from its `orig.c` with pinned IDO,
using `tests/add_test.py --target irix-o2`. The unchanged baseline inferred
`s8` and `s16`; this checkout infers `s32` with casts at the stores.

Conker can opt into this checkout for host starter generation:

```bash
CONKER_MIPS_TO_C=/Users/troy/Development/decompilation/m2c-conker/m2c.py ./conker next --ready
```

Run that command from Conker's repository after verifying that its wrapper
honors the override. Some versions of `scripts/conker.sh` unconditionally
replace `CONKER_MIPS_TO_C` in `run_host_mips_to_c`; those need a local adapter
that selects the supplied path, validates it and uses its directory for
`PYTHONPATH`. With no override, keep the default pinned host tool. The compiler
and Docker toolchain remain pinned. Cloud workspaces need their own checkout
of this fork, at the tested branch/commit, rather than the Mac path above.

A second local fix uses `M2C_FIELD` to cast a computed integer address
before dereferencing it in valid-syntax output. It preserves known integer
address types and existing pointer/array accesses; it does not guess an original
pointer parameter type. This fixes the pilot's `func_1507EB80` compile failure.

A third local IDO fix captures reused byte and halfword global loads in a
temporary, preserving the ASM register's snapshot across potentially aliasing
stores. On the corrected source-context pilot, `func_1510D874` improves from
`CURRENT (605)` to `CURRENT (255)`. Across 18 comparable functions the average
falls from 426.11 to 406.67 (4.56%), with one improvement and no regressions.
The corrected benchmark compiles only the target function with canonical
declarations, so shorter candidates cannot include neighboring functions in
their score. These measurements are first-pass scores, not accepted matches.

A fourth local fix converts aligned ASM pointer byte offsets to C element
counts at formatting time, preserving raw IR offsets for field recovery.
For real Conker `func_15016370`, `s32_pointer += 0x32C` becomes
`+= 0xCB`, restoring the compiled advance from `0xCB0` to `0x32C` bytes.
Its full-span first-pass score improves from 165 to 160; the other 42 scorable
pilot cases are unchanged. Seven unsupported starters are excluded and no new
zero-score starter is produced. Word, halfword, byte and negative steps have
focused regressions; existing SH and void-pointer expectations were corrected
against their original source and ASM. The rejected stack-argument snapshot
experiment gave no score improvement and was not adopted.

A fifth fix preserves the distinct symbols and addends in memory `%lo`
relocations when their base is directly defined by a symbolic MIPS `lui`.
Reusing one upper half previously redirected later accesses to the first
global. For real Conker `func_151E81EC`, the starter now clears all five intended
globals instead of only three. Its pinned IDO object score rises from 205 to
400 because compiling the separate canonical globals introduces two extra
address loads; the old lower score described incorrect C. This is a correctness
repair, not a score improvement or new zero-score starter. The other 42
comparable pilot cases are unchanged; seven unsupported starters are excluded.
The earlier pilot averages include this incorrect starter. Matching hi/lo
pairs and bases changed by arithmetic or address completion retain their prior
handling. Six unit tests and a standalone ASM fixture cover destination
identity, loads, relocation addends and those recovery limits.

A sixth IDO fix keeps a previously loaded word-sized field in a temporary
when a byte or halfword store to the same base precedes its later use. It
preserves the ASM read order and keeps inferred and context-provided types.
The rule is restricted to MIPS/IDO; unrelated bases and word stores retain
existing handling. Real Conker `func_150CBF5C` improves from `CURRENT (130)` to
`CURRENT (120)`, with the other 42 scorable cases unchanged and no regressions.
The pilot covers 50 cases across 48 distinct functions (20 with context and
30 without, with two overlaps); seven unsupported cases are excluded. The
combined mean is 267.44 to 267.21, a small 0.087% decrease. There are no new
zero-score starters; the previous five-global correctness fix remains intact.
Six focused tests and a standalone fixture cover load order, scalar/pointer
context types, compiler targeting and the rule's limits.

A seventh IDO fix declares captured narrow global-load temporaries as `s32`.
Byte and halfword load values fit this word-sized local and retain their C
integer promotions. Only single-assignment snapshot locals are widened; load
casts, global declarations, inferred return types and planned phi variables
keep their types. Real Conker `func_1510D874` improves from `CURRENT (255)` to
`CURRENT (20)`, removing an extra register copy. In the same 50-case pilot,
one of 43 scorable cases improves, 42 are unchanged and none regress. The
combined mean falls from 267.21 to 261.74 (2.05%); seven unsupported cases are
excluded and no new zero-score starter is produced. The remaining score is
from register choices, so this is a better first pass rather than an exact
match. The selected pilot establishes a local benefit, not a corpus-wide rate.
Signed byte/halfword loads and narrow explicit/inferred returns have focused
regressions; the full suite passes 465 tests.

An eighth IDO fix extends those word-sized snapshot declarations to captured
byte/halfword field loads through pointers. Existing capture timing and load
casts are retained; single-use reads and planned phi types stay unchanged.
Real Conker `func_15033EC4` improves from `CURRENT (240)` to `CURRENT (55)`
with and without source context. The paired 50-case pilot has two improved
cases for this one function, 41 unchanged scores, no regressions and seven
unsupported exclusions. The case mean falls from 261.74 to 253.14 (3.29%);
counting each of the 41 scorable functions once, it falls from 247.68 to
243.17 (1.82%). No new zero-score starter is produced, and the remaining target
differences are register choices. Six focused tests cover signedness, narrow
return types, GCC handling, word loads, single-use reads and branch joins;
all 471 tests pass. These are first-pass pilot results rather than a measured
corpus-wide improvement or accepted game-source matches.

A ninth local IDO fix prefers an unsigned byte/halfword field when a stored
positive constant has its high bit set and the destination type is compatible.
This avoids IDO shortening a byte register value of 255 to -1. Known signed
fields, signed loads, incoming parameter widths and other compiler targets
retain their handling. Real Conker `func_1502EA60` and `func_1502EA7C` each
improve from `CURRENT (5)` to `CURRENT (0)` without source context. In the same
50-case pilot, two of 43 scorable cases improve and the other 41 are unchanged,
with no regressions and seven unsupported exclusions. The case mean falls
from 253.14 to 252.91 (0.092%); zero-score cases increase from 15 to 17.
These are two new full-span zero-score starters, not recorded or integrated
game-source matches. Eight focused tests and a standalone fixture cover
constant ranges, signed contexts/loads, global fields, compiler targeting and
parameter widths; all 480 tests pass. This improvement is local and unpushed.

A further IDO recovery captures scaled integer addresses as explicitly cast
pointer locals while retaining integer operand and parameter types. Known
pointer arithmetic and constant field offsets retain their handling. Real
Conker `func_15087FC4` improves from `CURRENT (10)` to `CURRENT (0)`. An expanded
98-case pilot across 96 distinct functions includes the original 50 cases and
48 deterministic controls covering floating-point operations, branches/loops,
direct calls and bit operations. Of 74 scorable cases, one improves and 73
are unchanged, with no regressions; 24 unsupported or compile-failing cases
remain excluded. All 17 existing zeros survive and one new full-span zero
starter is produced. Six focused tests cover pointer conversions, integer
parameter types, load returns, input reuse, compiler targeting and rule limits;
all 486 tests pass. Updated array/address fixtures preserve their original
byte addresses and add explicit C pointer conversions. These pilot zeros are
not recorded or integrated game-source matches.

IDO overlapping field accesses retain their individual instruction widths,
including partial stores to known pointer/structure fields. The 98-case Conker
pilot improves `func_150A7C10` from `CURRENT (6845)` to `CURRENT (6655)`;
73 other scorable cases and all 18 existing zeros are unchanged. Seven focused
regressions cover mixed widths, signed loads, explicit context, union members
and plain-pointer inference; all 493 tests pass. No game source is modified.

Valid-syntax output uses byte-pointer casts for void-pointer arithmetic,
including increments and pointer differences, without changing context types.
In the same 98-case Conker pilot, eight previously compile-failing starters
become scorable; all 74 prior scores and 18 zeros remain unchanged. Seven
focused arithmetic/type-preservation tests and all 500 suite tests pass.

Function definitions retain explicitly volatile scalar parameters from context,
including typedef qualifiers, while preserving their ABI widths. This restores
compilation of Conker `func_151D5D60` (`CURRENT (615)`); all 82 previously
scorable pilot cases and 18 zeros are unchanged. Seven focused tests and all
507 tests pass. Division fixtures now retain the qualifiers in their `orig.c`.

Valid-syntax equality between differently typed object pointers compares their
addresses through explicit void-pointer casts, preserving the original target
types. Conker `func_1509CB68` and `func_1503B840` now compile and score 1910
and 1770 respectively; all 83 prior scores and 18 zeros are unchanged. Seven
focused comparison tests and all 514 suite tests pass.

Unknown external globals used only by address can be represented in valid C
as byte storage of unspecified extent, without assuming an object layout.
Typed field accesses retain the original instruction widths and offsets;
context types, defined data and globals read by value retain their handling.
Five formerly unsupported Conker starters become scorable. Four have full-span
`CURRENT (0)`: `func_15125690`, `func_1503DF0C`, `func_15052F58` and
`func_150221E8`; `func_1517E05C` scores 100. All 85 prior scores remain
unchanged. Six focused tests and all 520 tests pass. These are standalone
first-pass results, not integrated game-source matches.

IDO recovery recognizes homogeneous copied stack arrays when a masked index
proves that an indirect byte access stays within their inferred storage. The
valid C expression uses the local object's address instead of an undefined
physical stack pointer; out-of-bounds and unmasked cases retain their handling.
`func_151D9918` and `func_151D9A20` now compile and score 360 each; all 90
prior scorable cases and 22 zeros are unchanged. Six focused bound/layout
tests and all 526 tests pass.

IDO captures an earlier signed halfword field load before a later unsigned
halfword load from the same object, preserving the ASM evaluation order and
word-sized register snapshot without changing field/return widths. Conker
`func_1515F008` improves from `CURRENT (60)` to `CURRENT (45)`; the other
91 scorable cases and all 22 zeros are unchanged. Six focused regressions
and all 532 suite tests pass.

There is a small test suite, which works as follows:
 - As you develop your commit, occasionally run `./run_tests.py` to see if any tests have changed output.
   These tests run the decompiler on a small corpus of assembly.
 - Before pushing your commit, run `./run_tests.py --overwrite` to write changed tests to disk, and commit resultant changes.

`./run_tests.py` additionally runs a handful of unit tests in `tests/unit/`.

### Running Decompilation Project Tests

It's possible to use the entire corpus of assembly files from decompilation projects as regression tests.

For now, the output of these tests are not tracked in version control.
You need to run `./run_tests.py --overwrite ...` **before** making any code changes to create the baseline output.

As an example, if you have the `oot` project cloned locally in the parent directory containing `m2c`, the following will decompile all of its assembly files.

```bash
./run_tests.py --project ../oot --project-with-context ../oot
```

This has been tested with:
- [zeldaret/oot](https://github.com/zeldaret/oot)
- [zeldaret/mm](https://github.com/zeldaret/mm)
    - See notes below, the repository needs to be partially built
- [pmret/papermario](https://github.com/pmret/papermario)
    - Need to use the `ver/us` or `ver/jp` subfolder, e.g. `--project ../papermario/ver/us`

#### Creating Context Files

The following bash can be used in each decompilation project to create a "universal" context file that can be used for decompiling any assembly file in the project.
This creates `ctx.c` in the project directory.

```bash
cd mm       # Or oot, papermario, etc.
find include/ src/ -type f -name "*.h" | sed -e 's/.*/#include "\0"/' > ctx_includes.c
tools/m2ctx.py ctx_includes.c
```

#### Notes for Majora's Mask

The build system in the MM decompilation project is currently being re-written.
It uses "transient" assembly that is not checked in, and in the normal build process it re-groups `.rodata` sections by function.

To use the MM project, run the following to *just* build the transient assembly files (and avoid running `split_asm.py`).

```bash
cd mm
make distclean
make setup
make asm/disasm.dep
```

The repository should be setup correctly if there are `asm/code`, `asm/boot`, and `asm/overlays` folders with `.asm` files, but there *should not* be an `asm/non_matchings` folder.

### Coverage

Code branch coverage can be computed by running `./run_tests.py --coverage`.
By default, this will generate an HTML coverage report `./htmlcov/index.html`.

### Adding an End-to-End Test

You are encouraged to add new end-to-end tests using the `./tests/add_test.py` script.

For MIPS tests, you'll need the IDO `cc` compiler and the `spimdisasm` pip package.

A good reference test to base your new test on is [`array-access`](tests/end_to_end/array-access).

Create a new directory in `tests/end_to_end`, and write the `orig.c` test case.
If you want the test to pass in C context, also add `irix-o2-flags.txt` & `irix-g-flags.txt` files.

After writing these files, run `add_test.py` with the path to the new `orig.c` file, as shown below.
This example assumes that the IDO compiler is available from the OOT decompilation project.
You should change this exported path to match your system.

```bash
export IDO_CC=$HOME/oot/tools/ido_recomp/linux/7.1/cc
./tests/add_test.py $PWD/tests/end_to_end/my-new-test/orig.c
```

This should create `irix-o2.s` and `irix-g.s` files in your test directory.

Now, run `./run_tests.py --overwrite` to invoke the decompiler and write the output to `irix-o2-out.c` and `irix-g-out.c`. 
Finally, `git add` your test to track it.

```bash
./run_tests.py --overwrite
git add tests/end_to_end/my-new-test
```

For PowerPC, the `MWCC_CC` environment variable should be set to point to a PPC cc binary (mwcceppc.exe),
and on non-Windows, `WINE` set to point to wine or equivalent ([wibo](https://github.com/decompals/wibo) also works).

### Installation as Python Package

You can include `m2c` as a dependency in your project by adding the following to your `requirements.txt`
(or `project.dependencies` section of `pyproject.toml`):

```
m2c @ git+https://github.com/matt-kempster/m2c.git

# To specify a specific Git ref, such as a commit, tag, or branch:
m2c @ git+https://github.com/matt-kempster/m2c.git@[YOUR REF HERE]
```

When installed as a Python package, a standalone command entrypoint is provided
which can run the CLI.

```bash
m2c [options] [-t <target>] [--context <context file>] [-f <function name>] <asmfile>...
```
