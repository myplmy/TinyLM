// Fixed-shape, pretokenized P079 G4 inference for the P083 R4 experiment.
#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#if defined(__AVX2__) && defined(__FMA__) && defined(__F16C__)
#include <immintrin.h>
#define TLM_G4_AVX2_KERNELS 1
#else
#define TLM_G4_AVX2_KERNELS 0
#include <limits>
#endif
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

extern "C" int p014e_cpu_lookup(const uint8_t*, const float*, const int64_t*, float*,
                                int64_t, int64_t, int64_t, int64_t);

namespace {
constexpr int D = 768, E = 256, F = 2048, V = 32768;
constexpr int Heads = 12, Head = 64, Kv = 3 * Head;
constexpr int Layers = 16, Mlps = 7, Visits = 28, Slots = 14, Limit = 1024;
constexpr int Group = 128, PackedGroup = 26, Tile = 32;
constexpr float Epsilon = 1e-5F;
using Clock = std::chrono::steady_clock;

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

class Mapping {
public:
    explicit Mapping(int fd) {
        constexpr int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
        require(fcntl(fd, F_GET_SEALS) == seals, "model descriptor must be sealed");
        struct stat status{};
        require(fstat(fd, &status) == 0 && status.st_size > 0 && status.st_size < 30000000,
                "invalid model size");
        size = static_cast<size_t>(status.st_size);
        void* address = mmap(nullptr, size, PROT_READ, MAP_PRIVATE, fd, 0);
        require(address != MAP_FAILED, "model mmap failed");
        data = static_cast<const uint8_t*>(address);
    }
    Mapping(const Mapping&) = delete;
    Mapping& operator=(const Mapping&) = delete;
    ~Mapping() { munmap(const_cast<uint8_t*>(data), size); }
    const uint8_t* data = nullptr;
    size_t size = 0;
};

struct Reader {
    const uint8_t* data;
    size_t remaining;

    template<class T> const T* take(size_t count) {
        require(count <= remaining / sizeof(T), "truncated model");
        require(reinterpret_cast<uintptr_t>(data) % alignof(T) == 0, "unaligned model");
        const auto* value = reinterpret_cast<const T*>(data);
        data += count * sizeof(T);
        remaining -= count * sizeof(T);
        return value;
    }
};

struct Matrix {
    const uint8_t* codes;
    const float* scales;
    int rows, cols;
};

Matrix matrix(Reader& stream, int rows, int cols) {
    const int groups = rows * (cols / Group);
    const auto* codes = stream.take<uint8_t>(groups * PackedGroup);
    return {codes, stream.take<float>(groups), rows, cols};
}

struct Layer {
    const float *a_scale, *a_shift, *m_scale, *m_shift, *gates;
    Matrix q, o, k, v;
};

struct Mlp { Matrix gate, up, down; };

struct Model {
    explicit Model(const Mapping& mapping) {
        Reader in{mapping.data, mapping.size};
        require(std::memcmp(in.take<char>(8), "TLMG4R4", 8) == 0, "model magic differs");
        route = in.take<int32_t>(Visits);
        owners = in.take<int32_t>(Layers);
        mlp_index = in.take<int32_t>(Layers);
        codes = in.take<int8_t>(V * E);
        scales = in.take<float>(V);
        embed_up = in.take<float>(D * E);
        cos = in.take<float>(Limit * Head / 2);
        sin = in.take<float>(Limit * Head / 2);
        norm_f = in.take<float>(D);
        for (int i = 0; i < Layers; ++i) {
            require(owners[i] >= 0 && owners[i] <= i && owners[owners[i]] == owners[i],
                    "invalid CLA owner");
            require(mlp_index[i] >= 0 && mlp_index[i] < Mlps, "invalid shared MLP index");
            Layer& layer = layers[i];
            layer.a_scale = in.take<float>(D);
            layer.a_shift = in.take<float>(D);
            layer.m_scale = in.take<float>(D);
            layer.m_shift = in.take<float>(D);
            layer.gates = in.take<float>(2);
            layer.q = matrix(in, D, D);
            layer.o = matrix(in, D, D);
            if (owners[i] == i) {
                layer.k = matrix(in, Kv, D);
                layer.v = matrix(in, Kv, D);
            }
        }
        for (auto& mlp : mlps) {
            mlp.gate = matrix(in, F, D);
            mlp.up = matrix(in, F, D);
            mlp.down = matrix(in, D, F);
        }
        require(in.remaining == 0, "unexpected trailing model bytes");

        int slot = -1, active_owner = -1;
        for (int i = 0; i < Visits; ++i) {
            const int layer = route[i];
            require(layer >= 0 && layer < Layers, "invalid route layer");
            if (owners[layer] == layer) {
                active_owner = layer;
                ++slot;
            }
            require(slot >= 0 && slot < Slots && active_owner == owners[layer],
                    "noncontiguous CLA visits");
            slot_at[i] = slot;
        }
        require(slot + 1 == Slots, "invalid KV slot count");
    }

