from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestByteAddressAccess(unittest.TestCase):
    def decompile(self, body: str, context: str = "", valid: bool = True) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
            ctx = path / "context.c"
            ctx.write_text(context)
            args = ["--target", "mips-ido-c", "--no-cache", "--context", str(ctx)]
            if valid:
                args.append("--valid-syntax")
            return decompile_and_capture_output(parse_flags(args + [str(asm)]))

    def test_indexed_load_preserves_width_and_signedness(self) -> None:
        for instruction, type_name in (
            ("lb", "s8"),
            ("lh", "s16"),
            ("lhu", "u16"),
            ("lw", "s32"),
        ):
            with self.subTest(instruction=instruction):
                output = self.decompile(
                    f"addu $t0, $a0, $a1\n{instruction} $v0, 0($t0)",
                    "int test(void *base, int offset);",
                )
                self.assertIn(f"{type_name} *, 0)", output)
                self.assertNotIn("return *((u8 *)", output)

    def test_indexed_float_load_preserves_float_type(self) -> None:
        output = self.decompile(
            "addu $t0, $a0, $a1\nlwc1 $f0, 0($t0)",
            "float test(void *base, int offset);",
        )
        self.assertIn("f32 *, 0)", output)

    def test_indexed_stores_preserve_width(self) -> None:
        for instruction, type_name in (("sh", "s16"), ("sw", "s32")):
            with self.subTest(instruction=instruction):
                output = self.decompile(
                    f"addu $t0, $a0, $a1\n{instruction} $a2, 0($t0)",
                    "void test(void *base, int offset, int value);",
                )
                self.assertIn(f"{type_name} *, 0) =", output)

    def test_nested_unknown_layout_load_without_context(self) -> None:
        output = self.decompile(
            "lw $t0, 4($a0)\naddiu $t1, $a0, 0x100\n"
            "sll $t0, $t0, 2\naddu $t1, $t1, $t0\nlw $v0, 0($t1)"
        )
        self.assertIn("s32 test(void *arg0)", output)
        self.assertIn("s32 *, 0)", output)
        self.assertIn("0x100", output)

    def test_known_element_pointer_keeps_array_access(self) -> None:
        output = self.decompile(
            "sll $a1, $a1, 2\naddu $t0, $a0, $a1\nlw $v0, 0($t0)",
            "int test(int *base, int index);",
        )
        self.assertIn("return base[index];", output)
        self.assertNotIn("M2C_FIELD", output)

    def test_known_byte_pointer_keeps_byte_access(self) -> None:
        output = self.decompile(
            "addu $t0, $a0, $a1\nlbu $v0, 0($t0)",
            "int test(unsigned char *base, int index);",
        )
        self.assertNotIn("M2C_FIELD", output)
        self.assertIn("return (s32) base[index];", output)

    def test_diagnostic_mode_keeps_existing_access(self) -> None:
        output = self.decompile(
            "addu $t0, $a0, $a1\nlw $v0, 0($t0)",
            "int test(void *base, int offset);",
            valid=False,
        )
        self.assertNotIn("M2C_FIELD", output)
        self.assertNotIn("(u8 *)", output)
