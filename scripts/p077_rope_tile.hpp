#pragma once

#include <cmath>

template<int Pairs>
inline void fill_rope_tile(const float* frequencies, int start, int count, float* cosine, float* sine) {
    for (int row = 0; row < count; ++row) {
        const float position = static_cast<float>(start + row);
        for (int pair = 0; pair < Pairs; ++pair) {
            const float angle = position * frequencies[pair];
            cosine[row * Pairs + pair] = std::cos(angle);
            sine[row * Pairs + pair] = std::sin(angle);
        }
    }
}
