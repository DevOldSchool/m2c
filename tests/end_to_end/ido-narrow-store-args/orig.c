struct Fields {
    signed char byte;
    signed short half;
};

void test(struct Fields *fields, int byte, int half) {
    fields->byte = byte;
    fields->half = half;
}
