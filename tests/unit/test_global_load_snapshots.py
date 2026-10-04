from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestGlobalLoadSnapshots(unittest.TestCase):
    def decompile(
        self, target: str, context: str, assembly_text: Optional[str] = None
    ) -> str:
        assembly = (
            Path(__file__).parents[1] / "end_to_end/ido-global-load-snapshots/irix-o2.s"
        )
        with TemporaryDirectory() as directory:
            if assembly_text is not None:
                assembly = Path(directory) / "test.s"
                assembly.write_text(assembly_text)
            context_file = Path(directory) / "context.c"
            context_file.write_text(context)
            return decompile_and_capture_output(
                parse_flags(
                    [
                        "--target",
                        target,
                        "--valid-syntax",
                        "--no-cache",
                        "--context",
                        str(context_file),
                        str(assembly),
                    ]
                )
            )

    def test_byte_and_halfword_reads_are_captured_once(self) -> None:
        output = self.decompile(
            "mips-ido-c",
            "extern unsigned char byte_count; extern unsigned short half_count;"
            "void test(unsigned char *out); void test_half(unsigned short *out);",
        )
        for global_name in ("byte_count", "half_count"):
            self.assertEqual(1, output.count(global_name))
            self.assertIn("s32 temp_v0;", output)
            self.assertIn(f"temp_v0 = {global_name};", output)
        self.assertIn("temp_v0 + 1", output)

    def test_load_signedness_does_not_change_explicit_context(self) -> None:
        output = self.decompile(
            "mips-ido-c",
            "extern signed char byte_count; extern signed short half_count;"
            "void test(unsigned char *out); void test_half(unsigned short *out);",
        )
        self.assertIn("temp_v0 = (u8) byte_count;", output)
        self.assertIn("temp_v0 = (u16) half_count;", output)
        self.assertEqual(1, output.count("byte_count"))
        self.assertEqual(1, output.count("half_count"))

    def test_gcc_retains_existing_global_read_heuristic(self) -> None:
        output = self.decompile(
            "mips-gcc-c",
            "extern unsigned char byte_count; extern unsigned short half_count;"
            "void test(unsigned char *out); void test_half(unsigned short *out);",
        )
        self.assertNotIn("temp_v0 = byte_count", output)
        self.assertNotIn("temp_v0 = half_count", output)
        self.assertGreater(output.count("byte_count"), 1)
        self.assertGreater(output.count("half_count"), 1)

    def test_signed_loads_keep_sign_extension_with_word_locals(self) -> None:
        assembly = (
            (
                Path(__file__).parents[1]
                / "end_to_end/ido-global-load-snapshots/irix-o2.s"
            )
            .read_text()
            .replace("lbu ", "lb ")
            .replace("lhu ", "lh ")
        )
        output = self.decompile(
            "mips-ido-c",
            "extern unsigned char byte_count; extern unsigned short half_count;"
            "void test(unsigned char *out); void test_half(unsigned short *out);",
            assembly,
        )
        self.assertEqual(2, output.count("s32 temp_v0;"))
        self.assertIn("temp_v0 = (s8) byte_count;", output)
        self.assertIn("temp_v0 = (s16) half_count;", output)

    def test_word_snapshot_preserves_explicit_narrow_return(self) -> None:
        output = self.decompile(
            "mips-ido-c",
            "extern unsigned char byte_count; signed char test(unsigned char *out);",
            ".set noreorder\nglabel test\n"
            "lui $v0, %hi(byte_count)\nlb $v0, %lo(byte_count)($v0)\n"
            "sb $v0, 0($a0)\njr $ra\nnop\n",
        )
        self.assertIn("s8 test(u8 *out)", output)
        self.assertIn("s32 temp_v0;", output)
        self.assertIn("temp_v0 = (s8) byte_count;", output)

    def test_single_use_load_preserves_inferred_narrow_return(self) -> None:
        output = self.decompile(
            "mips-ido-c",
            "",
            ".set noreorder\nglabel test\n"
            "lui $v0, %hi(byte_count)\nlb $v0, %lo(byte_count)($v0)\n"
            "jr $ra\nnop\n",
        )
        self.assertIn("s8 test(void)", output)
        self.assertNotIn("temp_v0", output)
