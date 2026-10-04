extern ? D_400120;
extern ? D_410130;

s32 test(s32 arg0, s32 arg1, s32 arg2) {
    s32 *temp_t2;
    s32 temp_v1;
    void *temp_t5;

    sp->unk0 = (s32) D_400120.unk0;
    temp_v1 = arg0 * 4;
    temp_t2 = (s32 *) (arg1 + temp_v1);
    sp->unk4 = (u16) D_400120.unk4;
    temp_t5 = (void *) (arg2 + temp_v1);
    return temp_t5->unk4 + (*(sp + arg0) * *temp_t2) + *(&D_410130 + (arg0 * 2));
}
