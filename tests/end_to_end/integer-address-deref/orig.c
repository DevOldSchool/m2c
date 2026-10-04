void test(int address, int *index, unsigned char value) {
    if (*index + 1 < 40) {
        *(unsigned char *)(address + *index) = value;
        *index += 1;
    }
}
