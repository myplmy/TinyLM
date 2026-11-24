// Exact 5-trit expansion for the two input widths of the compact G4 engine.
#include <array>
#include <cstdint>
#include <immintrin.h>

extern "C" int p014e_scalar_lookup(const uint8_t*, const float*, const int64_t*, float*,
                                   int64_t, int64_t, int64_t, int64_t);

namespace {
constexpr int Group = 128, Packed = 26, Patterns = 243;

constexpr auto digit_table() {
    std::array<std::array<float, 8>, Patterns> table{};
    for (int code = 0; code < Patterns; ++code) {
        int remaining = code;
        for (int digit = 0; digit < 5; ++digit) {
            table[code][digit] = static_cast<float>(remaining % 3 - 1);
            remaining /= 3;
        }
    }
    return table;
}

alignas(32) constexpr auto Digits = digit_table();

bool valid_bytes(const uint8_t* codes, int n) {
    const __m256i largest = _mm256_set1_epi8(static_cast<char>(Patterns - 1));
    int i = 0;
    for (; i + 32 <= n; i += 32) {
        const __m256i bytes = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(codes + i));
        const __m256i relation = _mm256_cmpeq_epi8(_mm256_max_epu8(bytes, largest), largest);
        if (static_cast<uint32_t>(_mm256_movemask_epi8(relation)) != UINT32_MAX)
            return false;
    }
    for (; i < n; ++i)
        if (codes[i] >= Patterns) return false;
    return true;
}
}  // namespace

extern "C" int p014e_cpu_lookup(const uint8_t* codes, const float* scales,
                                const int64_t* ids, float* y,
                                int64_t count, int64_t n, int64_t k, int64_t g) {
    if (!codes || !scales || !ids || !y || count != 1 || g != Group ||
        (k != 768 && k != 2048) || n <= 0 || n > (INT64_C(1) << 24) ||
        ids[0] < 0 || ids[0] >= n) {
        return p014e_scalar_lookup(codes, scales, ids, y, count, n, k, g);
    }
    const int groups = static_cast<int>(k / Group);
    const uint8_t* row = codes + ids[0] * groups * Packed;
    if (!valid_bytes(row, groups * Packed))
        return p014e_scalar_lookup(codes, scales, ids, y, count, n, k, g);

    const float* row_scales = scales + ids[0] * groups;
    const __m256i last_three = _mm256_setr_epi32(-1, -1, -1, 0, 0, 0, 0, 0);
    for (int group = 0; group < groups; ++group) {
        const uint8_t* bytes = row + group * Packed;
        float* dst = y + group * Group;
        const __m256 scale = _mm256_set1_ps(row_scales[group]);
        // Extra lanes are overwritten by the next store, entirely inside this group.
        for (int chunk = 0; chunk < Packed - 1; ++chunk) {
            const __m256 trits = _mm256_load_ps(Digits[bytes[chunk]].data());
            _mm256_storeu_ps(dst + chunk * 5, _mm256_mul_ps(trits, scale));
        }
        const __m256 tail = _mm256_load_ps(Digits[bytes[Packed - 1]].data());
        _mm256_maskstore_ps(dst + 125, last_three, _mm256_mul_ps(tail, scale));
    }
    return 0;
}
