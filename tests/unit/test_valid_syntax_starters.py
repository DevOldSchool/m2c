from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestValidSyntaxStarters(unittest.TestCase):
    def decompile(
        self,
        assembly: str,
        context: str = "typedef int s32;\ntypedef float f32;\n",
        flags: Optional[List[str]] = None,
    ) -> str:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "test.s"
            source.write_text(".set noreorder\nglabel test\n" + assembly + "\n")
            ctx = root / "context.c"
            ctx.write_text(context)
            args = [
                "--target",
                "mips-ido-c",
                "--valid-syntax",
                "--no-cache",
                "--context",
                str(ctx),
                str(source),
            ]
            return decompile_and_capture_output(parse_flags(args + (flags or [])))

    two_calls = """
        addiu $sp, $sp, -0x18
        sw $ra, 0x14($sp)
        jal foo
        addiu $a0, $zero, 1
        jal foo
        {second_delay}
        lw $ra, 0x14($sp)
        jr $ra
        addiu $sp, $sp, 0x18
        """

    def test_unprototyped_redeclaration_keeps_earlier_prototype(self) -> None:
        output = self.decompile(
            self.two_calls.format(second_delay="nop"),
            context="typedef int s32;\ns32 foo(void);\ns32 foo();\n",
        )
        self.assertIn("foo();\n    foo();", output)
        self.assertNotIn("foo(1)", output)

    def test_second_half_of_f64_is_valid_syntax(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x18
            sw $ra, 0x14($sp)
            jal foo
            nop
            lw $ra, 0x14($sp)
            jr $ra
            mov.s $f0, $f1
            """,
            context="typedef float f32;\nf32 foo(void);\n",
        )
        self.assertIn("M2C_ERROR(/* second half of f64 */)", output)

    def test_forward_declared_struct_pointer_offsets_count_bytes(self) -> None:
        output = self.decompile(
            """
            lbu $t0, 0x0($a1)
            sll $t0, $t0, 2
            addu $t1, $a0, $t0
            jr $ra
            lw $v0, 0x20($t1)
            """,
            context="typedef unsigned char u8;\nstruct S;\n"
            "void *test(struct S *arg0, u8 *arg1);\n",
        )
        self.assertIn("((u8 *) arg0 + (*arg1 * 4))", output)

    def test_pointer_difference_between_types_counts_bytes(self) -> None:
        output = self.decompile(
            """
            lui $t0, %hi(table)
            addiu $t0, $t0, %lo(table)
            jr $ra
            subu $v0, $a0, $t0
            """,
            context="typedef int s32;\ntypedef unsigned char u8;\n"
            "extern s32 table;\ns32 test(u8 *arg0);\n",
        )
        self.assertIn("(u8 *) arg0 - (u8 *) &table", output)

    def test_void_typed_address_only_global_is_byte_storage(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x20
            sw $ra, 0x14($sp)
            lui $t0, %hi(blob)
            addiu $t0, $t0, %lo(blob)
            sw $t0, 0x18($sp)
            jal use
            addiu $a0, $sp, 0x18
            lw $ra, 0x14($sp)
            jr $ra
            addiu $sp, $sp, 0x20
            """,
            context="void use(void **);\n",
        )
        self.assertNotIn("extern void blob;", output)
        self.assertIn("extern u8 blob[];", output)
