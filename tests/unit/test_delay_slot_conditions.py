from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestDelaySlotConditions(unittest.TestCase):
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
                flags += ["--context", str(ctx)]
            return decompile_and_capture_output(parse_flags([*flags, str(asm)]))

    def test_loop_compares_old_cursor_before_delay_increment(self) -> None:
        for target in ("mips-ido-c", "mips-gcc-c"):
            with self.subTest(target=target):
                output = self.decompile(
                    "move $v0, $a0\n.Lloop:\nsb $a2, 0($v0)\n"
                    "bne $v0, $a1, .Lloop\naddiu $v0, $v0, 1",
                    "void test(unsigned char *start, unsigned char *end, int value);",
                    target,
                )
                self.assertIn("temp_cond = var_v0 != end;", output)
                self.assertIn("} while (temp_cond);", output)
                self.assertLess(
                    output.index("temp_cond ="), output.index("var_v0 += 1;")
                )

    def test_delay_decrement_tests_old_global(self) -> None:
        output = self.decompile(
            "lui $a0, %hi(counter)\naddiu $a0, $a0, %lo(counter)\n"
            "lw $v1, 0($a0)\nli $v0, 6\naddiu $t6, $v1, -1\n"
            "bgtz $v1, .Lend\nsw $t6, 0($a0)\nli $v0, 4\n.Lend:"
        )
        self.assertIn("temp_cond = counter > 0;", output)
        self.assertLess(output.index("temp_cond ="), output.index("counter -= 1;"))
        self.assertIn("if (!temp_cond)", output)

    def test_computed_condition_keeps_old_global_through_delay_store(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(counter)\naddiu $t0, $t0, %lo(counter)\n"
            "lw $t6, 0($t0)\nslti $a0, $t6, 1\naddiu $t7, $t6, -1\n"
            "li $v0, 6\nbeqz $a0, .Lend\nsw $t7, 0($t0)\nli $v0, 4\n.Lend:"
        )
        self.assertLess(output.index("counter < 1"), output.index("counter -= 1;"))
        self.assertIn("if (!temp_cond)", output)

    def test_increment_before_branch_needs_no_condition_snapshot(self) -> None:
        output = self.decompile(
            "move $v0, $a0\n.Lloop:\nsb $a2, 0($v0)\n"
            "addiu $v0, $v0, 1\nbne $v0, $a1, .Lloop\nnop",
            "void test(unsigned char *start, unsigned char *end, int value);",
        )
        self.assertNotIn("temp_cond", output)
        self.assertIn("} while (var_v0 != end);", output)

    def test_unrelated_delay_write_needs_no_snapshot(self) -> None:
        output = self.decompile(
            "li $v0, 0\n.Lloop:\naddiu $a0, $a0, -1\n"
            "bnez $a0, .Lloop\naddiu $v0, $v0, 1"
        )
        self.assertNotIn("temp_cond", output)

    def test_existing_value_snapshot_is_reused(self) -> None:
        output = self.decompile(
            "li $v1, 0\n.Lloop:\naddiu $v1, $v1, 1\n"
            "sll $t3, $v1, 1\nslti $at, $t3, 5\n"
            "bnez $at, .Lloop\nmove $v1, $t3\nmove $v0, $v1"
        )
        self.assertNotIn("temp_cond", output)
        self.assertIn("} while (temp_t3 < 5);", output)

    def test_branch_likely_slot_stays_on_taken_path(self) -> None:
        output = self.decompile(
            "beql $a0, $zero, .Lend\naddiu $a0, $a0, 1\n"
            "addiu $a0, $a0, 10\n.Lend:\nmove $v0, $a0",
            "int test(int value);",
        )
        self.assertNotIn("temp_cond", output)
        self.assertIn("value == 0", output)
        self.assertIn("var_a0 = value + 1;", output)
        self.assertIn("var_a0 = value + 0xA;", output)
