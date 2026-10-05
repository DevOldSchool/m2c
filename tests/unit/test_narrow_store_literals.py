from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestNarrowStoreLiterals(unittest.TestCase):
    def decompile(
        self, body: str, *, context: str = "", target: str = "mips-ido-c"
    ) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            assembly = path / "test.s"
            assembly.write_text(f"glabel test\n{body}\njr $ra\nnop\n")
            flags = ["--target", target, "--valid-syntax", "--no-cache"]
            if context:
                context_file = path / "context.c"
                context_file.write_text(context)
                flags.extend(["--context", str(context_file)])
            return decompile_and_capture_output(parse_flags([*flags, str(assembly)]))

    def test_positive_high_bit_constants_infer_unsigned_fields(self) -> None:
        for store, scalar, values in (
            ("sb", "u8", (0x80, 0xFF)),
            ("sh", "u16", (0x8000, 0xFFFF)),
        ):
            for value in values:
                with self.subTest(store=store, value=value):
                    output = self.decompile(f"li $t6, {value}\n{store} $t6, 4($a0)")
                    self.assertIn(f"M2C_FIELD(arg0, {scalar} *, 4)", output)
                    self.assertIn(f"= 0x{value:X}U;", output)

    def test_low_negative_and_truncated_constants_keep_existing_types(self) -> None:
        for store, scalar, values in (
            ("sb", "s8", (0x7F, -1, 0x100)),
            ("sh", "s16", (0x7FFF, -1, 0x10000)),
        ):
            for value in values:
                with self.subTest(store=store, value=value):
                    output = self.decompile(f"li $t6, {value}\n{store} $t6, 4($a0)")
                    self.assertIn(f"M2C_FIELD(arg0, {scalar} *, 4)", output)

    def test_signed_context_fields_are_preserved(self) -> None:
        for store, scalar, value in (
            ("sb", "signed char", 0xFF),
            ("sh", "signed short", 0xFFFF),
        ):
            with self.subTest(store=store):
                context = (
                    f"struct Object {{ int padding; {scalar} value; }};"
                    "void test(struct Object *object);"
                )
                body = f"li $t6, {value}\n{store} $t6, 4($a0)"
                output = self.decompile(body, context=context)
                self.assertEqual(
                    self.decompile(body, context=context, target="mips-gcc-c"), output
                )
                self.assertIn("object->value = -1;", output)

    def test_signed_load_after_store_keeps_sign_extension(self) -> None:
        for store, load, value, cast in (
            ("sb", "lb", 0xFF, "s8"),
            ("sh", "lh", 0xFFFF, "s16"),
        ):
            with self.subTest(store=store):
                output = self.decompile(
                    f"li $t6, {value}\n{store} $t6, 4($a0)\n{load} $v0, 4($a0)"
                )
                self.assertIn(f"return ({cast})", output)

    def test_gcc_retains_existing_signed_field_inference(self) -> None:
        for store, scalar, value in (("sb", "s8", 0xFF), ("sh", "s16", 0xFFFF)):
            with self.subTest(store=store):
                output = self.decompile(
                    f"li $t6, {value}\n{store} $t6, 4($a0)", target="mips-gcc-c"
                )
                self.assertIn(f"M2C_FIELD(arg0, {scalar} *, 4)", output)

    def test_word_stores_and_incoming_parameters_are_unchanged(self) -> None:
        word = self.decompile("li $t6, 255\nsw $t6, 4($a0)")
        parameter = self.decompile("li $t6, 255\nsb $t6, 4($a0)\nsb $a1, 5($a0)")
        self.assertIn("M2C_FIELD(arg0, s32 *, 4)", word)
        self.assertIn("void test(void *arg0, s32 arg1)", parameter)
        self.assertIn("M2C_FIELD(arg0, s8 *, 5) = (s8) arg1;", parameter)

    def test_global_store_keeps_positive_value_and_signed_read(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(flag)\nli $t6, 255\nsb $t6, %lo(flag)($t0)\n"
            "lb $v0, %lo(flag)($t0)"
        )
        self.assertIn("extern u8 flag;", output)
        self.assertIn("flag = 0xFF;", output)
        self.assertIn("return (s8) flag;", output)

    def test_declared_signed_global_is_not_retyped(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(flag)\nli $t6, 255\nsb $t6, %lo(flag)($t0)\n"
            "lb $v0, %lo(flag)($t0)",
            context="extern signed char flag; signed char test(void);",
        )
        self.assertIn("s8 test(void)", output)
        self.assertIn("flag = -1;", output)
        self.assertIn("return flag;", output)
