import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestMixedAccessWidths(unittest.TestCase):
    def decompile(
        self, body: str, context: str = "", target: str = "mips-ido-c"
    ) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
            flags = ["--target", target, "--valid-syntax", "--no-cache"]
            if context:
                ctx = path / "context.c"
                ctx.write_text(context)
                flags.extend(["--context", str(ctx)])
            return decompile_and_capture_output(parse_flags([*flags, str(asm)]))

    def test_doubleword_then_halfword_and_byte_keep_their_widths(self) -> None:
        output = self.decompile("sd $zero, 0($a0)\nsh $a1, 0($a0)\nsb $a1, 4($a0)")
        self.assertIn("M2C_FIELD(arg0, s64 *, 0) = 0;", output)
        self.assertIn("M2C_FIELD(arg0, s16 *, 0) = (s16) arg1;", output)
        self.assertIn("M2C_FIELD(arg0, s8 *, 4) = (s8) arg1;", output)

    def test_overlapping_signed_byte_load_keeps_sign_extension(self) -> None:
        output = self.decompile("sh $a1, 0($a0)\nlb $v0, 0($a0)")
        self.assertIn("M2C_FIELD(arg0, s16 *, 0)", output)
        self.assertIn("return M2C_FIELD(arg0, s8 *, 0);", output)

    def test_context_pointer_does_not_widen_halfword_store(self) -> None:
        output = self.decompile(
            "sd $zero, 0($a0)\nsh $a1, 0($a0)",
            "void test(long long *p, int value);",
        )
        self.assertIn("void test(s64 *p, s32 value)", output)
        self.assertIn("*p = 0;", output)
        self.assertIn("M2C_FIELD(p, s16 *, 0) = (s16) value;", output)

    def test_context_struct_field_uses_macro_only_for_partial_store(self) -> None:
        output = self.decompile(
            "sd $zero, 0($a0)\nsh $a1, 0($a0)",
            "struct S { long long whole; int extra; }; void test(struct S *p, int value);",
        )
        self.assertIn("p->whole = 0;", output)
        self.assertIn("M2C_FIELD(p, s16 *, 0) = (s16) value;", output)

    def test_union_selects_members_by_width(self) -> None:
        output = self.decompile(
            "sd $zero, 0($a0)\nsh $a1, 0($a0)",
            "union U { long long whole; short half; }; void test(union U *p, int value);",
        )
        self.assertIn("p->whole = 0;", output)
        self.assertIn("p->half = (s16) value;", output)
        self.assertNotIn("M2C_FIELD", output)

    def test_single_width_still_infers_a_plain_pointer(self) -> None:
        output = self.decompile("sw $a1, 0($a0)\nlw $v0, 0($a0)")
        self.assertIn("s32 test(s32 *arg0, s32 arg1)", output)
        self.assertIn("*arg0 = arg1;", output)
        self.assertIn("return *arg0;", output)

    def test_gcc_single_width_still_uses_plain_pointer(self) -> None:
        output = self.decompile("sw $a1, 0($a0)\nlw $v0, 0($a0)", target="mips-gcc-c")
        self.assertIn("s32 test(s32 *arg0, s32 arg1)", output)
        self.assertIn("*arg0 = arg1;", output)
