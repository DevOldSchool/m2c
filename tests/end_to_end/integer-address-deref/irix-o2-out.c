void test(s32 arg0, s32 *arg1, s32 arg2) {
    s32 temp_v0;

    temp_v0 = *arg1;
    if ((temp_v0 + 1) < 0x28) {
        M2C_FIELD((arg0 + temp_v0), s8 *, 0) = arg2 & 0xFF;
        *arg1 += 1;
    }
}
