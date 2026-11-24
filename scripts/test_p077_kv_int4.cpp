#include <iostream>

#define main original_g4_cli
#include "p109_g4_compact_cpu.cpp"
#undef main

#include "p109_g4_grouped_int8_cache.hpp"

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const int planes = std::stoi(argv[1]);
    if (planes < 0 || planes > 3) return 2;
    constexpr int Capacity = 2048;
    constexpr int Slot = Slots - 1;
    GroupedInt8Cache cache(Capacity, 1024, planes);
    std::vector<float> key(Capacity * Kv), value(Capacity * Kv);
    const auto bytes = key.size() * sizeof(float);
    if (!std::cin.read(reinterpret_cast<char*>(key.data()), bytes) ||
        !std::cin.read(reinterpret_cast<char*>(value.data()), bytes)) return 2;
    int past = 0;
    for (int end : {31, 32, 991, 1009, 1028, 1100, Capacity}) {
        cache.append_recent(Slot, past, end - past, key.data() + past * Kv, value.data() + past * Kv);
        past = end;
    }
    cache.restore(Slot, Capacity, key.data(), value.data());
    std::array<float, 64 * Kv> crossing_key, crossing_value;
    cache.restore_block(Slot, Capacity, 1001, 64, crossing_key.data(), crossing_value.data());
    if (std::memcmp(key.data() + 1001 * Kv, crossing_key.data(), sizeof(crossing_key)) ||
        std::memcmp(value.data() + 1001 * Kv, crossing_value.data(), sizeof(crossing_value))) return 3;
    const uint64_t cache_bytes = cache.bytes();
    std::cout.write(reinterpret_cast<const char*>(&cache_bytes), sizeof(cache_bytes));
    std::cout.write(reinterpret_cast<const char*>(key.data()), bytes);
    std::cout.write(reinterpret_cast<const char*>(value.data()), bytes);
}
