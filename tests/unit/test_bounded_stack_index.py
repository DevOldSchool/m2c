from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from m2c.options import Formatter
from m2c.translate import BinaryOp, GlobalSymbol, Literal, bounded_stack_index
from m2c.types import Type
from run_tests import decompile_and_capture_output


class TestBoundedStackIndex(unittest.TestCase):
    def decompile(self, mask: int = 1, context: str = "") -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(
                f""".set noreorder
glabel test
addiu $sp, $sp, -40
sw $ra, 20($sp)
lui $t7, %hi(data)
addiu $t7, $t7, %lo(data)
lw $t0, 0($t7)
lw $t1, 4($t7)
addiu $t6, $sp, 32
sw $t0, 0($t6)
jal pick
sw $t1, 4($t6)
andi $t2, $v0, {mask}
sll $t2, $t2, 2
addu $v0, $sp, $t2
lbu $v0, 35($v0)
lw $ra, 20($sp)
addiu $sp, $sp, 40
jr $ra
nop
"""
            )
            ctx = path / "context.c"
            ctx.write_text(
                "extern int data[2]; int pick(void); unsigned char test(void);\n"
                + context
            )
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

    def test_bounded_byte_read_uses_the_copied_local_array(self) -> None:
        output = self.decompile()
        self.assertIn("s32 sp20[2];", output)
        self.assertIn("((u8 *) &sp20 + ((pick() & 1) * 4))", output)
        self.assertIn("u8 *, 3)", output)
        self.assertNotIn("M2C_UNK", output)
        self.assertNotIn("(u8 *) sp +", output)

    def test_out_of_bounds_index_does_not_infer_an_array(self) -> None:
        output = self.decompile(mask=2)
        self.assertNotIn("s32 sp20[2];", output)
        self.assertIn("M2C_UNK", output)

    def test_context_array_extent_and_name_are_preserved(self) -> None:
        output = self.decompile(
            context="struct _m2c_stack_test { char pad[32]; int values[2]; };"
        )
        self.assertIn("s32 values[2];", output)
        self.assertIn("((u8 *) &values + ((pick() & 1) * 4))", output)
        self.assertNotIn("M2C_UNK", output)

    def test_mask_and_stride_give_a_conservative_byte_bound(self) -> None:
        sp = GlobalSymbol(c_symbol_name="sp", type=Type.ptr())
        value = GlobalSymbol(c_symbol_name="index", type=Type.u32())
        mask = BinaryOp(left=value, op="&", right=Literal(3), type=Type.u32())
        scaled = BinaryOp(left=mask, op="*", right=Literal(4), type=Type.u32())
        address = BinaryOp(left=sp, op="+", right=scaled, type=Type.ptr())
        result = bounded_stack_index(address)
        assert result is not None
        self.assertEqual(result[1], 12)
        self.assertEqual(result[0].format(Formatter()), "((index & 3) * 4)")

    def test_unmasked_index_is_not_assumed_bounded(self) -> None:
        sp = GlobalSymbol(c_symbol_name="sp", type=Type.ptr())
        index = GlobalSymbol(c_symbol_name="index", type=Type.u32())
        scaled = BinaryOp(left=index, op="*", right=Literal(4), type=Type.u32())
        address = BinaryOp(left=sp, op="+", right=scaled, type=Type.ptr())
        self.assertIsNone(bounded_stack_index(address))

    def test_other_base_address_is_not_treated_as_stack(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="buffer", type=Type.ptr())
        mask = BinaryOp(left=Literal(5), op="&", right=Literal(1), type=Type.u32())
        scaled = BinaryOp(left=mask, op="*", right=Literal(4), type=Type.u32())
        address = BinaryOp(left=pointer, op="+", right=scaled, type=Type.ptr())
        self.assertIsNone(bounded_stack_index(address))
