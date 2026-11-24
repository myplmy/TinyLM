// Emit bit patterns from the same engine code in each build.
#define main compact_entry
#include "p109_g4_compact_cpu.cpp"
#undef main

namespace {
template <class T>
void emit(const T* first, size_t count) {
    if (std::fwrite(first, sizeof(T), count, stdout) != count)
        std::exit(1);
}

uint32_t random_bits(uint32_t& seed) {
    seed = 1664525U * seed + 1013904223U;
    return seed;
}

float ordinary_float(uint32_t& seed) {
    return (static_cast<int>(random_bits(seed) >> 16) - 32768) * 0x1p-12F;
}
}

int main() {
    std::vector<uint16_t> half(65536);
    for (size_t i = 0; i < half.size(); ++i)
        half[i] = static_cast<uint16_t>(i);
    std::vector<float> decoded(half.size());
    load_half(decoded.data(), half.data(), half.size());
    emit(decoded.data(), decoded.size());
    store_half(half.data(), decoded.data(), decoded.size());
    emit(half.data(), half.size());

    std::vector<float> inputs;
    for (int sign : {1, -1}) {
        const float direction = sign > 0 ? 1.F : -1.F;
        for (uint32_t i = 0; i <= 0x7bff; ++i) {
            const float midpoint = i == 0x7bff ? 65520.F : (decoded[i] + decoded[i + 1]) * 0.5F;
            const float edge = direction * midpoint;
            inputs.push_back(std::nextafter(edge, -INFINITY));
            inputs.push_back(edge);
            inputs.push_back(std::nextafter(edge, INFINITY));
        }
    }
    uint32_t seed = 13665;
    for (int i = 0; i < 65536; ++i) {
        uint32_t bits = random_bits(seed);
        float value;
        std::memcpy(&value, &bits, sizeof(value));
        inputs.push_back(value);
    }
    std::vector<uint16_t> encoded(inputs.size());
    store_half(encoded.data(), inputs.data(), inputs.size());
    emit(encoded.data(), encoded.size());

    std::array<float, F> x{}, y{};
    std::array<int8_t, E> row{};
    constexpr int positions = 19;
    std::array<float, positions*Kv> values{};
    std::array<float, positions> scores{};
    std::array<float, Head> attended{};
    for (int trial = 0; trial < 97; ++trial) {
        for (size_t j = 0; j < x.size(); ++j) {
            x[j] = ordinary_float(seed);
            y[j] = ordinary_float(seed);
        }
        for (auto& weight : row)
            weight = static_cast<int8_t>(static_cast<int>(random_bits(seed) >> 24) - 128);
        const std::array<float, 6> dots = {
            dot(x.data(), y.data(), Head), dot(x.data(), y.data(), Kv),
            dot(x.data(), y.data(), E), dot(x.data(), y.data(), D),
            dot(x.data(), y.data(), F), output_dot(x.data(), row.data(), 0.00318531F),
        };
        emit(dots.data(), dots.size());
        for (auto& value : values) value = ordinary_float(seed);
        float denom = 0.F;
        for (auto& score : scores) {
            score = std::abs(ordinary_float(seed));
            denom += score;
        }
        weighted_values(attended.data(), values.data() + 2*Head, scores.data(), positions, denom);
        emit(attended.data(), attended.size());
    }
}
