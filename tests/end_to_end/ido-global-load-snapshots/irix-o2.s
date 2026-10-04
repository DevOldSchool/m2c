# Reconstructed from orig.o compiled by IDO 5.3 with:
# cc -c -32 -G 0 -signed -non_shared -O2 -mips2 orig.c
# Symbolic operands preserve the original object's HI16/LO16 relocations.
.set noat
.set noreorder

glabel test
    lui $v0, %hi(byte_count)
    lbu $v0, %lo(byte_count)($v0)
    slti $at, $v0, 8
    beqz $at, .Lbyte_end
     addiu $t6, $v0, 1
    sb $v0, 0($a0)
    sb $t6, 1($a0)
.Lbyte_end:
    jr $ra
     nop

glabel test_half
    lui $v0, %hi(half_count)
    lhu $v0, %lo(half_count)($v0)
    slti $at, $v0, 8
    beqz $at, .Lhalf_end
     addiu $t6, $v0, 1
    sh $v0, 0($a0)
    sh $t6, 2($a0)
.Lhalf_end:
    jr $ra
     nop
