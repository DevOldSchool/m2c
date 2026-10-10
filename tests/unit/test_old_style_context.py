from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.arch_mips import MipsArch
from m2c.c_types import build_typemap, parse_function, type_to_string
from m2c.error import DecompFailure
from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestOldStyleContext(unittest.TestCase):
    def signature(self, source: str) -> tuple[list[str], list[str]]:
        with TemporaryDirectory() as directory:
            context = Path(directory) / "context.c"
            context.write_text(source)
            typemap = build_typemap([context], MipsArch(), False)
            function = typemap.functions["test"]
            global_function = parse_function(typemap.var_types["test"])
            assert function.params is not None and global_function is not None
            assert global_function.params is not None
            return (
                [type_to_string(p.type, p.name or "") for p in function.params],
                [type_to_string(p.type) for p in global_function.params],
            )

    def decompile(self, assembly: str, context: str) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / "input.s"
            source.write_text(".set noreorder\nglabel test\n" + assembly + "\n")
            ctx = path / "context.c"
            ctx.write_text(context)
            return decompile_and_capture_output(
                parse_flags(
                    [
                        "--target",
                        "mips-ido-c",
                        "--valid-syntax",
                        "--no-cache",
                        "--context",
                        str(ctx),
                        str(source),
                    ]
                )
            )

    def test_identifier_order_and_default_integer_promotions(self) -> None:
        params, globals_ = self.signature(
            "typedef unsigned short U16; int test(a,b,c,d) "
            "signed char c; U16 b; unsigned int d; int a; { return 0; }"
        )
        self.assertEqual(params, ["int a", "int b", "int c", "unsigned int d"])
        self.assertEqual(globals_, ["int", "int", "int", "unsigned int"])

    def test_pointer_typedef_is_not_promoted(self) -> None:
        params, _ = self.signature(
            "typedef float Real; int test(a,b) Real *a; const char *b; {return 0;}"
        )
        self.assertEqual(params, ["Real *a", "const char *b"])

    def test_implicit_int_and_register_parameter(self) -> None:
        params, _ = self.signature("int test(a,b) register short b; {return a+b;}")
        self.assertEqual(params, ["int a", "int b"])

    def test_array_and_function_parameters_decay(self) -> None:
        params, _ = self.signature(
            "typedef int Row[4]; int test(a,b,c) int a[3]; int b(int); Row c; {return 0;}"
        )
        self.assertEqual(params, ["int *a", "int (*b)(int)", "int *c"])

    def test_qualified_parameter_typedef(self) -> None:
        params, _ = self.signature(
            "typedef volatile int Word; int test(x) Word x; {return x;}"
        )
        self.assertEqual(params, ["Word x"])

    def test_ansi_narrow_parameters_are_unchanged(self) -> None:
        params, _ = self.signature("int test(unsigned char a, float b) {return a;}")
        self.assertEqual(params, ["unsigned char a", "float b"])

    def test_malformed_parameter_lists_fail_closed(self) -> None:
        for source in (
            "int test(a,a) int a; {return a;}",
            "int test(a) int b; {return 0;}",
            "int test(a) int a; short a; {return a;}",
        ):
            with self.subTest(source=source), self.assertRaises(DecompFailure):
                self.signature(source)

    def test_unrelated_old_style_definition_no_longer_blocks_context(self) -> None:
        output = self.decompile(
            "jr $ra\naddiu $v0, $a0, 1",
            "int legacy(a) unsigned char a; {return a;} int test(int value);",
        )
        self.assertIn("s32 test(s32 value)", output)
        self.assertIn("return value + 1;", output)

    def test_callee_conversion_is_preserved_for_promoted_parameter(self) -> None:
        output = self.decompile(
            "jr $ra\nandi $v0, $a0, 0xFF",
            "int test(value) unsigned char value; {return value;}",
        )
        self.assertIn("s32 test(s32 value)", output)
        self.assertIn("return value & 0xFF;", output)

    def test_unsupported_abi_shapes_fail_closed(self) -> None:
        for declaration in (
            "float value",
            "double value",
            "long long value",
            "void value",
            "volatile unsigned char value",
            "struct S value",
        ):
            with self.subTest(declaration=declaration), self.assertRaises(
                DecompFailure
            ):
                self.signature(
                    "struct S {int x;}; int test(value) "
                    + declaration
                    + "; {return 0;}"
                )

    def test_call_preserves_promoted_integer_argument(self) -> None:
        output = self.decompile(
            "addiu $sp, $sp, -0x18\nsw $ra, 0x14($sp)\n"
            "li $a0, 0x1234\n"
            "jal callee\nnop\nlw $ra, 0x14($sp)\n"
            "addiu $sp, $sp, 0x18\njr $ra\nnop",
            "int callee(value) unsigned char value; {return value;} int test(void);",
        )
        self.assertIn("callee(0x1234)", output)
        self.assertNotIn("(u8)", output)
