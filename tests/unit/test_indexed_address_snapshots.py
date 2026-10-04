from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestIndexedAddressSnapshots(unittest.TestCase):
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

    def test_integer_sum_has_an_explicit_pointer_conversion(self) -> None:
        output = self.decompile(
            "sll $t7, $a1, 2\naddu $t6, $a0, $t7\nsb $a2, 3($t6)",
            "void test(int address, int offset, int value);",
        )
        self.assertIn("void test(s32 address, s32 offset, s32 value)", output)
        self.assertIn("temp_t6 = (void *) (address + (offset * 4));", output)
        self.assertIn("M2C_FIELD(temp_t6, s8 *, 3)", output)

    def test_known_byte_pointer_keeps_element_access(self) -> None:
        output = self.decompile(
            "sll $t7, $a1, 2\naddu $t6, $a0, $t7\nsb $a2, 0($t6)",
            "void test(unsigned char *address, int offset, int value);",
        )
        self.assertNotIn("temp_t6 =", output)
        self.assertIn("*(address + (offset * 4))", output)

    def test_constant_field_offset_does_not_need_a_snapshot(self) -> None:
        output = self.decompile(
            "addiu $t6, $a0, 4\nsb $a1, 0($t6)", "void test(int address, int value);"
        )
        self.assertNotIn("temp_t6", output)
        self.assertIn("M2C_FIELD(address, s8 *, 4)", output)

    def test_single_load_preserves_word_return_type(self) -> None:
        output = self.decompile(
            "sll $t7, $a1, 2\naddu $t6, $a0, $t7\nlw $v0, 0($t6)",
            "int test(int address, int offset);",
        )
        self.assertIn("s32 test(s32 address, s32 offset)", output)
        self.assertIn("temp_t6 = (s32 *) (address + (offset * 4));", output)
        self.assertIn("return *temp_t6;", output)

    def test_gcc_keeps_existing_address_macro(self) -> None:
        output = self.decompile(
            "sll $t7, $a1, 2\naddu $t6, $a0, $t7\nsb $a2, 3($t6)",
            "void test(int address, int offset, int value);",
            target="mips-gcc-c",
        )
        self.assertNotIn("temp_t6 =", output)
        self.assertIn("M2C_FIELD((address + (offset * 4))", output)

    def test_overwritten_input_keeps_its_original_value(self) -> None:
        output = self.decompile(
            "sll $t7, $a1, 2\naddu $t6, $a0, $t7\nmove $a1, $zero\nsb $a2, 3($t6)\nmove $v0, $a1",
            "int test(int address, int offset, int value);",
        )
        self.assertIn("temp_t6 = (void *) (address + (offset * 4));", output)
        self.assertIn("return 0;", output)
