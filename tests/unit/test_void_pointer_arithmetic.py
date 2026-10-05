import unittest

from m2c.options import Formatter
from m2c.translate import (
    BinaryOp,
    GlobalSymbol,
    Literal,
    format_assignment,
    format_expr,
)
from m2c.types import Type


class TestVoidPointerArithmetic(unittest.TestCase):
    def test_void_pointer_addition_uses_bytes_without_changing_types(self) -> None:
        pointer_type = Type.ptr(Type.void())
        pointer = GlobalSymbol(c_symbol_name="p", type=pointer_type)
        expr = BinaryOp(left=pointer, op="+", right=Literal(8), type=pointer_type)
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "(u8 *) p + 8"
        )
        target = pointer.type.get_pointer_target()
        assert target is not None
        self.assertTrue(target.is_void())

    def test_unspecified_pointer_target_uses_bytes(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="p", type=Type.ptr())
        expr = BinaryOp(left=pointer, op="+", right=Literal(8), type=pointer.type)
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "(u8 *) p + 8"
        )
        self.assertIsNone(pointer.type.get_pointer_target())

    def test_negative_offset_keeps_byte_count(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="p", type=Type.ptr(Type.void()))
        expr = BinaryOp(left=pointer, op="+", right=Literal(-8), type=pointer.type)
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "(u8 *) p - 8"
        )

    def test_void_pointer_compound_assignment_is_explicit(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="p", type=Type.ptr(Type.void()))
        for op in ("+", "-"):
            expr = BinaryOp(left=pointer, op=op, right=Literal(8), type=pointer.type)
            self.assertEqual(
                format_assignment(pointer, expr, Formatter(valid_syntax=True)),
                f"p = (u8 *) p {op} 8;",
            )

    def test_pointer_difference_keeps_byte_units(self) -> None:
        lhs = GlobalSymbol(c_symbol_name="a", type=Type.ptr(Type.void()))
        rhs = GlobalSymbol(c_symbol_name="b", type=Type.ptr(Type.void()))
        expr = BinaryOp(left=lhs, op="-", right=rhs, type=Type.s32())
        self.assertEqual(
            format_expr(expr, Formatter(valid_syntax=True)), "(u8 *) a - (u8 *) b"
        )

    def test_typed_pointer_keeps_element_scaling(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="p", type=Type.ptr(Type.s32()))
        expr = BinaryOp(
            left=pointer, op="+", right=Literal(8), type=pointer.type, byte_offset=True
        )
        self.assertEqual(format_expr(expr, Formatter(valid_syntax=True)), "p + 2")
        self.assertEqual(
            format_assignment(pointer, expr, Formatter(valid_syntax=True)), "p += 2;"
        )

    def test_diagnostic_output_keeps_existing_form(self) -> None:
        pointer = GlobalSymbol(c_symbol_name="p", type=Type.ptr(Type.void()))
        expr = BinaryOp(left=pointer, op="+", right=Literal(8), type=pointer.type)
        self.assertEqual(format_expr(expr, Formatter()), "p + 8")
