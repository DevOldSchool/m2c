from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestMipsNarrowStores(unittest.TestCase):
    def decompile(self, target: str, context: str = "") -> str:
        # This fixture was compiled from word-sized parameters by IDO. Reuse
        # it to check context overrides and other compiler targets as well.
        assembly = (
            Path(__file__).parents[1] / "end_to_end/ido-narrow-store-args/irix-o2.s"
        )
        with TemporaryDirectory() as directory:
            flags = ["--target", target, "--valid-syntax", "--no-cache"]
            if context:
                context_file = Path(directory) / "context.c"
                context_file.write_text(context)
                flags.extend(["--context", str(context_file)])
            flags.append(str(assembly))
            return decompile_and_capture_output(parse_flags(flags))

    def test_unknown_ido_register_parameters(self) -> None:
        output = self.decompile("mips-ido-c")
        self.assertIn("void test(void *arg0, s32 arg1, s32 arg2)", output)
        self.assertIn("= (s8) arg1;", output)
        self.assertIn("= (s16) arg2;", output)

    def test_known_narrow_parameters(self) -> None:
        output = self.decompile(
            "mips-ido-c", "void test(void *, signed char, signed short);"
        )
        self.assertIn("void test(void *arg0, s8 arg1, s16 arg2)", output)
        self.assertNotIn("(s8) arg1", output)
        self.assertNotIn("(s16) arg2", output)

    def test_known_unsigned_parameters(self) -> None:
        output = self.decompile(
            "mips-ido-c", "void test(void *, unsigned char, unsigned short);"
        )
        self.assertIn("void test(void *arg0, u8 arg1, u16 arg2)", output)

    def test_known_word_parameters(self) -> None:
        output = self.decompile("mips-ido-c", "void test(void *, int, int);")
        self.assertIn("void test(void *arg0, s32 arg1, s32 arg2)", output)

    def test_gcc_inference_unchanged(self) -> None:
        output = self.decompile("mips-gcc-c")
        self.assertIn("void test(void *arg0, s8 arg1, s16 arg2)", output)
