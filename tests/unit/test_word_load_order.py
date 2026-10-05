from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestWordLoadOrder(unittest.TestCase):
    def decompile(
        self, body: str, *, target: str = "mips-ido-c", context: str = ""
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

    def body(self, narrow: str = "sh", base: str = "$a0") -> str:
        return f"""lw $t6, 0($a0)
li $t8, 32
{narrow} $t8, 6({base})
ori $t7, $t6, 1
sw $t7, 0($a0)"""

    def test_word_snapshot_precedes_byte_and_halfword_stores(self) -> None:
        for mnemonic in ("sb", "sh"):
            with self.subTest(mnemonic=mnemonic):
                output = self.decompile(self.body(mnemonic))
                self.assertIn("s32 temp_t6;", output)
                self.assertIn("temp_t6 =", output)
                self.assertIn("temp_t6 | 1", output)
                self.assertLess(output.index("temp_t6 ="), output.index("= 0x20;"))

    def test_context_type_and_named_fields_are_preserved(self) -> None:
        output = self.decompile(
            self.body(),
            context="struct Object { unsigned int flags; short unused; short state; };"
            "void test(struct Object *object);",
        )
        self.assertIn("u32 temp_t6;", output)
        self.assertIn("temp_t6 = object->flags;", output)
        self.assertIn("object->state = 0x20;", output)
        self.assertIn("object->flags = temp_t6 | 1;", output)

    def test_pointer_word_load_keeps_its_context_type(self) -> None:
        output = self.decompile(
            "lw $t6, 0($a0)\nli $t8, 32\nsh $t8, 6($a0)\nsw $zero, 0($t6)",
            context="struct Object { int *pointer; short unused; short state; };"
            "void test(struct Object *object);",
        )
        self.assertIn("s32 *temp_t6;", output)
        self.assertIn("temp_t6 = object->pointer;", output)
        self.assertIn("*temp_t6 = 0;", output)

    def test_gcc_does_not_use_the_ido_ordering_rule(self) -> None:
        output = self.decompile(self.body(), target="mips-gcc-c")
        self.assertNotIn("temp_t6", output)

    def test_other_object_and_word_store_retain_existing_handling(self) -> None:
        for body in (
            self.body(base="$a1"),
            self.body("sw").replace("6($a0)", "4($a0)"),
        ):
            with self.subTest(body=body):
                self.assertNotIn("temp_t6", self.decompile(body))

    def test_unused_read_and_read_after_store_do_not_gain_temps(self) -> None:
        for body in (
            "lw $t6, 0($a0)\nli $t8, 32\nsh $t8, 6($a0)",
            "li $t8, 32\nsh $t8, 6($a0)\nlw $t6, 0($a0)\n"
            "ori $t7, $t6, 1\nsw $t7, 0($a0)",
        ):
            with self.subTest(body=body):
                self.assertNotIn("temp_t6", self.decompile(body))
