from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestReusedHi(unittest.TestCase):
    def decompile(
        self, body: str, *, context: str = "", target: str = "mips-ido-c"
    ) -> str:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            asm = path / "test.s"
            asm.write_text(f"glabel test\n{body}\njr $ra\nnop\n")
            flags = ["--target", target, "--valid-syntax", "--no-cache"]
            if context:
                ctx = path / "context.c"
                ctx.write_text(context)
                flags.extend(["--context", str(ctx)])
            return decompile_and_capture_output(parse_flags([*flags, str(asm)]))

    def test_reused_hi_keeps_each_store_destination(self) -> None:
        body = """lui $t0, %hi(first)
sw $zero, %lo(first)($t0)
sw $zero, %lo(second)($t0)
sw $zero, %lo(third)($t0)"""
        for target in ("mips-ido-c", "mips-gcc-c"):
            for context in ("", "extern int first, second, third; void test(void);"):
                with self.subTest(target=target, context=context):
                    output = self.decompile(body, context=context, target=target)
                    for name in ("first", "second", "third"):
                        self.assertEqual(1, output.count(f"{name} = 0;"))

    def test_load_uses_its_own_low_symbol(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(first)\nlw $v0, %lo(second)($t0)",
            context="extern int first, second; int test(void);",
        )
        self.assertIn("return second;", output)
        self.assertNotIn("return first;", output)

    def test_low_addend_is_not_replaced_by_high_addend(self) -> None:
        context = "extern int values[4]; void test(void);"
        for hi, lo, index in ((0, 4, 1), (4, 8, 2), (8, 4, 1)):
            with self.subTest(hi=hi, lo=lo):
                output = self.decompile(
                    f"lui $t0, %hi(values + {hi})\n"
                    f"sw $zero, %lo(values + {lo})($t0)",
                    context=context,
                )
                self.assertIn(f"values[{index}] = 0;", output)

    def test_modified_base_is_not_retargeted(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(first)\naddiu $t0, $t0, 8\n" "lw $v0, %lo(second)($t0)",
            context="extern int first[8], second; int test(void);",
        )
        self.assertIn("return first[2];", output)
        self.assertNotIn("return second;", output)

    def test_completed_address_is_not_an_upper_half(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(first)\naddiu $t0, $t0, %lo(first)\n"
            "lw $v0, %lo(second)($t0)",
            context="extern int first, second; int test(void);",
        )
        self.assertIn("return first;", output)
        self.assertNotIn("return second;", output)

    def test_matching_hi_lo_pair_is_unchanged(self) -> None:
        output = self.decompile(
            "lui $t0, %hi(values + 4)\nlw $v0, %lo(values + 4)($t0)",
            context="extern int values[4]; int test(void);",
        )
        self.assertIn("return values[1];", output)
