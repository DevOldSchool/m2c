s32 func_00400174(?, ?, s32, s32, s32);             /* static */
? func_0040019C(s32, s32, s32);                     /* static */
extern s32 D_4101C0;
extern ? D_4101C8;

s32 test(s32 arg0, s32 arg1) {
    s32 sp2C;
    s32 sp28;
    s32 sp24;
    void *temp_t5;
    void *temp_t9;

    temp_t9 = (void *) (D_4101C0 + (arg0 * 8));
    sp2C = temp_t9->unk4 + 1;
    temp_t5 = (void *) (D_4101C0 + (arg0 * 8));
    sp24 = temp_t5->unk8;
    sp28 = func_00400174(1, 2, sp2C, arg1, arg0);
    if (sp28 == 0) {
        return 0;
    }
    func_0040019C(sp24, sp28, sp2C);
    *(&D_4101C8 + arg0) = 5;
    return sp28;
}