    const int32_t *route, *owners, *mlp_index;
    const int8_t* codes;
    const float *scales, *embed_up, *cos, *sin, *norm_f;
    std::array<Layer, Layers> layers{};
    std::array<Mlp, Mlps> mlps{};
    std::array<int, Visits> slot_at{};
};

#if TLM_G4_AVX2_KERNELS
float reduce(__m256 value) {
    __m128 sum = _mm_add_ps(_mm256_castps256_ps128(value), _mm256_extractf128_ps(value, 1));
    sum = _mm_hadd_ps(sum, sum);
    return _mm_cvtss_f32(_mm_hadd_ps(sum, sum));
}

float dot(const float* x, const float* y, int width) {
    __m256 a = _mm256_setzero_ps(), b = a, c = a, d = a;
    for (int j = 0; j < width; j += 32) {
        a = _mm256_fmadd_ps(_mm256_loadu_ps(x+j), _mm256_loadu_ps(y+j), a);
        b = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+8), _mm256_loadu_ps(y+j+8), b);
        c = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+16), _mm256_loadu_ps(y+j+16), c);
        d = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+24), _mm256_loadu_ps(y+j+24), d);
    }
    return reduce(_mm256_add_ps(_mm256_add_ps(a, b), _mm256_add_ps(c, d)));
}
#else
float reduce(const std::array<float, 8>& lanes) {
    // The same low/high and horizontal pairing as the AVX2 reduction.
    return ((lanes[0] + lanes[4]) + (lanes[1] + lanes[5])) +
           ((lanes[2] + lanes[6]) + (lanes[3] + lanes[7]));
}

float dot(const float* x, const float* y, int width) {
    std::array<float, 32> sums{};
    for (int j = 0; j < width; j += 32)
        for (int lane = 0; lane < 32; ++lane)
            sums[lane] = std::fma(x[j + lane], y[j + lane], sums[lane]);
    std::array<float, 8> lanes;
    for (int lane = 0; lane < 8; ++lane)
        lanes[lane] = (sums[lane] + sums[lane + 8]) + (sums[lane + 16] + sums[lane + 24]);
    return reduce(lanes);
}
#endif

float output_dot(const float* hidden, const int8_t* row, float row_scale) {
#if TLM_G4_AVX2_KERNELS
    const __m256 scale = _mm256_set1_ps(row_scale);
    __m256 total = _mm256_setzero_ps();
    for (int j = 0; j < E; j += 8) {
        const __m128i bytes = _mm_loadl_epi64(reinterpret_cast<const __m128i*>(row+j));
        const __m256 w = _mm256_mul_ps(_mm256_cvtepi32_ps(_mm256_cvtepi8_epi32(bytes)), scale);
        total = _mm256_fmadd_ps(_mm256_loadu_ps(hidden+j), w, total);
    }
#else
    std::array<float, 8> total{};
    for (int j = 0; j < E; j += 8) {
        for (int lane = 0; lane < 8; ++lane) {
            const float weight = static_cast<float>(row[j + lane]) * row_scale;
            total[lane] = std::fma(hidden[j + lane], weight, total[lane]);
        }
    }
#endif
    return reduce(total);
}

