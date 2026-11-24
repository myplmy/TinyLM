#include <chrono>
#include <iostream>

#define main original_g4_cli
#include "p109_g4_compact_cpu.cpp"
#undef main

#include "p109_g4_grouped_int8_cache.hpp"
#include "p077_g4_grouped_attention.hpp"

namespace {
constexpr int Capacity = 2048;
constexpr int Width = 32;
using Clock = std::chrono::steady_clock;

void fill(std::vector<float>& array, int seed, int modulus, float divisor) {
    for (size_t i = 0; i < array.size(); ++i) {
        const int value = static_cast<int>((i * seed) % modulus) - modulus / 2;
        array[i] = value / divisor;
    }
}

struct Fixture {
    GroupedInt8Cache cache{Capacity, 1920, 4, 2};
    GroupedBlockAttention control{Capacity}, online{Capacity, true};
    std::vector<float> key = std::vector<float>(Capacity * Kv), value = std::vector<float>(Capacity * Kv);
    std::vector<float> query = std::vector<float>(Width * D), a = std::vector<float>(Width * D), b = std::vector<float>(Width * D);
    float error = 0.F;
    int tested = 0;

    Fixture() {
        fill(key, 39, 233, 128.F);
        fill(value, 69, 509, 256.F);
        fill(query, 17, 997, 96.F);
    }

    void read(GroupedBlockAttention& algorithm, int slot, int past, int next, int width, float* out) {
        if (next == 0) {
            algorithm.compute(cache, slot, past, query.data(), nullptr, nullptr, next, out);
        } else {
            algorithm.compute_prefill(cache, slot, past, query.data(), key.data()+past*Kv,
                                      value.data()+past*Kv, next, width, out);
        }
    }

    void compare(int slot, int past, int next, int width) {
        read(control, slot, past, next, width, a.data());
        read(online, slot, past, next, width, b.data());
        for (int i = 0; i < width * D; ++i) {
            if (!std::isfinite(b[i])) throw std::runtime_error("non-finite online attention");
            error = std::max(error, std::fabs(a[i]-b[i]));
        }
        tested += width * D;
    }

    void check() {
        for (const int slot : {0, Slots-1}) {
            int past = 0;
            for (const int end : {0,1,31,32,63,64,65,1023,1919,1920,1921,2046,2047}) {
                cache.append_recent(slot, past, end-past, key.data()+past*Kv, value.data()+past*Kv);
                past = end;
                if (past) compare(slot, past, 0, 1);
                for (int next : {1,3,33,65,129}) {
                    for (int width : {1,2,3,4,7,Width}) {
                        if (past+next+width-1 <= Capacity) compare(slot,past,next,width);
                    }
                }
            }
        }
        if (error > 0.0001F) throw std::runtime_error("online attention exceeds the numeric tolerance");
    }

    void benchmark() {
        constexpr int past = 1984;
        cache.append_recent(0, 0, past, key.data(), value.data());
        compare(0,past,1,Width);
        std::cout << "[";
        bool first = true;
        for (int repeat=0; repeat<6; ++repeat) {
            for (bool candidate : {false,true,true,false}) {
                const auto begin = Clock::now();
                read(candidate ? online : control,0,past,1,Width,b.data());
                const double ms = std::chrono::duration<double,std::milli>(Clock::now()-begin).count();
                if (!first) std::cout << ',';
                first = false;
                std::cout << "{\"online\":" << (candidate ? "true" : "false") << ",\"ms\":" << ms << '}';
            }
        }
        std::cout << ']';
    }
};
}

int main() {
    Fixture fixture;
    fixture.check();
    std::cout << "{\"max_abs\":" << fixture.error << ",\"checked_values\":" << fixture.tested
              << ",\"old_bytes\":" << fixture.control.workspace_bytes()
              << ",\"online_bytes\":" << fixture.online.workspace_bytes() << ",\"timing\":";
    fixture.benchmark();
    std::cout << "}\n";
}
