from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestStackLocals(unittest.TestCase):
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

    def test_slot_only_read_after_neighbour_address_escapes_is_declared(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x28
            sw $ra, 0x14($sp)
            jal fill
            addiu $a0, $sp, 0x18
            lwc1 $f0, 0x1C($sp)
            lw $ra, 0x14($sp)
            jr $ra
            addiu $sp, $sp, 0x28
            """,
            context="typedef float f32;\nvoid fill(f32 *);\n",
        )
        self.assertIn("f32 sp1C;", output)
        self.assertIn("f32 sp18;", output)
        self.assertIn("return sp1C;", output)

    def test_open_stack_array_is_sized_to_its_slot(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x30
            addiu $t0, $sp, 0x10
            sll $t1, $a0, 2
            addu $t2, $t0, $t1
            sw $zero, 0x0($t2)
            sw $a1, 0x20($sp)
            jr $ra
            addiu $sp, $sp, 0x30
            """
        )
        self.assertIn("sp10[4];", output)
        self.assertNotIn("sp10[];", output)

    def test_open_stack_array_extends_to_frame_top(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x30
            addiu $t0, $sp, 0x10
            sll $t1, $a0, 2
            addu $t2, $t0, $t1
            sw $zero, 0x0($t2)
            jr $ra
            addiu $sp, $sp, 0x30
            """
        )
        self.assertIn("sp10[8];", output)

    def test_byte_inside_halfword_stack_slot_reads_through_slot(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x18
            sh $a0, 0x10($sp)
            lbu $v0, 0x11($sp)
            jr $ra
            addiu $sp, $sp, 0x18
            """
        )
        self.assertIn("M2C_FIELD(&sp10, u8 *, 1)", output)
        self.assertNotIn("unksp", output)
