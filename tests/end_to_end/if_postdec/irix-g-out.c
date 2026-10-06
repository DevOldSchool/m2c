extern s32 D_4100F0;

s32 test(void) {
    s32 temp_a0;
    s32 temp_cond;

    temp_a0 = D_4100F0 < 1;
    temp_cond = temp_a0 == 0;
    D_4100F0 -= 1;
    if (!temp_cond) {
        return 4;
    }
    return 6;
}
