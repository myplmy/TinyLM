#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <iostream>
#include <stdexcept>
#include <vector>

constexpr int Slots = 14, Head = 64, Kv = 3 * Head;
constexpr int Capacity = 2048, Block = 64;

void load_half(float* dst, const uint16_t* src, size_t count) {
    for (size_t i = 0; i < count; i += 8) {
        const auto encoded = _mm_loadu_si128(reinterpret_cast<const __m128i*>(src + i));
        _mm256_storeu_ps(dst + i, _mm256_cvtph_ps(encoded));
    }
}

void store_half(uint16_t* dst, const float* src, size_t count) {
    for (size_t i = 0; i < count; i += 8) {
        const auto half = _mm256_cvtps_ph(_mm256_loadu_ps(src + i), _MM_FROUND_TO_NEAREST_INT);
        _mm_storeu_si128(reinterpret_cast<__m128i*>(dst + i), half);
    }
}

#define GroupedInt8Cache PreviousGroupedInt8Cache
#include "p109_g4_grouped_int8_cache_before.hpp"
#undef GroupedInt8Cache
#include "p109_g4_grouped_int8_cache.hpp"

int main() {
    PreviousGroupedInt8Cache previous(Capacity);
    GroupedInt8Cache current(Capacity);
    std::vector<float> key(Capacity * Kv), value(Capacity * Kv);
    std::vector<float> old_key(key.size()), old_value(value.size());
    std::vector<float> new_key(key.size()), new_value(value.size());
    std::array<float, Block * Kv + 2> block_key{}, block_value{};
    size_t full_reads = 0, block_reads = 0, compared_elements = 0;
    size_t append_calls = 0, appended_rows = 0;
    constexpr float Guard = 21.25F;
    constexpr std::array lengths{0, 1, 31, 32, 33, 63, 64, 65, 511, 1024, 2017, 2047, 2048};
    for (int slot = 0; slot < Slots; ++slot) {
        for (size_t i = 0; i < key.size(); ++i) {
            key[i] = static_cast<float>(static_cast<int>((i * 37 + slot * 19) % 1009) - 504) / 512.F;
            value[i] = static_cast<float>(static_cast<int>((i * 83 + slot * 113) % 1531) - 765) / 1024.F;
        }
        int past = 0;
        for (const int end : lengths) {
            previous.append(slot, past, end - past, key.data(), value.data());
            const std::vector<float> recent_key(key.begin() + past * Kv, key.begin() + end * Kv);
            const std::vector<float> recent_value(value.begin() + past * Kv, value.begin() + end * Kv);
            current.append_recent(slot, past, end - past, recent_key.data(), recent_value.data());
            ++append_calls;
            appended_rows += end - past;
            past = end;
            previous.restore(slot, end, old_key.data(), old_value.data());
            current.restore(slot, end, new_key.data(), new_value.data());
            const auto full_bytes = size_t(end) * Kv * sizeof(float);
            if (std::memcmp(old_key.data(), new_key.data(), full_bytes) ||
                std::memcmp(old_value.data(), new_value.data(), full_bytes)) {
                throw std::runtime_error("full reader regression");
            }
            ++full_reads;
            const std::array starts{0, std::min(1, end), std::min(31, end), std::min(32, end),
                                    end / 2, std::max(0, end - 47), end};
            for (int first : starts) {
                for (int width : {0, 1, 7, 31, 32, 33, Block}) {
                    const int count = std::min(width, end - first);
                    const auto elements = size_t(count) * Kv;
                    const auto bytes = elements * sizeof(float);
                    block_key.front() = block_key[elements + 1] = Guard;
                    block_value.front() = block_value[elements + 1] = Guard;
                    current.restore_block(slot, end, first, count, block_key.data() + 1, block_value.data() + 1);
                    if (block_key.front() != Guard || block_key[elements + 1] != Guard ||
                        block_value.front() != Guard || block_value[elements + 1] != Guard ||
                        std::memcmp(old_key.data() + first * Kv, block_key.data() + 1, bytes) ||
                        std::memcmp(old_value.data() + first * Kv, block_value.data() + 1, bytes)) {
                        throw std::runtime_error("range differs from frozen full reader");
                    }
                    ++block_reads;
                    compared_elements += elements * 2;
                }
            }
        }
    }
    int refusals = 0;
    for (const auto args : {std::array{-1, 0, 0, 0}, std::array{0, Capacity + 1, 0, 0},
                            std::array{0, 10, 9, 2}, std::array{0, 10, 0, -1}}) {
        try {
            current.restore_block(args[0], args[1], args[2], args[3], block_key.data(), block_value.data());
        } catch (const std::out_of_range&) {
            ++refusals;
        }
    }
    if (refusals != 4 || current.bytes() != previous.bytes()) {
        throw std::runtime_error("cache storage or refusal count differs");
    }
    int append_refusals = 0;
    for (const auto args : {std::array{-1, 0, 0}, std::array{0, Capacity + 1, 0},
                            std::array{0, Capacity, 1}, std::array{0, 10, -1}}) {
        try {
            current.append_recent(args[0], args[1], args[2], nullptr, nullptr);
        } catch (const std::out_of_range&) {
            ++append_refusals;
        }
    }
    if (append_refusals != 4) throw std::runtime_error("append refusal count differs");
    const size_t fp16 = Slots * 1024 * Kv * 2 * sizeof(uint16_t);
    const size_t fp16_restore = 1024 * Kv * 2 * sizeof(float);
    const size_t int8_restore = Block * Kv * 2 * sizeof(float);
    const size_t encode_workspace = 32 * Kv * 2 * sizeof(uint16_t);
    std::cout << "{\"full_reads\":" << full_reads << ",\"block_reads\":" << block_reads
              << ",\"compared_elements\":" << compared_elements << ",\"range_refusals\":" << refusals
              << ",\"append_calls\":" << append_calls << ",\"appended_rows\":" << appended_rows
              << ",\"append_refusals\":" << append_refusals
              << ",\"fp16_1024_cache_bytes\":" << fp16 << ",\"fp16_1024_restore_bytes\":" << fp16_restore
              << ",\"group_int8_2048_cache_bytes\":" << current.bytes()
              << ",\"group_int8_64row_restore_bytes\":" << int8_restore
              << ",\"group_int8_encode_workspace_bytes\":" << encode_workspace
              << ",\"group_int8_2048_cache_and_work\":" << current.bytes() + int8_restore + encode_workspace
              << "}" << std::endl;
}
