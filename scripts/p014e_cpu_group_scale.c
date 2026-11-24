/* Keep the existing path and digit table in the same numerical experiment. */
#define p014e_cpu_linear p014e_reference_linear
#include "p014e_direct_cpu.c"
#undef p014e_cpu_linear

int p014e_group_scale_linear(const float *x, const uint8_t *codes, const float *scales,
                            float *y, int64_t m, int64_t n, int64_t k, int64_t g,
                            int64_t begin, int64_t end) {
    if (!x || !codes || !scales || !y || !valid_shape(m,n,k,g) ||
        begin < 0 || end < begin || end > m*n) return 1;
    const int64_t groups = k/g;
    const int64_t bytes = (g+4)/5;
    for (int64_t flat = begin; flat < end; ++flat) {
        const float *input = x + (flat/n)*k;
        const int64_t row = flat%n;
        double sum = 0.0;
        for (int64_t group = 0; group < groups; ++group) {
            const uint8_t *packed = codes + (row*groups + group)*bytes;
            const float *values = input + group*g;
            double partial = 0.0;
            for (int64_t offset = 0; offset < g; offset += 5) {
                const uint8_t byte = packed[offset/5];
                if (byte > 242) return 4;
                const int8_t *trits = DIGITS[byte];
                for (int j = 0; j < 5 && offset+j < g; ++j) {
                    partial += (double)values[offset+j] * (double)trits[j];
                }
            }
            sum += partial * (double)scales[row*groups + group];
        }
        y[flat] = (float)sum;
    }
    return 0;
}
