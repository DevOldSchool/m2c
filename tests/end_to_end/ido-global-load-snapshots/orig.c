unsigned char byte_count;
unsigned short half_count;

void test(unsigned char *out) {
    unsigned char snapshot = byte_count;
    if (snapshot < 8) {
        out[0] = snapshot;
        out[1] = snapshot + 1;
    }
}

void test_half(unsigned short *out) {
    unsigned short snapshot = half_count;
    if (snapshot < 8) {
        out[0] = snapshot;
        out[1] = snapshot + 1;
    }
}
