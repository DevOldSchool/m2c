void test(u8 *out) {
    s32 temp_v0;

    temp_v0 = byte_count;
    if ((s32) temp_v0 < 8) {
        out->unk0 = temp_v0;
        out->unk1 = (s8) (temp_v0 + 1);
    }
}
