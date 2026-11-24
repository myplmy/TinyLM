// Included after the established AVX2 lookup code and its digit table.
extern "C" bool p109_g270_expand_row(const uint8_t* codes, const float* scales, int token, float* out) {
    constexpr int PackedWidth = 52;
    const uint8_t* row = codes + token * PackedWidth;
    if (!valid_bytes(row, PackedWidth)) return false;
    const __m256 scale = _mm256_set1_ps(scales[token]);
    for (int chunk = 0; chunk < 50; ++chunk) {
        const __m256 digits = _mm256_load_ps(Digits[row[chunk]].data());
        _mm256_storeu_ps(out + chunk * 5, _mm256_mul_ps(digits, scale));
    }
    const __m256i last_five = _mm256_setr_epi32(-1, -1, -1, -1, -1, 0, 0, 0);
    const __m256i last_one = _mm256_setr_epi32(-1, 0, 0, 0, 0, 0, 0, 0);
    _mm256_maskstore_ps(out + 250, last_five, _mm256_mul_ps(_mm256_load_ps(Digits[row[50]].data()), scale));
    _mm256_maskstore_ps(out + 255, last_one, _mm256_mul_ps(_mm256_load_ps(Digits[row[51]].data()), scale));
    return true;
}
