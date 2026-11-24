// Included by the compact G4 diagnostic after its FP16 conversion helpers.
class GroupedInt8Cache {
public:
    static constexpr int GroupTokens = 32;

    explicit GroupedInt8Cache(int capacity, int prefix_int4_rows = 0, int int4_planes = 0)
        : GroupedInt8Cache(capacity, prefix_int4_rows, (int4_planes & 1) ? 4 : 8,
                           (int4_planes & 2) ? 4 : 8) {}

    GroupedInt8Cache(int capacity, int prefix_rows, int key_bits, int value_bits)
        : capacity_(capacity), packed_rows_(capacity / GroupTokens * GroupTokens),
          tail_rows_(std::min(capacity, GroupTokens - 1)),
          prefix_rows_(std::clamp(prefix_rows, 0, packed_rows_) / GroupTokens * GroupTokens),
          key_bits_(checked_bits(key_bits)), value_bits_(checked_bits(value_bits)),
          key_codes_(Slots * slot_bytes(key_bits_)), value_codes_(Slots * slot_bytes(value_bits_)),
          key_scales_(Slots * (packed_rows_ / GroupTokens) * Kv), value_scales_(Slots * packed_rows_ * KvHeads),
          key_minima_(key_bits_ == 2 ? Slots * (prefix_rows_ / GroupTokens) * Kv : 0),
          value_minima_(value_bits_ == 2 ? Slots * prefix_rows_ * KvHeads : 0),
          tail_keys_(Slots * tail_rows_ * Kv), tail_values_(Slots * tail_rows_ * Kv) {}

    size_t bytes() const {
        return key_codes_.capacity() + value_codes_.capacity() + sizeof(uint16_t) *
               (key_scales_.capacity() + value_scales_.capacity() + key_minima_.capacity() + value_minima_.capacity() +
                tail_keys_.capacity() + tail_values_.capacity());
    }

    void restore(int slot, int past, float* keys, float* values) const {
        restore_rows<Kv>(slot, past, 0, past, 0, keys, values);
    }

    void restore_block(int slot, int past, int first, int count, float* keys, float* values) const {
        check_restore_range(slot, past, first, count);
        restore_rows<Kv>(slot, past, first, count, 0, keys, values);
    }

    // Retain the native Kv-wide row stride and restore only the selected head's columns.
    void restore_head_block(int slot, int past, int first, int count, int kv_head,
                            float* keys, float* values) const {
        check_restore_range(slot, past, first, count);
        if (kv_head < 0 || kv_head >= KvHeads) throw std::out_of_range("grouped KV head");
        restore_rows<Head>(slot, past, first, count, kv_head * Head, keys, values);
    }

    void append(int slot, int past, int count, const float* keys, const float* values) {
        const int end = past + count;
        const int complete = end / GroupTokens * GroupTokens;
        for (int start = past / GroupTokens * GroupTokens; start < complete; start += GroupTokens) {
            store_group(slot * packed_rows_ + start, keys + start * Kv, values + start * Kv);
        }
        const int residual_start = std::max(past, complete);
        if (const int remaining = end - residual_start) {
            const int offset = (slot * tail_rows_ + residual_start - complete) * Kv;
            store_half(tail_keys_.data() + offset, keys + residual_start * Kv, remaining * Kv);
            store_half(tail_values_.data() + offset, values + residual_start * Kv, remaining * Kv);
        }
    }

    void append_recent(int slot, int past, int count, const float* keys, const float* values) {
        if (slot < 0 || slot >= Slots || past < 0 || past > capacity_ || count < 0 || count > capacity_ - past) {
            throw std::out_of_range("grouped KV append range");
        }
        if (count == 0) return;
        const int tail = slot * tail_rows_ * Kv;
        int consumed = 0;
        if (const int prefix = past % GroupTokens) {
            const int fill = GroupTokens - prefix;
            if (count < fill) {
                store_half(tail_keys_.data() + tail + prefix * Kv, keys, count * Kv);
                store_half(tail_values_.data() + tail + prefix * Kv, values, count * Kv);
                return;
            }
            std::copy_n(tail_keys_.data() + tail, prefix * Kv, work_keys_.data());
            std::copy_n(tail_values_.data() + tail, prefix * Kv, work_values_.data());
            store_half(work_keys_.data() + prefix * Kv, keys, fill * Kv);
            store_half(work_values_.data() + prefix * Kv, values, fill * Kv);
            encode_group(slot * packed_rows_ + past - prefix);
            consumed = fill;
        }
        for (; count - consumed >= GroupTokens; consumed += GroupTokens) {
            store_group(slot * packed_rows_ + past + consumed, keys + consumed * Kv, values + consumed * Kv);
        }
        if (const int remaining = count - consumed) {
            store_half(tail_keys_.data() + tail, keys + consumed * Kv, remaining * Kv);
            store_half(tail_values_.data() + tail, values + consumed * Kv, remaining * Kv);
        }
    }

private:
    static constexpr int KvHeads = Kv / Head;
    static constexpr float MinimumScale = 0x1p-14F;

