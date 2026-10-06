from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from typing import List, Optional

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestIdoAbsIntrinsics(unittest.TestCase):
    def decompile(
        self,
        instruction: str = "abs.s $f0, $f12",
        context: str = "",
        flags: Optional[List[str]] = None,
    ) -> str:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            asm = root / "test.s"
            asm.write_text(".set noreorder\nglabel test\njr $ra\n" + instruction + "\n")
            ctx = root / "context.c"
            ctx.write_text(context)
            args = [
                "--target",
                "mips-ido-c",
                "--valid-syntax",
                "--no-cache",
                "--context",
                str(ctx),
                str(asm),
            ]
            args += flags or []
            return decompile_and_capture_output(parse_flags(args))

    def test_single_precision_declares_intrinsic(self) -> None:
        output = self.decompile()
        self.assertIn("f32 fabsf(f32);", output)
        self.assertEqual(output.count("#pragma intrinsic(fabsf)"), 1)

    def test_double_precision_declares_intrinsic(self) -> None:
        output = self.decompile("abs.d $f0, $f12")
        self.assertIn("f64 fabs(f64);", output)
        self.assertIn("#pragma intrinsic(fabs)", output)

    def test_context_declaration_is_not_repeated(self) -> None:
        output = self.decompile(context="typedef float f32; f32 fabsf(f32);")
        self.assertNotIn("f32 fabsf(f32);", output)
        self.assertIn("#pragma intrinsic(fabsf)", output)

    def test_global_declarations_none_is_respected(self) -> None:
        output = self.decompile(flags=["--globals", "none"])
        self.assertNotIn("#pragma", output)
        self.assertNotIn("f32 fabsf(f32);", output)

    def test_other_compiler_is_unchanged(self) -> None:
        output = self.decompile(flags=["--target", "mips-gcc-c"])
        self.assertNotIn("#pragma", output)
        self.assertNotIn("f32 fabsf(f32);", output)

    def test_ordinary_math_call_is_not_marked_intrinsic(self) -> None:
        with TemporaryDirectory() as directory:
            asm = Path(directory) / "test.s"
            asm.write_text(
                ".set noreorder\nglabel test\naddiu $sp,$sp,-0x18\nsw $ra,0x14($sp)\njal fabsf\nnop\nlw $ra,0x14($sp)\njr $ra\naddiu $sp,$sp,0x18\n"
            )
            output = decompile_and_capture_output(
                parse_flags(
                    ["--target", "mips-ido-c", "--valid-syntax", "--no-cache", str(asm)]
                )
            )
            self.assertNotIn("#pragma", output)

    def test_mixed_ordinary_call_is_not_rewritten(self) -> None:
        with TemporaryDirectory() as directory:
            asm = Path(directory) / "test.s"
            asm.write_text(
                ".set noreorder\nglabel test\naddiu $sp,$sp,-0x18\nsw $ra,0x14($sp)\nabs.s $f12,$f12\njal fabsf\nnop\nlw $ra,0x14($sp)\njr $ra\naddiu $sp,$sp,0x18\n"
            )
            output = decompile_and_capture_output(
                parse_flags(
                    ["--target", "mips-ido-c", "--valid-syntax", "--no-cache", str(asm)]
                )
            )
            self.assertNotIn("#pragma", output)

    def test_unrelated_instruction_emits_no_math_declaration(self) -> None:
        output = self.decompile("neg.s $f0, $f12")
        self.assertNotIn("#pragma", output)
        self.assertNotIn("fabs", output)
