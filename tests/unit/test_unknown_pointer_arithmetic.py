from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output
from m2c.options import Formatter
from m2c.translate import (
    AddressOf,
    BinaryOp,
    GlobalSymbol,
    Literal,
    format_assignment,
    format_expr,
)
from m2c.types import FunctionSignature, Type


class TestUnknownPointerArithmetic(unittest.TestCase):
    def test_unknown_pointee_stride_counts_bytes_and_keeps_pointer_type(self) -> None:
        target = Type.any()
        pointer = GlobalSymbol("p", Type.ptr(target))
        for offset in (56, -56, 812):
            expr = BinaryOp(pointer, "+", Literal(offset), pointer.type)
            text = format_assignment(pointer, expr, Formatter(valid_syntax=True))
            self.assertIn("(u8 *) p", text)
            self.assertIn("(M2C_UNK *)", text)
            self.assertNotIn("p +=", text)
            self.assertNotIn("p -=", text)
        self.assertIsNone(target.get_size_bytes())

    def test_unknown_pointer_difference_counts_bytes(self) -> None:
        a = GlobalSymbol("a", Type.ptr(Type.any()))
        b = GlobalSymbol("b", Type.ptr(Type.any()))
        expr = BinaryOp(a, "-", b, Type.s32())
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "(u8 *) a - (u8 *) b"
        )

    def test_known_element_stride_is_not_changed(self) -> None:
        p = GlobalSymbol("p", Type.ptr(Type.s32()))
        expr = BinaryOp(p, "+", Literal(14), p.type)
        self.assertEqual(
            format_assignment(p, expr, Formatter(valid_syntax=True)), "p += 0xE;"
        )

    def test_known_byte_offset_is_scaled_once(self) -> None:
        p = GlobalSymbol("p", Type.ptr(Type.s32()))
        expr = BinaryOp(p, "+", Literal(56), p.type, byte_offset=True)
        self.assertEqual(
            format_assignment(p, expr, Formatter(valid_syntax=True)), "p += 0xE;"
        )

    def test_function_pointer_is_not_treated_as_unknown_object_storage(self) -> None:
        t = Type.ptr(
            Type.function(FunctionSignature(return_type=Type.void(), params_known=True))
        )
        p = GlobalSymbol("p", t)
        expr = BinaryOp(p, "+", Literal(1), t)
        self.assertNotIn("u8", format_expr(expr, Formatter(valid_syntax=True)))

    def test_diagnostic_output_is_unchanged(self) -> None:
        p = GlobalSymbol("p", Type.ptr(Type.any()))
        expr = BinaryOp(p, "+", Literal(56), p.type)
        self.assertEqual(format_assignment(p, expr, Formatter()), "p += 0x38;")

    def test_unknown_address_storage_comparison_uses_emitted_types(self) -> None:
        target = Type.any()
        p = GlobalSymbol("p", Type.ptr(target))
        storage = GlobalSymbol("end", target, is_referenced=True)
        end = AddressOf(storage, type=storage.type.reference())
        expr = BinaryOp(p, "!=", end, Type.boolean())
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)),
            "(void *) p != (void *) ((u8 *) end)",
        )
        self.assertIsNone(target.get_size_bytes())

    def test_two_byte_storage_addresses_need_no_comparison_cast(self) -> None:
        a = GlobalSymbol("a", Type.any(), is_referenced=True)
        b = GlobalSymbol("b", Type.any(), is_referenced=True)
        expr = BinaryOp(
            AddressOf(a, a.type.reference()),
            "==",
            AddressOf(b, b.type.reference()),
            Type.boolean(),
        )
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "((u8 *) a) == ((u8 *) b)"
        )

    def test_mips_mixed_width_loop_uses_byte_stride_and_valid_comparison(self) -> None:
        for stride in (56, 812):
            with self.subTest(stride=stride), TemporaryDirectory() as directory:
                asm = Path(directory) / "test.s"
                asm.write_text(
                    ".set noreorder\nglabel test\n"
                    "lui $v0, %hi(storage)\naddiu $v0, $v0, %lo(storage)\n"
                    "lui $v1, %hi(end)\naddiu $v1, $v1, %lo(end)\n"
                    ".Lloop:\nsh $zero, 0($v0)\nsb $zero, 12($v0)\n"
                    f"addiu $v0, $v0, {stride}\nbne $v0, $v1, .Lloop\nnop\n"
                    "jr $ra\nnop\n"
                )
                output = decompile_and_capture_output(
                    parse_flags(
                        [
                            "--target",
                            "mips-ido-c",
                            "--valid-syntax",
                            "--no-cache",
                            str(asm),
                        ]
                    )
                )
                self.assertIn(
                    f"var_v0 = (M2C_UNK *) ((u8 *) var_v0 + 0x{stride:X});", output
                )
                self.assertIn("(void *) var_v0 != (void *) ((u8 *) end)", output)
                self.assertIn("s16 *, 0)", output)
                self.assertIn("s8 *, 0xC)", output)
