from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestPointerFieldSnapshots(unittest.TestCase):
    def decompile(self, body: str, context: str, target: str = "mips-ido-c") -> str:
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

    def test_dereferenced_field_pointer_is_captured(self) -> None:
        output = self.decompile(
            "lw $t0, 4($a0)\nlw $v0, 8($t0)", "int test(void *object);"
        )
        self.assertIn("void *temp_t0;", output)
        self.assertIn("temp_t0 = M2C_FIELD(object, void **, 4);", output)
        self.assertIn("return M2C_FIELD(temp_t0, s32 *, 8);", output)

    def test_target_store_retains_existing_inline_access(self) -> None:
        output = self.decompile(
            "lw $t0, 4($a0)\nsb $a1, 8($t0)",
            "void test(void *object, int value);",
        )
        self.assertNotIn("temp_t0", output)
        self.assertIn("M2C_FIELD(M2C_FIELD(object, void **, 4), s8 *, 8)", output)

    def test_known_pointer_field_keeps_context_type(self) -> None:
        output = self.decompile(
            "lw $t0, 4($a0)\nlw $v0, 8($t0)",
            "struct S { int count; int *child; }; int test(struct S *object);",
        )
        self.assertIn("s32 *temp_t0;", output)
        self.assertIn("temp_t0 = object->child;", output)
        self.assertIn("s32 test(struct S *object)", output)

    def test_returned_pointer_without_dereference_does_not_gain_a_temp(self) -> None:
        output = self.decompile("lw $v0, 4($a0)", "void *test(void *object);")
        self.assertNotIn("temp_v0", output)

    def test_plain_parameter_pointer_does_not_gain_a_temp(self) -> None:
        output = self.decompile("lw $v0, 8($a0)", "int test(int *object);")
        self.assertNotIn("temp_a0", output)

    def test_gcc_keeps_existing_nested_access(self) -> None:
        output = self.decompile(
            "lw $t0, 4($a0)\nlw $v0, 8($t0)",
            "int test(void *object);",
            target="mips-gcc-c",
        )
        self.assertNotIn("temp_t0", output)

    def test_global_pointer_load_is_not_treated_as_a_field(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(pointer)\nlw $t0, %lo(pointer)($t0)\nlw $v0, 8($t0)",
            "extern int *pointer; int test(void);",
        )
        self.assertNotIn("temp_t0", output)
        self.assertIn("M2C_FIELD(pointer, s32 *, 8)", output)
