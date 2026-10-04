from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from m2c.options import Formatter
from m2c.translate import BinaryOp, GlobalSymbol, Literal, format_assignment
from m2c.types import Type
from run_tests import decompile_and_capture_output


class TestPointerByteOffsets(unittest.TestCase):
    def decompile_step(self, typename: str, offset: int) -> str:
        # The loaded pointer advances by an ASM byte immediate, then is saved.
        assembly = f"""glabel test
 lw $v0, 0($a0)
 addiu $v0, $v0, {offset}
 sw $v0, 0($a0)
 jr $ra
 nop
"""
        with TemporaryDirectory() as directory:
            path = Path(directory)
            context = path / "context.c"
            context.write_text(f"void test({typename} **ptr);")
            asm = path / "test.s"
            asm.write_text(assembly)
            return decompile_and_capture_output(
                parse_flags(
                    [
                        "--target",
                        "mips-ido-c",
                        "--valid-syntax",
                        "--no-cache",
                        "--context",
                        str(context),
                        str(asm),
                    ]
                )
            )

    def test_word_and_halfword_offsets_count_elements(self) -> None:
        self.assertIn("*ptr += 3;", self.decompile_step("int", 12))
        self.assertIn("*ptr += 6;", self.decompile_step("short", 12))

    def test_negative_offsets_count_elements(self) -> None:
        self.assertIn("*ptr -= 3;", self.decompile_step("int", -12))
        self.assertIn("*ptr -= 6;", self.decompile_step("short", -12))

    def test_byte_pointer_offset_is_unchanged(self) -> None:
        self.assertIn("*ptr += 0xC;", self.decompile_step("char", 12))
        self.assertIn("*ptr -= 0xC;", self.decompile_step("char", -12))

    def test_formatting_preserves_raw_ir_offset(self) -> None:
        pointer = GlobalSymbol("p", Type.s32().reference())
        offset = Literal(12)
        expression = BinaryOp(pointer, "+", offset, pointer.type, byte_offset=True)
        fmt = Formatter()
        self.assertEqual("p += 3;", format_assignment(pointer, expression, fmt))
        self.assertEqual("(p + 3)", expression.format(fmt))
        self.assertIs(expression.right, offset)
        self.assertEqual(12, offset.value)
        # Already scaled C arithmetic must not be scaled a second time.
        elements = BinaryOp(pointer, "+", Literal(3), pointer.type)
        self.assertEqual("p += 3;", format_assignment(pointer, elements, fmt))
