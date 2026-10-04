from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestIntegerAddress(unittest.TestCase):
    def decompile(self, context: str) -> str:
        assembly = (
            Path(__file__).parents[1] / "end_to_end/integer-address-deref/irix-o2.s"
        )
        with TemporaryDirectory() as directory:
            context_file = Path(directory) / "context.c"
            context_file.write_text(context)
            flags = [
                "--target",
                "mips-ido-c",
                "--valid-syntax",
                "--no-cache",
                "--context",
                str(context_file),
                str(assembly),
            ]
            return decompile_and_capture_output(parse_flags(flags))

    def test_explicit_integer_address_keeps_its_type(self) -> None:
        output = self.decompile(
            "void test(int address, int *index, unsigned char value);"
        )
        self.assertIn("void test(s32 address, s32 *index, u8 value)", output)
        self.assertIn("M2C_FIELD((address + temp_v0), s8 *, 0)", output)
        self.assertNotIn("*(address +", output)

    def test_known_pointer_still_uses_array_access(self) -> None:
        output = self.decompile(
            "void test(unsigned char *address, int *index, unsigned char value);"
        )
        self.assertIn("void test(u8 *address, s32 *index, u8 value)", output)
        self.assertIn("address[temp_v0] = value & 0xFF;", output)
        self.assertNotIn("M2C_FIELD", output)
