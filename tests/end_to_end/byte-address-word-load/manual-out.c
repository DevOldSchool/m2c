s32 test(void *arg0) {
    return M2C_FIELD(((u8 *) ((u8 *) arg0 + 0x100) + (M2C_FIELD(arg0, s32 *, 4) * 4)), s32 *, 0);
}
