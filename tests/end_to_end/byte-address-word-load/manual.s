.set noreorder
glabel test
lw $t0, 4($a0)
addiu $t1, $a0, 0x100
sll $t0, $t0, 2
addu $t1, $t1, $t0
jr $ra
lw $v0, 0($t1)
