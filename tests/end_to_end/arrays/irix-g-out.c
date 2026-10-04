extern ? D_400130;
extern ? D_410140;

s32 test(s32 arg0, s32 arg1, s32 arg2) {
    s32 *temp_t3;
    void *temp_t0;

    sp->unk0 = (s32) D_400130.unk0;
    sp->unk4 = (u16) D_400130.unk4;
    temp_t3 = (s32 *) (arg1 + (arg0 * 4));
    temp_t0 = (void *) (arg2 + (arg0 * 4));
    return temp_t0->unk4 + ((*(sp + arg0) * *temp_t3) + *(&D_410140 + (arg0 * 2)));
}