void project(const Matrix& hard, const float* x, float* y, int count, float* weight) {
    for (int64_t row = 0; row < hard.rows; ++row) {
        require(p014e_cpu_lookup(hard.codes, hard.scales, &row, weight, 1, hard.rows,
                                hard.cols, Group) == 0, "invalid 5-trit matrix row");
        for (int t = 0; t < count; ++t)
            y[t * hard.rows + row] = dot(x + t * hard.cols, weight, hard.cols);
    }
}

void normalize(float* dst, const float* src, int width) {
    const float gain = 1.F / std::sqrt(dot(src, src, width) / width + Epsilon);
    for (int j = 0; j < width; ++j) dst[j] = src[j] * gain;
}

void scaled_norm(float* dst, const float* src, const float* scale, const float* shift) {
    normalize(dst, src, D);
    for (int i = 0; i < D; ++i) dst[i] = dst[i] * (1.F + scale[i]) + shift[i];
}

void rotate(float* vector, const float* cos, const float* sin, int width) {
    for (int h = 0; h < width; h += Head) {
        float* row = vector + h;
        normalize(row, row, Head);
        for (int j = 0; j < Head / 2; ++j) {
            const float a = row[j], b = row[j + Head / 2];
            row[j] = a * cos[j] - b * sin[j];
            row[j + Head / 2] = a * sin[j] + b * cos[j];
        }
    }
}

#if TLM_G4_AVX2_KERNELS
void load_half(float* dst, const uint16_t* src, size_t count) {
    for (size_t j = 0; j < count; j += 8)
        _mm256_storeu_ps(dst+j, _mm256_cvtph_ps(_mm_loadu_si128(
            reinterpret_cast<const __m128i*>(src+j))));
}

void store_half(uint16_t* dst, const float* src, size_t count) {
    for (size_t j = 0; j < count; j += 8)
        _mm_storeu_si128(reinterpret_cast<__m128i*>(dst+j),
                         _mm256_cvtps_ph(_mm256_loadu_ps(src+j), _MM_FROUND_TO_NEAREST_INT));
}
#else
static_assert(sizeof(float) == sizeof(uint32_t) && std::numeric_limits<float>::is_iec559 &&
              std::numeric_limits<float>::digits == 24, "IEEE binary32 is required");

