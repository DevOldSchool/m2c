from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional
import unittest

from m2c.main import parse_flags
from run_tests import decompile_and_capture_output


class TestStarterDeclarations(unittest.TestCase):
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

    def test_guessed_callee_with_differing_arities_is_unprototyped(self) -> None:
        output = self.decompile(self.two_calls.format(second_delay="nop"))
        self.assertIn("foo();", output)
        self.assertIn("unprototyped: call arities differ", output)
        self.assertIn("foo(1);", output)

    def test_guessed_callee_with_consistent_arity_keeps_prototype(self) -> None:
        output = self.decompile(
            self.two_calls.format(second_delay="addiu $a0, $zero, 2")
        )
        self.assertIn("M2C_UNK foo(M2C_UNK);", output)
        self.assertNotIn("unprototyped", output)

    def test_context_callee_with_differing_arities_keeps_its_declaration(
        self,
    ) -> None:
        output = self.decompile(
            self.two_calls.format(second_delay="nop"),
            context="typedef int s32;\nvoid foo();\n",
        )
        self.assertNotIn("unprototyped", output)

    later_global = """
        lui $v0, %hi(later)
        jr $ra
        lw $v0, %lo(later)($v0)
        """

    def test_global_declared_after_placeholder_is_redeclared(self) -> None:
        output = self.decompile(
            self.later_global,
            context='typedef int s32;\n#pragma GLOBAL_ASM("asm/nonmatchings/x/test.s")\n'
            "extern s32 later;\n",
        )
        self.assertIn(
            "extern s32 later;                                   "
            "/* declared after this function in context */",
            output,
        )

    def test_global_declared_before_placeholder_is_not_repeated(self) -> None:
        output = self.decompile(
            self.later_global,
            context="typedef int s32;\nextern s32 later;\n"
            '#pragma GLOBAL_ASM("asm/nonmatchings/x/test.s")\n',
        )
        self.assertNotIn("extern", output)

    def test_context_without_placeholder_is_unchanged(self) -> None:
        output = self.decompile(
            self.later_global,
            context='typedef int s32;\n#pragma GLOBAL_ASM("asm/other.s")\n'
            "extern s32 later;\n",
        )
        self.assertNotIn("extern", output)

    def test_type_declared_after_placeholder_is_not_used(self) -> None:
        output = self.decompile(
            self.later_global,
            context='#pragma GLOBAL_ASM("asm/test.s")\n'
            "typedef struct { int x; } Later;\nextern Later later;\n",
        )
        self.assertIn("later.x", output)
        self.assertNotIn("extern", output)

    def test_function_declared_after_placeholder_is_redeclared(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x18
            sw $ra, 0x14($sp)
            jal foo
            nop
            lw $ra, 0x14($sp)
            jr $ra
            addiu $sp, $sp, 0x18
            """,
            context='typedef unsigned int u32;\n#pragma GLOBAL_ASM("asm/test.s")\n'
            "u32 foo(void);\n",
        )
        self.assertIn(
            "u32 foo(void);                                      "
            "/* extern; declared after this function in context */",
            output,
        )

    def test_redeclaration_keeps_context_qualifiers(self) -> None:
        output = self.decompile(
            """
            addiu $sp, $sp, -0x18
            sw $ra, 0x14($sp)
            jal copy
            nop
            lw $ra, 0x14($sp)
            jr $ra
            addiu $sp, $sp, 0x18
            """,
            context='typedef unsigned int u32;\n#pragma GLOBAL_ASM("asm/test.s")\n'
            "void *copy(void *, const void *, u32);\n",
        )
        self.assertIn("void *copy(void *, const void *, u32);", output)
