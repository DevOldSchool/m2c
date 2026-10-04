void test(void *arg0, s32 arg1) {
    M2C_FIELD(arg0, u8 *, 4) = 0xFFU;
    M2C_FIELD(arg0, u16 *, 6) = 0xFFFFU;
    M2C_FIELD(arg0, s8 *, 8) = (s8) arg1;
}