float from_half(uint16_t half) {
    const uint32_t sign = uint32_t(half & 0x8000) << 16;
    const uint32_t exponent = (half >> 10) & 31;
    uint32_t fraction = half & 1023;
    uint32_t bits = sign;
    if (exponent == 31) {
        bits |= 0x7f800000 | (fraction << 13);
        if (fraction) bits |= 0x00400000;  // Match F16C quieting of signaling NaNs.
    } else if (exponent != 0) {
        bits |= ((exponent + 112) << 23) | (fraction << 13);
    } else if (fraction != 0) {
        uint32_t normalized_exponent = 113;
        while ((fraction & 1024) == 0) {
            fraction <<= 1;
            --normalized_exponent;
        }
        bits |= (normalized_exponent << 23) | ((fraction & 1023) << 13);
    }
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

uint32_t round_to_even(uint32_t value, int shift) {
    const uint32_t base = value >> shift;
    const uint32_t halfway = 1U << (shift - 1);
    const uint32_t rest = value & ((1U << shift) - 1);
    return base + (rest > halfway || (rest == halfway && (base & 1)));
}

uint16_t to_half(float value) {
    uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    const uint32_t sign = (bits >> 16) & 0x8000;
    const int exponent = (bits >> 23) & 255;
    const uint32_t fraction = bits & 0x007fffff;
    if (exponent == 255 && fraction != 0)
        return static_cast<uint16_t>(sign | 0x7e00 | (fraction >> 13));
    if (exponent > 142) return static_cast<uint16_t>(sign | 0x7c00);
    if (exponent >= 113)
        return static_cast<uint16_t>(sign | (((exponent - 112) << 10) + round_to_even(fraction, 13)));
    if (exponent < 102) return static_cast<uint16_t>(sign);
    return static_cast<uint16_t>(sign | round_to_even(fraction | 0x00800000, 126 - exponent));
}

void load_half(float* dst, const uint16_t* src, size_t count) {
    for (size_t j = 0; j < count; ++j) dst[j] = from_half(src[j]);
}

void store_half(uint16_t* dst, const float* src, size_t count) {
    for (size_t j = 0; j < count; ++j) dst[j] = to_half(src[j]);
}
#endif

void weighted_values(float* output, const float* value, const float* score, int end, float denom,
                     bool accumulate = false) {
#if TLM_G4_AVX2_KERNELS
    __m256 sums[Head / 8]{};
    if (accumulate) {
        for (int j = 0; j < Head / 8; ++j) sums[j] = _mm256_loadu_ps(output + j * 8);
    }
    for (int t = 0; t < end; ++t) {
        const __m256 prob = _mm256_set1_ps(score[t] / denom);
        const float* row = value + t * Kv;
        for (int j = 0; j < Head / 8; ++j)
            sums[j] = _mm256_fmadd_ps(prob, _mm256_loadu_ps(row+j*8), sums[j]);
    }
    for (int j = 0; j < Head / 8; ++j)
        _mm256_storeu_ps(output + j * 8, sums[j]);
#else
    if (!accumulate) std::fill_n(output, Head, 0.F);
    for (int t = 0; t < end; ++t) {
        const float prob = score[t] / denom;
        const float* row = value + t * Kv;
        for (int j = 0; j < Head; ++j)
            output[j] = std::fma(prob, row[j], output[j]);
    }
#endif
}

struct Runtime {
    explicit Runtime(const Model& weights, int capacity)
        : model(weights), capacity(capacity), x(capacity * D), key(capacity * Kv),
          value(capacity * Kv), kept_key(Slots * capacity * Kv),
          kept_value(Slots * capacity * Kv) {}

    size_t kv_bytes() const {
        return (kept_key.capacity() + kept_value.capacity()) * sizeof(uint16_t);
    }

    size_t scratch_bytes() const {
        return sizeof(*this) + (x.capacity() + key.capacity() + value.capacity()) * sizeof(float);
    }

    void begin_slot(const Layer& layer, int slot, int count, int past) {
        auto* ks = kept_key.data() + slot * capacity * Kv;
        auto* vs = kept_value.data() + slot * capacity * Kv;
        load_half(key.data(), ks, past * Kv);
        load_half(value.data(), vs, past * Kv);
        for (int base = 0; base < count; base += Tile) {
            const int width = std::min(Tile, count - base);
            float* k = key.data() + (past + base) * Kv;
            const float* xb = x.data() + base * D;
            project(layer.k, xb, k, width, weight.data());
            project(layer.v, xb, value.data() + (past + base) * Kv, width, weight.data());
            for (int i = 0; i < width; ++i) {
                const int pos = (past + base + i) * (Head / 2);
                rotate(k + i * Kv, model.cos + pos, model.sin + pos, Kv);
            }
        }
        store_half(ks + past * Kv, key.data() + past * Kv, count * Kv);
        store_half(vs + past * Kv, value.data() + past * Kv, count * Kv);
    }

    void attention(const float* q, float* output, int end) {
        for (int head = 0; head < Heads; ++head) {
            const int offset = (head / 4) * Head;
            const float* query = q + head * Head;
            float largest = -INFINITY;
            for (int t = 0; t < end; ++t) {
                score[t] = dot(query, key.data() + t * Kv + offset, Head) * 0.125F;
                largest = std::max(largest, score[t]);
            }
            float denom = 0.F;
            for (int t = 0; t < end; ++t) {
                score[t] = std::exp(score[t] - largest);
                denom += score[t];
            }
            weighted_values(output + head * Head, value.data() + offset, score.data(), end, denom);
        }
    }

    void visit(const Layer& layer, const Mlp& mlp, int count, int past) {
        for (int base = 0; base < count; base += Tile) {
            const int n = std::min(Tile, count - base);
            float* resid = x.data() + base * D;
            for (int t = 0; t < n; ++t)
                scaled_norm(norm.data() + t*D, resid + t*D, layer.a_scale, layer.a_shift);
            project(layer.q, norm.data(), query.data(), n, weight.data());
            for (int t = 0; t < n; ++t) {
                const int pos = past + base + t;
                rotate(query.data() + t*D, model.cos + pos*(Head/2), model.sin + pos*(Head/2), D);
                attention(query.data() + t*D, attn.data() + t*D, pos + 1);
            }
            project(layer.o, attn.data(), projected.data(), n, weight.data());
            for (int j = 0; j < n * D; ++j) resid[j] += layer.gates[0] * projected[j];

            for (int t = 0; t < n; ++t)
                scaled_norm(norm.data() + t*D, resid + t*D, layer.m_scale, layer.m_shift);
            project(mlp.gate, norm.data(), gate.data(), n, weight.data());
            project(mlp.up, norm.data(), up.data(), n, weight.data());
            for (int j = 0; j < n * F; ++j) gate[j] = gate[j] / (1.F + std::exp(-gate[j])) * up[j];
            project(mlp.down, gate.data(), projected.data(), n, weight.data());
            for (int j = 0; j < n * D; ++j) resid[j] += layer.gates[1] * projected[j];
        }
    }

    uint32_t next(const uint32_t* tokens, int count, int past) {
        require(past + count <= capacity && count > 0 && past >= 0, "context exceeds allocation");
        for (int t = 0; t < count; ++t) {
            const uint32_t token = tokens[t];
            require(token < V, "token outside vocabulary");
            for (int j = 0; j < E; ++j) hidden[j] = static_cast<float>(model.codes[token*E+j]) * model.scales[token];
            for (int j = 0; j < D; ++j) x[t*D+j] = dot(hidden.data(), model.embed_up + j*E, E);
        }
        for (int i = 0; i < Visits; ++i) {
            const int index = model.route[i];
            const Layer& layer = model.layers[index];
            if (model.owners[index] == index) begin_slot(layer, model.slot_at[i], count, past);
            visit(layer, model.mlps[model.mlp_index[index]], count, past);
        }
        normalize(norm.data(), x.data() + (count - 1)*D, D);
        hidden.fill(0.F);
        for (int i = 0; i < D; ++i) {
            const float a = norm[i] * model.norm_f[i];
            for (int j = 0; j < E; ++j) hidden[j] += a * model.embed_up[i*E+j];
        }
        for (int token = 0; token < V; ++token) {
            const auto* row = model.codes + token*E;
            logits[token] = output_dot(hidden.data(), row, model.scales[token]);
            require(std::isfinite(logits[token]), "nonfinite output");
        }
        return static_cast<uint32_t>(std::max_element(logits.begin(), logits.end()) - logits.begin());
    }

    const Model& model;
    int capacity;
    std::vector<float> x, key, value;
    std::vector<uint16_t> kept_key, kept_value;
    std::array<float, E> hidden{};
    std::array<float, F> weight{};
    std::array<float, Tile*D> norm{}, query{}, attn{}, projected{};
    std::array<float, Tile*F> gate{}, up{};
    std::array<float, Limit> score{};
    std::array<float, V> logits{};
};

struct Memory {
    size_t rss = 0, pss = 0, private_bytes = 0, high_water = 0;
};

Memory read_memory() {
    Memory m;
    FILE* f = std::fopen("/proc/self/status", "r");
    require(f != nullptr, "unable to read local memory status");
    char line[256];
    size_t value;
    while (fgets(line, sizeof(line), f))
        if (sscanf(line, "VmHWM: %zu kB", &value) == 1) m.high_water = value * 1024;
    fclose(f);
    f = std::fopen("/proc/self/smaps_rollup", "r");
    require(f != nullptr, "unable to read local RSS");
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "Rss: %zu kB", &value) == 1) m.rss = value * 1024;
        if (sscanf(line, "Pss: %zu kB", &value) == 1) m.pss = value * 1024;
        if (sscanf(line, "Private_Clean: %zu kB", &value) == 1 ||
            sscanf(line, "Private_Dirty: %zu kB", &value) == 1) m.private_bytes += value * 1024;
    }
    fclose(f);
    require(m.rss > 0 && m.high_water > 0, "incomplete memory accounting");
    return m;
}