    void check_restore_range(int slot, int past, int first, int count) const {
        if (slot < 0 || slot >= Slots || past < 0 || past > capacity_ ||
            first < 0 || first > past || count < 0 || count > past - first) {
            throw std::out_of_range("grouped KV restore range");
        }
    }

    struct CodeGroup {
        size_t offset;
        int bits;
        int prefix_row;
    };

    static int checked_bits(int bits) {
        if (bits != 2 && bits != 3 && bits != 4 && bits != 8) throw std::invalid_argument("grouped KV precision");
        return bits;
    }

    size_t slot_bytes(int bits) const {
        return size_t(prefix_rows_) * Kv * bits / 8 + size_t(packed_rows_ - prefix_rows_) * Kv;
    }

    CodeGroup code_group(int row, int bits) const {
        if (bits == 8 || !prefix_rows_) return {size_t(row) * Kv, 8, 0};
        const int token = row % packed_rows_;
        const int slot = row / packed_rows_;
        const size_t base = slot * slot_bytes(bits);
        if (token < prefix_rows_) return {base + size_t(token) * Kv * bits / 8, bits, slot * prefix_rows_ + token};
        return {base + size_t(prefix_rows_) * Kv * bits / 8 + size_t(token - prefix_rows_) * Kv, 8, 0};
    }

    template<int Columns>
    void restore_rows(int slot, int past, int first, int count, int column_begin,
                      float* keys, float* values) const {
        if (count == 0) return;
        const int complete = past / GroupTokens * GroupTokens;
        const int end = first + count;
        const int packed_end = std::min(end, complete);
        for (int group = first / GroupTokens * GroupTokens; group < packed_end; group += GroupTokens) {
            const int row = slot * packed_rows_ + group;
            const auto key_codes = code_group(row, key_bits_);
            const auto value_codes = code_group(row, value_bits_);
            const int begin = std::max(first, group) - group;
            const int limit = std::min(packed_end - group, GroupTokens);
            const uint16_t* scales = key_scales_.data() + (row / GroupTokens) * Kv;
            for (int column = column_begin; column < column_begin + Columns; column += 8) {
                const __m256 key_scale = keys ? _mm256_cvtph_ps(_mm_loadu_si128(
                    reinterpret_cast<const __m128i*>(scales + column))) : _mm256_setzero_ps();
                const __m256 key_minimum = keys && key_codes.bits == 2 ? _mm256_cvtph_ps(_mm_loadu_si128(
                    reinterpret_cast<const __m128i*>(key_minima_.data() + key_codes.prefix_row / GroupTokens * Kv + column)))
                    : _mm256_setzero_ps();
                for (int t = begin; t < limit; ++t) {
                    const int offset = t * Kv + column;
                    const int output = (group + t - first) * Kv + column;
                    if (keys) restore8(keys + output, key_codes_.data(), key_codes, offset, key_scale, key_minimum);
                    if (values) {
                        const uint16_t scale = value_scales_[(row + t) * KvHeads + column / Head];
                        const float minimum = value_codes.bits == 2 ? _cvtsh_ss(
                            value_minima_[(value_codes.prefix_row + t) * KvHeads + column / Head]) : 0.F;
                        restore8(values + output, value_codes_.data(), value_codes, offset,
                                 _mm256_set1_ps(_cvtsh_ss(scale)), _mm256_set1_ps(minimum));
                    }
                }
            }
        }
        const int start_tail = std::max(first, complete);
        if (end > start_tail) {
            const int offset = (slot * tail_rows_ + start_tail - complete) * Kv;
            const int output = (start_tail - first) * Kv;
            if constexpr (Columns == Kv) {
                const int elements = (end - start_tail) * Kv;
                if (keys) load_half(keys + output, tail_keys_.data() + offset, elements);
                if (values) load_half(values + output, tail_values_.data() + offset, elements);
            } else {
                for (int t = 0; t < end - start_tail; ++t) {
                    const int column = t * Kv + column_begin;
                    if (keys) load_half(keys + output + column, tail_keys_.data() + offset + column, Columns);
                    if (values) load_half(values + output + column, tail_values_.data() + offset + column, Columns);
                }
            }
        }
    }

