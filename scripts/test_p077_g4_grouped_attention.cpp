#include <iostream>
#include <memory>

#define main original_g4_cli
#include "p109_g4_compact_cpu.cpp"
#undef main

#define GroupedInt8Cache FrozenGroupedCache
#include "p109_g4_grouped_int8_cache_before.hpp"
#undef GroupedInt8Cache
#include "p109_g4_grouped_int8_cache.hpp"
#include "p077_g4_grouped_attention.hpp"

void full_attention(const float* query, const float* key, const float* value, int visible, float* output) {
    std::vector<float> scores(visible);
    for (int head = 0; head < Heads; ++head) {
        const int offset = (head / 4) * Head;
        float largest = -INFINITY;
        for (int t = 0; t < visible; ++t) {
            scores[t] = dot(query + head * Head, key + t * Kv + offset, Head) * 0.125F;
            largest = std::max(largest, scores[t]);
        }
        float denom = 0.F;
        for (int t = 0; t < visible; ++t) {
            scores[t] = std::exp(scores[t] - largest);
            denom += scores[t];
        }
        weighted_values(output + head * Head, value + offset, scores.data(), visible, denom);
    }
}

int main() {
    constexpr int Capacity = 2048;
    std::vector<float> raw_key(Capacity * Kv), raw_value(Capacity * Kv);
    std::vector<float> full_key(Capacity * Kv), full_value(Capacity * Kv);
    auto reference = std::make_unique<FrozenGroupedCache>(Capacity);
    auto cache = std::make_unique<GroupedInt8Cache>(Capacity);
    GroupedBlockAttention blocked(Capacity);
    std::array<float, D> query, expected, actual;
    int comparisons = 0;
    for (int slot : {0, Slots - 1}) {
        for (size_t i = 0; i < raw_key.size(); ++i) {
            raw_key[i] = static_cast<float>(static_cast<int>((i * 39 + slot * 7) % 233) - 116) / 128.F;
            raw_value[i] = static_cast<float>(static_cast<int>((i * 69 + slot * 13) % 509) - 254) / 256.F;
        }
        int past = 0;
        for (int length : {0, 1, 31, 32, 33, 63, 64, 1007, 1024, 1985, 2047, 2048}) {
            reference->append(slot, past, length - past, raw_key.data(), raw_value.data());
            cache->append_recent(slot, past, length - past, raw_key.data() + past * Kv, raw_value.data() + past * Kv);
            past = length;
            reference->restore(slot, past, full_key.data(), full_value.data());
            const float* recent_key = raw_key.data() + past * Kv;
            const float* recent_value = raw_value.data() + past * Kv;
            for (int visible_new : {0, 1, 4, 17}) {
                if (past + visible_new == 0 || past + visible_new > Capacity) continue;
                std::copy_n(recent_key, visible_new * Kv, full_key.data() + past * Kv);
                std::copy_n(recent_value, visible_new * Kv, full_value.data() + past * Kv);
                for (float scale : {0.125F, 1.F, 32.F}) {
                    for (int j = 0; j < D; ++j)
                        query[j] = static_cast<float>(((j * 17 + past) % 97) - 48) * scale / 64.F;
                    full_attention(query.data(), full_key.data(), full_value.data(), past + visible_new, expected.data());
                    blocked.compute(*cache, slot, past, query.data(), recent_key, recent_value, visible_new, actual.data());
                    if (std::memcmp(expected.data(), actual.data(), sizeof(actual))) {
                        throw std::runtime_error("block attention differs from full attention");
                    }
                    ++comparisons;
                }
            }
        }
    }
    std::cout << "{\"comparisons\":" << comparisons << ",\"attention_values\":" << comparisons * D
              << ",\"block_workspace_bytes\":" << blocked.workspace_bytes() << "}" << std::endl;
}
