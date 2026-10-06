# A forwarded a0 precedes explicitly prepared register and stack arguments.
.set noreorder
glabel test
addiu $sp, $sp, -0x30
sw $ra, 0x2c($sp)
sw $a1, 0x34($sp)
sw $a2, 0x38($sp)
sw $a3, 0x3c($sp)
li $a1, 2
li $a2, 3
li $a3, 4
sw $zero, 0x10($sp)
sw $zero, 0x14($sp)
sw $zero, 0x18($sp)
li $t0, 8
sw $t0, 0x1c($sp)
li $t1, 9
jal callee
sw $t1, 0x20($sp)
lw $ra, 0x2c($sp)
addiu $sp, $sp, 0x30
jr $ra
nop
