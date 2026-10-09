from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestBoundedSignedShifts(unittest.TestCase):
    def decompile(self, body: str, *, context: str = "", valid: bool = True) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            assembly = path / "test.s"
            assembly.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
            flags = ["--target", "mips-ido-c", "--no-cache"]
            if valid:
                flags.append("--valid-syntax")
            if context:
                ctx = path / "context.c"
                ctx.write_text(context)
                flags += ["--context", str(ctx)]
            return decompile_and_capture_output(parse_flags([*flags, str(assembly)]))

    def test_signed_halfword_scale_uses_defined_multiplication(self) -> None:
        output = self.decompile("lh $v0, 0($a0)\nsll $v0, $v0, 16")
        self.assertIn("*arg0 * 0x10000", output)
        self.assertNotIn("<<", output)

    def test_signed_byte_largest_safe_scale(self) -> None:
        output = self.decompile("lb $v0, 0($a0)\nsll $v0, $v0, 24")
        self.assertIn("*arg0 * 0x01000000", output)
        self.assertNotIn("<<", output)

    def test_signed_context_parameter_and_field(self) -> None:
        output = self.decompile("sll $v0, $a0, 16", context="int test(short value);")
        self.assertIn("value * 0x10000", output)
        output = self.decompile(
            "lh $v0, 4($a0)\nsll $v0, $v0, 16",
            context="struct S { int other; short scale; }; int test(struct S *p);",
        )
        self.assertIn("p->scale * 0x10000", output)

    def test_unsigned_full_width_variable_and_overflowing_shifts_unchanged(
        self,
    ) -> None:
        for body in (
            "lhu $v0, 0($a0)\nsll $v0, $v0, 16",
            "lw $v0, 0($a0)\nsll $v0, $v0, 16",
            "lh $v0, 0($a0)\nsllv $v0, $v0, $a1",
            "lh $v0, 0($a0)\nsll $v0, $v0, 17",
            "lb $v0, 0($a0)\nsll $v0, $v0, 25",
        ):
            with self.subTest(body=body):
                self.assertIn("<<", self.decompile(body))

    def test_negated_load_keeps_existing_multiplication(self) -> None:
        output = self.decompile("lh $v0, 0($a0)\nneg $v0, $v0\nsll $v0, $v0, 16")
        self.assertIn("*arg0 * -0x10000", output)

    def test_sign_extension_idiom_is_still_folded(self) -> None:
        output = self.decompile("sll $v0, $a0, 16\nsra $v0, $v0, 16")
        self.assertIn("s16 test(s16 arg0)", output)
        self.assertIn("return arg0;", output)
        self.assertNotIn("0x10000", output)

    def test_diagnostic_output_is_unchanged(self) -> None:
        output = self.decompile("lh $v0, 0($a0)\nsll $v0, $v0, 16", valid=False)
        self.assertIn("<< 0x10", output)
