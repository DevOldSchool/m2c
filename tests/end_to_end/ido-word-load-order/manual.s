# Keep this word load before a narrow store to the same object.
glabel test
lw $t6, 0($a0)
li $t8, 32
sh $t8, 6($a0)
ori $t7, $t6, 1
sw $t7, 0($a0)
jr $ra
nop
