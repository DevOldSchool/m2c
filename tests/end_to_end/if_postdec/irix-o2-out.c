extern s32 D_4100E0;

s32 test(void) {
    s32 temp_cond;

    temp_cond = D_4100E0 > 0;
    D_4100E0 -= 1;
    if (!temp_cond) {
        return 4;
    }
    return 6;
}
