#include <array>
#include <cstdio>
#include "p077_rope_tile.hpp"

int main() {
    constexpr int Pairs = 32, Limit = 2048;
    std::array<float,Pairs> frequencies{};
    if (std::fread(frequencies.data(), sizeof(float), Pairs, stdin) != Pairs) return 2;
    std::array<float,Limit*Pairs> cosine{}, sine{};
    int past = 0;
    while (past < Limit) {
        const int candidate = (past % 3 == 0 ? 64 : (past % 3 == 1 ? 1 : 31));
        const int count = candidate < Limit - past ? candidate : Limit - past;
        fill_rope_tile<Pairs>(frequencies.data(), past, count, cosine.data()+past*Pairs, sine.data()+past*Pairs);
        past += count;
    }
    if (std::fwrite(cosine.data(), sizeof(float), cosine.size(), stdout) != cosine.size()) return 3;
    if (std::fwrite(sine.data(), sizeof(float), sine.size(), stdout) != sine.size()) return 3;
    return 0;
}