void print_memory(const char* name, const Memory& m) {
    printf(",\"%s\":{\"rss\":%zu,\"pss\":%zu,\"private\":%zu,\"vm_hwm\":%zu}",
           name, m.rss, m.pss, m.private_bytes, m.high_water);
}

void write_logits(int fd, const std::array<float,V>& scores) {
    const char* p = reinterpret_cast<const char*>(scores.data());
    size_t left = scores.size() * sizeof(float);
    while (left) {
        const auto n = write(fd, p, left);
        if (n < 0 && errno == EINTR) continue;
        require(n > 0, "logit output failed");
        p += n;
        left -= static_cast<size_t>(n);
    }
}
}  // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 3, "expected model and optional logit file descriptors");
        const int model_fd = std::stoi(argv[1]), logits_fd = std::stoi(argv[2]);
        uint32_t header[2];
        require(fread(header, sizeof(uint32_t), 2, stdin) == 2, "missing request size");
        const uint32_t prefix = header[0], generate = header[1];
        require(prefix > 0 && prefix <= Limit && generate > 0 && generate <= 8 &&
                prefix + generate - 1 <= Limit, "unsupported request shape");
        std::array<uint32_t, Limit> tokens{};
        require(fread(tokens.data(), sizeof(uint32_t), prefix, stdin) == prefix && fgetc(stdin) == EOF,
                "incorrect request payload size");
        const Memory before = read_memory();
        const auto opened = Clock::now();
        Mapping packed(model_fd);
        Model model(packed);
        Runtime runtime(model, prefix + generate - 1);
        const double load = std::chrono::duration<double>(Clock::now() - opened).count();
        const Memory loaded = read_memory();
        std::array<uint32_t,8> ids{};
        std::array<double,8> times{};
        Memory prefilled{};
        for (uint32_t i = 0; i < generate; ++i) {
            const auto start = Clock::now();
            ids[i] = i == 0 ? runtime.next(tokens.data(), prefix, 0)
                            : runtime.next(&ids[i-1], 1, prefix + i - 1);
            times[i] = std::chrono::duration<double>(Clock::now() - start).count();
            if (i == 0) prefilled = read_memory();
            if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);
        }
        const Memory complete = read_memory();
        printf("{\"model_bytes\":%zu,\"kv_bytes\":%zu,\"scratch_bytes\":%zu,\"load_seconds\":%.9f",
               packed.size, runtime.kv_bytes(), runtime.scratch_bytes(), load);
        print_memory("before", before);
        print_memory("loaded", loaded);
        print_memory("prefilled", prefilled);
        print_memory("complete", complete);
        printf(",\"ids\":[");
        for (uint32_t i = 0; i < generate; ++i) printf("%s%u", i ? "," : "", ids[i]);
        printf("],\"seconds\":[");
        for (uint32_t i = 0; i < generate; ++i) printf("%s%.9f", i ? "," : "", times[i]);
        printf("]}\n");
        return 0;
    } catch (const std::exception& error) {
        fprintf(stderr, "compact CPU: %s\n", error.what());
        return 1;
    }
}
