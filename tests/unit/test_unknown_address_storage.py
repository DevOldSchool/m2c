from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from m2c.options import Formatter
from m2c.translate import AddressOf, GlobalSymbol
from m2c.types import Type
from run_tests import decompile_and_capture_output


class TestUnknownAddressStorage(unittest.TestCase):
    def decompile(self, body: str, context: str = "", valid: bool = True) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(f".set noreorder\nglabel test\n{body}\njr $ra\nnop\n")
            flags = ["--target", "mips-ido-c", "--no-cache"]
            if valid:
                flags.append("--valid-syntax")
            if context:
                ctx = path / "context.c"
                ctx.write_text(context)
                flags.extend(["--context", str(ctx)])
            return decompile_and_capture_output(parse_flags([*flags, str(asm)]))

    base = "lui $t0, %hi(storage)\naddiu $t0, $t0, %lo(storage)\n"

    def test_external_storage_has_unspecified_extent(self) -> None:
        output = self.decompile(self.base + "sh $a0, 0($t0)\nsh $a1, 2($t0)")
        self.assertIn("extern u8 storage[];", output)
        self.assertIn("M2C_FIELD(((u8 *) storage), s16 *, 0)", output)
        self.assertIn("M2C_FIELD(((u8 *) storage), s16 *, 2)", output)
        self.assertNotIn("M2C_UNK", output)

    def test_indexing_keeps_byte_offsets_and_store_width(self) -> None:
        output = self.decompile(
            self.base + "sll $t1, $a0, 2\naddu $v0, $t0, $t1\nsb $a1, 1($v0)"
        )
        self.assertIn("(((u8 *) storage) + (arg0 * 4))", output)
        self.assertIn("s8 *, 1)", output)

    def test_known_scalar_inference_is_unchanged(self) -> None:
        output = self.decompile(self.base + "lw $v0, 0($t0)")
        self.assertIn("extern s32 storage;", output)
        self.assertIn("return storage;", output)
        self.assertNotIn("byte-addressed", output)

    def test_context_structure_fields_remain_named(self) -> None:
        output = self.decompile(
            self.base + "sh $a0, 0($t0)\nsh $a1, 2($t0)",
            "struct S { short first; short second; }; extern struct S storage;",
        )
        self.assertIn("storage.first", output)
        self.assertIn("storage.second", output)
        self.assertNotIn("extern u8 storage[]", output)

    def test_direct_value_use_disables_storage_fallback(self) -> None:
        symbol = GlobalSymbol(c_symbol_name="storage", type=Type.any())
        address = AddressOf(symbol)
        address.use()
        self.assertTrue(symbol.is_unknown_address_storage(Formatter(valid_syntax=True)))
        symbol.use()
        self.assertFalse(
            symbol.is_unknown_address_storage(Formatter(valid_syntax=True))
        )
        self.assertEqual(address.format(Formatter(valid_syntax=True)), "&storage")

    def test_diagnostic_output_retains_unknown_layout(self) -> None:
        output = self.decompile(
            self.base + "sh $a0, 0($t0)\nsh $a1, 2($t0)", valid=False
        )
        self.assertNotIn("extern u8 storage[]", output)
        self.assertIn("extern ? storage;", output)
