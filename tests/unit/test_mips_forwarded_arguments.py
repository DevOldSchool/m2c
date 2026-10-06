from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestMipsForwardedArguments(unittest.TestCase):
    def decompile(self, setup: str, context: str = "") -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(
                ".set noreorder\nglabel test\n"
                "addiu $sp, $sp, -0x20\nsw $ra, 0x1c($sp)\n"
                + setup
                + "\njal callee\nnop\nlw $ra, 0x1c($sp)\n"
                "addiu $sp, $sp, 0x20\njr $ra\nnop\n"
            )
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

    def test_forwarded_first_argument_keeps_its_slot(self) -> None:
        output = self.decompile("li $a1, 7\nsw $zero, 0x10($sp)")
        self.assertIn("callee(arg0, 7, arg2, arg3, 0)", output)

    def test_forwarded_middle_arguments_keep_their_slots(self) -> None:
        output = self.decompile("li $a0, 1\nli $a3, 4\nsw $zero, 0x10($sp)")
        self.assertIn("callee(1, arg1, arg2, 4, 0)", output)

    def test_stack_arguments_follow_all_four_integer_registers(self) -> None:
        output = self.decompile("li $a1, 2\nli $a2, 3\nli $a3, 4\nsw $zero, 0x10($sp)")
        self.assertIn("callee(arg0, 2, 3, 4, 0)", output)

    def test_unused_trailing_registers_are_not_added(self) -> None:
        output = self.decompile("li $a0, 1")
        self.assertIn("callee(1)", output)
        self.assertNotIn("arg1", output)

    def test_known_signature_is_authoritative(self) -> None:
        output = self.decompile("li $a1, 7", "void callee(void);")
        self.assertIn("callee()", output)
        self.assertNotIn("arg0", output)

    def test_float_argument_path_is_not_reinterpreted_as_integers(self) -> None:
        output = self.decompile("mtc1 $zero, $f12\nli $a1, 7\nsw $zero, 0x10($sp)")
        self.assertIn("callee(0, 7, 0)", output)
        self.assertNotIn("arg0", output)

    def test_call_clobbered_registers_are_not_invented(self) -> None:
        output = self.decompile("jal first\nnop\nli $a1, 7\nsw $zero, 0x10($sp)")
        self.assertNotIn("callee(arg0", output)

    def test_all_register_arguments_can_be_forwarded(self) -> None:
        output = self.decompile("sw $zero, 0x10($sp)")
        self.assertIn("callee(arg0, arg1, arg2, arg3, 0)", output)

    def test_no_stack_arguments_keeps_existing_inference(self) -> None:
        output = self.decompile("li $a1, 7")
        self.assertIn("callee(7)", output)
