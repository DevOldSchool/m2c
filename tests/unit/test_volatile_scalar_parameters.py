from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestVolatileScalarParameters(unittest.TestCase):
    def decompile(self, body: str, context: str) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
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
                        str(asm),
                    ]
                )
            )

    def test_scalar_qualifier_is_preserved(self) -> None:
        output = self.decompile("addiu $v0, $a0, 1", "int test(volatile int value);")
        self.assertIn("s32 test(volatile s32 value)", output)

    def test_qualified_typedef_is_preserved(self) -> None:
        output = self.decompile(
            "addiu $v0, $a0, 1", "typedef int Word; int test(volatile Word value);"
        )
        self.assertIn("s32 test(volatile s32 value)", output)

    def test_volatile_typedef_is_preserved(self) -> None:
        output = self.decompile(
            "addiu $v0, $a0, 1", "typedef volatile int Word; int test(Word value);"
        )
        self.assertIn("s32 test(volatile s32 value)", output)

    def test_narrow_width_stays_context_provided(self) -> None:
        output = self.decompile(
            "sll $t0, $a0, 16\nsra $v0, $t0, 16", "int test(volatile short value);"
        )
        self.assertIn("s32 test(volatile s16 value)", output)

    def test_float_parameter_keeps_scalar_qualifier(self) -> None:
        output = self.decompile("mov.s $f0, $f12", "float test(volatile float value);")
        self.assertIn("f32 test(volatile f32 value)", output)

    def test_nonvolatile_parameter_is_not_qualified(self) -> None:
        output = self.decompile("addiu $v0, $a0, 1", "int test(int value);")
        self.assertIn("s32 test(s32 value)", output)
        self.assertNotIn("volatile", output)

    def test_pointee_qualifier_is_not_moved_to_parameter(self) -> None:
        output = self.decompile("lw $v0, 0($a0)", "int test(volatile int *value);")
        self.assertNotIn("volatile s32 *value", output)
        self.assertNotIn("s32 *volatile value", output)
