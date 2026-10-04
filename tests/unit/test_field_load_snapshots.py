from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestFieldLoadSnapshots(unittest.TestCase):
    def decompile(self, body: str, context: str, target: str = "mips-ido-c") -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            assembly = path / "test.s"
            assembly.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
            context_file = path / "context.c"
            context_file.write_text(context)
            return decompile_and_capture_output(
                parse_flags(
                    [
                        "--target",
                        target,
                        "--valid-syntax",
                        "--no-cache",
                        "--context",
                        str(context_file),
                        str(assembly),
                    ]
                )
            )

    def test_narrow_loads_use_word_locals_and_preserve_return_types(self) -> None:
        for load, store, scalar, returned in (
            ("lb", "sb", "char", "s8"),
            ("lbu", "sb", "unsigned char", "u8"),
            ("lh", "sh", "short", "s16"),
            ("lhu", "sh", "unsigned short", "u16"),
        ):
            with self.subTest(load=load):
                output = self.decompile(
                    f"{load} $v0, 0($a0)\n{store} $v0, 0($a1)",
                    f"struct Object {{ {scalar} value; }};"
                    f"{scalar} test(struct Object *object, {scalar} *out);",
                )
                self.assertIn("s32 temp_v0;", output)
                self.assertIn("temp_v0 = object->value;", output)
                self.assertIn(f"{returned} test(", output)
                self.assertEqual(1, output.count("object->value"))
                self.assertIn("return temp_v0;", output)

    def test_load_signedness_overrides_unsigned_field_context(self) -> None:
        for load, store, scalar, cast in (
            ("lb", "sb", "unsigned char", "s8"),
            ("lh", "sh", "unsigned short", "s16"),
        ):
            with self.subTest(load=load):
                output = self.decompile(
                    f"{load} $v0, 0($a0)\n{store} $v0, 0($a1)",
                    f"struct Object {{ {scalar} value; }};"
                    "int test(struct Object *object, void *out);",
                )
                self.assertIn("s32 temp_v0;", output)
                self.assertIn(f"temp_v0 = ({cast}) object->value;", output)

    def test_single_use_field_does_not_gain_a_temp(self) -> None:
        output = self.decompile(
            "lbu $v0, 0($a0)",
            "struct Object { unsigned char value; };"
            "unsigned char test(struct Object *object);",
        )
        self.assertNotIn("temp_v0", output)
        self.assertIn("u8 test(", output)
        self.assertIn("return object->value;", output)

    def test_gcc_retains_narrow_snapshot_type(self) -> None:
        output = self.decompile(
            "lbu $v0, 0($a0)\nsb $v0, 0($a1)",
            "struct Object { unsigned char value; };"
            "unsigned char test(struct Object *object, unsigned char *out);",
            target="mips-gcc-c",
        )
        self.assertIn("u8 temp_v0;", output)
        self.assertNotIn("s32 temp_v0;", output)

    def test_word_load_keeps_unsigned_context_type(self) -> None:
        output = self.decompile(
            "lw $v0, 0($a0)\nsw $v0, 0($a1)",
            "struct Object { unsigned int value; };"
            "unsigned int test(struct Object *object, unsigned int *out);",
        )
        self.assertIn("u32 temp_v0;", output)
        self.assertNotIn("s32 temp_v0;", output)

    def test_branch_join_keeps_narrow_phi_type(self) -> None:
        output = self.decompile(
            "bnez $a2, .Lother\nnop\nlbu $v0, 0($a0)\n"
            "b .Ljoin\nnop\n.Lother:\nlbu $v0, 1($a0)\n"
            ".Ljoin:\nsb $v0, 0($a1)",
            "unsigned char test(unsigned char *input, unsigned char *out, int choice);",
        )
        self.assertIn("u8 var_v0;", output)
        self.assertNotIn("s32 var_v0;", output)
        self.assertIn("u8 test(", output)
