import unittest

from m2c.options import Formatter
from m2c.translate import BinaryOp, GlobalSymbol, Literal, format_expr
from m2c.types import FunctionSignature, Type


class TestPointerEquality(unittest.TestCase):
    def comparison(
        self, left_type: Type, right_type: Type, op: str = "==", valid: bool = True
    ) -> str:
        lhs = GlobalSymbol(c_symbol_name="a", type=left_type)
        rhs = GlobalSymbol(c_symbol_name="b", type=right_type)
        expr = BinaryOp(left=lhs, op=op, right=rhs, type=Type.boolean())
        return format_expr(expr, Formatter(valid_syntax=valid))

    def test_different_object_pointer_types_compare_addresses(self) -> None:
        left_target, right_target = Type.u8(), Type.u16()
        for op in ("==", "!="):
            self.assertEqual(
                self.comparison(Type.ptr(left_target), Type.ptr(right_target), op),
                f"(void *) a {op} (void *) b",
            )
        self.assertEqual(left_target.get_size_bytes(), 1)
        self.assertEqual(right_target.get_size_bytes(), 2)

    def test_same_pointer_type_does_not_need_casts(self) -> None:
        self.assertEqual(
            self.comparison(Type.ptr(Type.u8()), Type.ptr(Type.u8())), "a == b"
        )

    def test_void_pointer_is_already_compatible(self) -> None:
        self.assertEqual(
            self.comparison(Type.ptr(Type.void()), Type.ptr(Type.u8())), "a == b"
        )

    def test_array_decay_uses_element_types(self) -> None:
        self.assertEqual(
            self.comparison(Type.ptr(Type.u8()), Type.array(Type.u16(), 4)),
            "(void *) a == (void *) b",
        )
        self.assertEqual(
            self.comparison(Type.array(Type.u8(), 4), Type.array(Type.u8(), 8)),
            "a == b",
        )

    def test_pointer_integer_comparison_does_not_cast_integer(self) -> None:
        self.assertEqual(self.comparison(Type.ptr(Type.u8()), Type.s32()), "a == b")
        pointer = GlobalSymbol(c_symbol_name="a", type=Type.ptr(Type.u8()))
        expr = BinaryOp(left=pointer, op="==", right=Literal(0), type=Type.boolean())
        self.assertEqual(format_expr(expr, Formatter(valid_syntax=True)), "a == NULL")

    def test_function_pointers_keep_existing_comparison(self) -> None:
        signature = FunctionSignature(return_type=Type.void(), params_known=True)
        self.assertEqual(
            self.comparison(Type.ptr(Type.function(signature)), Type.ptr(Type.u8())),
            "a == b",
        )

    def test_ordering_and_diagnostic_forms_are_unchanged(self) -> None:
        self.assertEqual(
            self.comparison(Type.ptr(Type.u8()), Type.ptr(Type.u16()), "<"), "a < b"
        )
        self.assertEqual(
            self.comparison(Type.ptr(Type.u8()), Type.ptr(Type.u16()), valid=False),
            "a == b",
        )
