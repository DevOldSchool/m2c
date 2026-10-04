void test(struct Object *object) {
    u32 temp_t6;

    temp_t6 = object->flags;
    object->state = 0x20;
    object->flags = temp_t6 | 1;
}
