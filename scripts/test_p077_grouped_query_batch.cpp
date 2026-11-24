#include <chrono>
#include <iomanip>
#include <iostream>
#include <string_view>

#define main original_g4_cli
#include "p109_g4_compact_cpu.cpp"
#undef main

#include "p109_g4_grouped_int8_cache.hpp"
#include "p077_g4_grouped_attention.hpp"

namespace {
constexpr int Capacity = 2048;
constexpr int Width = 32;
using Clock = std::chrono::steady_clock;

double us(Clock::duration duration) {
    return std::chrono::duration<double, std::micro>(duration).count();
}

struct TimedCache {
    const GroupedInt8Cache& cache;
    mutable double restore_us = 0.;
    mutable size_t values_restored = 0;

    void restore_block(int slot, int past, int first, int count, float* keys, float* values) const {
        const auto started = Clock::now();
        cache.restore_block(slot, past, first, count, keys, values);
        restore_us += us(Clock::now() - started);
        values_restored += count * Kv;
    }

    void restore_head_block(int slot, int past, int first, int count, int head, float* keys, float* values) const {
        const auto started = Clock::now();
        cache.restore_head_block(slot, past, first, count, head, keys, values);
        restore_us += us(Clock::now() - started);
        values_restored += count * Head;
    }
};

template<typename Cache>
void attend(GroupedBlockAttention& attention, Cache& cache, bool batch, int slot, int past,
            const float* query, const float* key, const float* value, int visible, int count, float* output) {
    if (batch) {
        attention.compute_prefill(cache, slot, past, query, key, value, visible, count, output);
    } else {
        for (int q = 0; q < count; ++q) {
            attention.compute(cache, slot, past, query + q * D, key, value, visible + q, output + q * D);
        }
    }
}

void fill(std::vector<float>& output, int seed, int modulus, float divisor) {
    for (size_t row = 0; row < output.size(); ++row) {
        const int index = static_cast<int>((row * seed) % modulus);
        output[row] = static_cast<float>(index - modulus / 2) / divisor;
    }
}

struct Fixture {
    GroupedInt8Cache cache;
    GroupedBlockAttention attention{Capacity};
    std::vector<float> key, value, query, one, many;
    explicit Fixture(int planes) : cache(Capacity, 1024, planes), key(Capacity * Kv), value(key.size()),
        query(Width * D), one(query.size()), many(query.size()) {
        fill(key, 39, 233, 128.F);
        fill(value, 69, 509, 256.F);
        fill(query, 17, 997, 96.F);
    }

    template<typename Cache>
    void run(bool batch, int slot, int past, int visible, int width, Cache& source) {
        auto& out = batch ? many : one;
        attend(attention, source, batch, slot, past, query.data(), key.data() + past * Kv,
               value.data() + past * Kv, visible, width, out.data());
    }

    void compare(int width) const {
        if (std::memcmp(one.data(), many.data(), width * D * sizeof(float))) {
            throw std::runtime_error("grouped prefill changes an attention value");
        }
    }
};

int check(Fixture& test) {
    int checked = 0;
    for (int slot : {0, Slots - 1}) {
        int past = 0;
        for (int end : {0, 1, 2, 31, 32, 33, 63, 64, 65, 1007, 1023, 1024, 1025, 1055, 1056,
                        1984, 2016, 2046, 2047}) {
            test.cache.append_recent(slot, past, end - past, test.key.data() + past * Kv,
                                     test.value.data() + past * Kv);
            past = end;
            for (int visible : {1, 3}) {
                for (int width : {1, 2, 3, 4, 7, Width}) {
                    if (past + visible + width - 1 > Capacity) continue;
                    test.run(false, slot, past, visible, width, test.cache);
                    test.run(true, slot, past, visible, width, test.cache);
                    test.compare(width);
                    checked += width * D;
                }
            }
        }
    }
    int refused = 0;
    for (auto bounds : {std::array{-1, 1, 1}, std::array{0, 0, 3}, std::array{0, 1, 0},
                        std::array{2047, 1, 2}, std::array{2048, 1, 1}}) {
        try {
            test.attention.compute_prefill(test.cache, 0, bounds[0], test.query.data(), test.key.data(),
                                           test.value.data(), bounds[1], bounds[2], test.many.data());
        } catch (const std::out_of_range&) {
            ++refused;
        }
    }
    if (refused != 5) throw std::runtime_error("grouped prefill accepted an invalid range");
    return checked;
}

void benchmark(Fixture& test, int past) {
    test.cache.append_recent(0, 0, past, test.key.data(), test.value.data());
    test.run(false, 0, past, 1, Width, test.cache);
    test.run(true, 0, past, 1, Width, test.cache);
    test.compare(Width);
    std::cout << "{\"past\":" << past << ",\"samples\":[";
    bool first = true;
    for (int repeat = 0; repeat < 6; ++repeat) {
        for (bool batch : {false, true, true, false}) {
            const auto started = Clock::now();
            test.run(batch, 0, past, 1, Width, test.cache);
            const auto elapsed = us(Clock::now() - started);
            test.compare(Width);
            TimedCache timed{test.cache};
            const auto profile_started = Clock::now();
            test.run(batch, 0, past, 1, Width, timed);
            const auto profile_elapsed = us(Clock::now() - profile_started);
            test.compare(Width);
            if (!first) std::cout << ',';
            first = false;
            std::cout << "{\"batch\":" << batch << ",\"total_us\":" << elapsed
                << ",\"profile_total_us\":" << profile_elapsed << ",\"restore_us\":" << timed.restore_us
                << ",\"restored\":" << timed.values_restored << '}';
        }
    }
    std::cout << "]}";
}
}

int main(int argc, char** argv) {
    const bool verify_only = argc == 2 && std::string_view(argv[1]) == "--verify-only";
    if (argc != 1 && !verify_only) return 2;
    std::cout << std::setprecision(10) << std::boolalpha << '[';
    for (int planes : {0, 3}) {
        if (planes) std::cout << ',';
        Fixture test(planes);
        const int checked = check(test);
        std::cout << "{\"planes\":" << planes << ",\"equal_float_values\":" << checked
            << ",\"workspace_bytes\":" << test.attention.workspace_bytes() << ",\"timing\":[";
        if (!verify_only) {
            for (int past : {512, 1024, 1984}) {
                if (past != 512) std::cout << ',';
                benchmark(test, past);
            }
        }
        std::cout << "]}";
    }
    std::cout << ']' << std::endl;
}
