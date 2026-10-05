from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestHalfwordLoadOrder(unittest.TestCase):
    def decompile(
        self,
        body: str,
        context: str = "int test(void *data);",
        target: str = "mips-ido-c",
    ) -> str:
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
                        target,
                        "--valid-syntax",
                        "--no-cache",
                        "--context",
                        str(ctx),
                        str(asm),
                    ]
                )
            )

    body = "lh $v0, 0($a0)\nlhu $t1, 32($a0)\nsll $v0, $v0, 16\nor $v0, $t1, $v0"

    def test_signed_halfword_stays_before_unsigned_load(self) -> None:
        output = self.decompile(self.body)
        self.assertIn("s32 temp_v0;", output)
        self.assertIn("temp_v0 = M2C_FIELD(data, s16 *, 0);", output)
        self.assertIn("M2C_FIELD(data, u16 *, 0x20) | (temp_v0 << 0x10)", output)

    def test_unsigned_pair_does_not_trigger_signed_rule(self) -> None:
        output = self.decompile(self.body.replace("lh $v0", "lhu $v0"))
        self.assertNotIn("temp_v0 =", output)

    def test_different_objects_do_not_trigger_same_object_rule(self) -> None:
        output = self.decompile(
            self.body.replace("32($a0)", "32($a1)"),
            "int test(void *data, void *other);",
        )
        self.assertNotIn("temp_v0 =", output)

    def test_gcc_preserves_existing_expression(self) -> None:
        output = self.decompile(self.body, target="mips-gcc-c")
        self.assertNotIn("temp_v0 =", output)

    def test_context_field_names_and_widths_survive(self) -> None:
        output = self.decompile(
            self.body.replace("32($a0)", "2($a0)"),
            "struct S { short high; unsigned short low; }; int test(struct S *data);",
        )
        self.assertIn("temp_v0 = data->high;", output)
        self.assertIn("data->low | (temp_v0 << 0x10)", output)

    def test_return_abi_keeps_context_narrow_width(self) -> None:
        output = self.decompile(
            "lh $v0, 0($a0)\nlhu $t1, 32($a0)\nsh $t1, 2($a0)",
            "short test(void *data);",
        )
        self.assertIn("s16 test(void *data)", output)
        self.assertIn("return temp_v0;", output)
