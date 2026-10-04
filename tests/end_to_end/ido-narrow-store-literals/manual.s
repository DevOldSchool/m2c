# Unsigned byte and halfword constants, followed by a word-sized argument.
# These register values must not be shortened to negative store literals.
.set noat
.set noreorder

glabel test
    ori $t6, $zero, 255
    ori $t7, $zero, 65535
    sb $t6, 4($a0)
    sh $t7, 6($a0)
    sb $a1, 8($a0)
    jr $ra
     nop
