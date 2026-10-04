# A shared symbolic upper half with distinct low relocations.
glabel test
lui $t0, %hi(first)
sw $zero, %lo(first)($t0)
sw $zero, %lo(second)($t0)
sw $zero, %lo(values + 4)($t0)
jr $ra
nop

glabel read_second
lui $t0, %hi(first)
jr $ra
lw $v0, %lo(second)($t0)