    static void restore8(float* target, const uint8_t* codes, CodeGroup group, int offset, __m256 scale, __m256 minimum) {
        __m256i integers;
        if (group.bits == 4) {
            int32_t word;
            std::memcpy(&word, codes + group.offset + offset / 2, sizeof(word));
            const __m128i raw = _mm_cvtsi32_si128(word);
            const __m128i mask = _mm_set1_epi8(15);
            const __m128i low = _mm_and_si128(raw, mask);
            const __m128i high = _mm_and_si128(_mm_srli_epi16(raw, 4), mask);
            const __m128i sign = _mm_set1_epi8(8);
            integers = _mm256_cvtepi8_epi32(_mm_sub_epi8(_mm_xor_si128(_mm_unpacklo_epi8(low, high), sign), sign));
        } else if (group.bits == 8) {
            integers = _mm256_cvtepi8_epi32(_mm_loadl_epi64(reinterpret_cast<const __m128i*>(codes + group.offset + offset)));
        } else {
            uint32_t word = 0;
            std::memcpy(&word, codes + group.offset + offset * group.bits / 8, group.bits);
            const __m256i positions = _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7);
            const __m256i shifts = _mm256_mullo_epi32(positions, _mm256_set1_epi32(group.bits));
            integers = _mm256_and_si256(_mm256_srlv_epi32(_mm256_set1_epi32(word), shifts),
                                        _mm256_set1_epi32((1 << group.bits) - 1));
            if (group.bits == 3) integers = _mm256_sub_epi32(integers, _mm256_set1_epi32(3));
        }
        __m256 product = _mm256_mul_ps(_mm256_cvtepi32_ps(integers), scale);
        if (group.bits == 2) product = _mm256_add_ps(product, minimum);
        const __m128i half = _mm256_cvtps_ph(product, _MM_FROUND_TO_NEAREST_INT);
        _mm256_storeu_ps(target, _mm256_cvtph_ps(half));
    }

    static void write_low_bits(uint8_t* codes, int position, int bits, unsigned code) {
        const int bit = position * bits;
        const int shift = bit & 7;
        const unsigned mask = ((1u << bits) - 1) << shift;
        const unsigned word = code << shift;
        auto* address = codes + bit / 8;
        address[0] = static_cast<uint8_t>((address[0] & ~mask) | word);
        if (shift + bits > 8) {
            address[1] = static_cast<uint8_t>((address[1] & ~(mask >> 8)) | (word >> 8));
        }
    }

    static void encode_line(const uint16_t* source, uint8_t* codes, CodeGroup group, int offset,
                            uint16_t& scale, uint16_t* minimum, int size, int stride) {
        const bool affine = group.bits == 2;
        const float max_code = affine ? 3.F : float((1 << (group.bits - 1)) - 1);
        float origin = 0.F, width = 0.F;
        if (affine) {
            float lo = _cvtsh_ss(source[0]), hi = lo;
            for (int i = 1; i < size; ++i) {
                const float value = _cvtsh_ss(source[i * stride]);
                lo = std::min(lo, value);
                hi = std::max(hi, value);
            }
            *minimum = _cvtss_sh(lo, _MM_FROUND_TO_NEAREST_INT);
            origin = _cvtsh_ss(*minimum);
            width = hi - origin;
        } else {
            for (int i = 0; i < size; ++i) width = std::max(width, std::fabs(_cvtsh_ss(source[i * stride])));
        }
        scale = _cvtss_sh(std::max(width / max_code, MinimumScale), _MM_FROUND_TO_NEAREST_INT);
        const float divisor = _cvtsh_ss(scale);
        for (int i = 0; i < size; ++i) {
            const float rounded = std::nearbyint((_cvtsh_ss(source[i * stride]) - origin) / divisor);
            const int code = static_cast<int>(std::clamp(rounded, affine ? 0.F : -max_code, max_code));
            const int position = offset + i * stride;
            if (group.bits == 4) {
                const int shift = (position & 1) * 4;
                auto& byte = codes[group.offset + position / 2];
                byte = static_cast<uint8_t>((byte & ~(15u << shift)) | ((unsigned(code) & 15u) << shift));
            } else if (group.bits == 8) {
                codes[group.offset + position] = static_cast<uint8_t>(code);
            } else {
                write_low_bits(codes + group.offset, position, group.bits, unsigned(code + (affine ? 0 : 3)));
            }
        }
    }

    void store_group(int row, const float* keys, const float* values) {
        store_half(work_keys_.data(), keys, GroupTokens * Kv);
        store_half(work_values_.data(), values, GroupTokens * Kv);
        encode_group(row);
    }

    void encode_group(int row) {
        const auto key_codes = code_group(row, key_bits_);
        const auto value_codes = code_group(row, value_bits_);
        for (int column = 0; column < Kv; ++column) {
            uint16_t* minimum = key_codes.bits == 2 ? &key_minima_[key_codes.prefix_row / GroupTokens * Kv + column] : nullptr;
            encode_line(work_keys_.data() + column, key_codes_.data(), key_codes, column,
                        key_scales_[(row / GroupTokens) * Kv + column], minimum, GroupTokens, Kv);
        }
        for (int t = 0; t < GroupTokens; ++t) {
            for (int h = 0; h < KvHeads; ++h) {
                const int offset = t * Kv + h * Head;
                uint16_t* minimum = value_codes.bits == 2 ? &value_minima_[(value_codes.prefix_row + t) * KvHeads + h] : nullptr;
                encode_line(work_values_.data() + offset, value_codes_.data(), value_codes, offset,
                            value_scales_[(row + t) * KvHeads + h], minimum, Head, 1);
            }
        }
    }

    int capacity_, packed_rows_, tail_rows_, prefix_rows_, key_bits_, value_bits_;
    std::vector<uint8_t> key_codes_, value_codes_;
    std::vector<uint16_t> key_scales_, value_scales_, key_minima_, value_minima_, tail_keys_, tail_values_;
    std::array<uint16_t, GroupTokens * Kv> work_keys_{}, work_values_{};
};
