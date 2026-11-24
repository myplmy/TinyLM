#include <iostream>

#define main original_g4_cli
#include "p109_g4_compact_cpu.cpp"
#undef main

#include "p109_g4_grouped_int8_cache.hpp"

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    const int key_bits = std::stoi(argv[1]);
    const int value_bits = std::stoi(argv[2]);
    const int old_rows = std::stoi(argv[3]);
    constexpr int Capacity = 2048;
#ifdef P077_ARCHIVE_REFERENCE
    if (key_bits != 4 || value_bits != 4 || old_rows != 1024) return 2;
    GroupedInt8Cache cache(Capacity, 1024, 3);
#else
    GroupedInt8Cache cache(Capacity, old_rows, key_bits, value_bits);
#endif
    std::vector<float> input_key(Capacity * Kv), input_value(Capacity * Kv);
    std::vector<float> output_key(Capacity * Kv), output_value(Capacity * Kv);
    const auto input_bytes = input_key.size() * sizeof(float);
    if (!std::cin.read(reinterpret_cast<char*>(input_key.data()), input_bytes) ||
        !std::cin.read(reinterpret_cast<char*>(input_value.data()), input_bytes)) return 2;

    for (int slot : {0, Slots - 1}) {
        int past = 0;
        for (int end : {31, 32, 1009, 1024, 1887, 1901, 1919, 1920, 1921, 2017, Capacity}) {
            const int offset = past * Kv;
            cache.append_recent(slot, past, end - past, input_key.data() + offset, input_value.data() + offset);
            past = end;
            cache.restore(slot, past, output_key.data(), output_value.data());
            const int first = std::max(0, past - 69);
            std::array<float, 69 * Kv> range_key{}, range_value{};
            cache.restore_block(slot, past, first, past - first, range_key.data(), range_value.data());
            const auto check_bytes = (past - first) * Kv * sizeof(float);
            if (std::memcmp(output_key.data() + first * Kv, range_key.data(), check_bytes) ||
                std::memcmp(output_value.data() + first * Kv, range_value.data(), check_bytes)) return 3;
            for (int head = 0; head < Kv / Head; ++head) {
                cache.restore_head_block(slot, past, first, past - first, head, range_key.data(), range_value.data());
                for (int i = 0; i < past - first; ++i) {
                    const int column = head * Head;
                    if (std::memcmp(output_key.data() + (first + i) * Kv + column,
                                    range_key.data() + i * Kv + column, Head * sizeof(float)) ||
                        std::memcmp(output_value.data() + (first + i) * Kv + column,
                                    range_value.data() + i * Kv + column, Head * sizeof(float))) return 4;
                }
            }
        }
        if (slot == 0) {
            // Reverse every value before filling the final slot to catch offset aliasing.
            for (auto& value : input_key) value = -value;
            for (auto& value : input_value) value = -value;
        }
    }

    const uint64_t stored_bytes = cache.bytes();
    std::cout.write(reinterpret_cast<const char*>(&stored_bytes), sizeof(stored_bytes));
    for (int slot : {0, Slots - 1}) {
        cache.restore(slot, Capacity, output_key.data(), output_value.data());
        std::cout.write(reinterpret_cast<const char*>(output_key.data()), input_bytes);
        std::cout.write(reinterpret_cast<const char*>(output_value.data()), input_bytes);
    }
}
