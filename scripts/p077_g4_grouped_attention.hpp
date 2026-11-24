// Uses the native G4 dot and value-accumulation routines.
class GroupedBlockAttention {
public:
    static constexpr int Rows = 64;
    static constexpr int KvHeads = Kv / Head;
    static constexpr int HeadsPerKv = Heads / KvHeads;
    static constexpr int PrefillQueries = KvHeads;
    static_assert(HeadsPerKv * KvHeads == Heads);

    explicit GroupedBlockAttention(int capacity, bool online = false)
        : capacity_(capacity), online_(online), score_rows_(online ? std::min(capacity, Rows) : capacity),
          scores_(Heads * score_rows_) {}

    size_t score_bytes() const { return scores_.capacity() * sizeof(float); }

    size_t workspace_bytes() const { return score_bytes() + sizeof(block_); }

    template<typename Cache>
    void compute(const Cache& cache, int slot, int past, const float* query,
                 const float* new_key, const float* new_value, int visible_new, float* output) {
        if (past < 0 || visible_new < 0 || past > capacity_ || visible_new > capacity_ - past ||
            past + visible_new == 0) {
            throw std::out_of_range("grouped attention length");
        }
        if (online_) {
            compute_online(cache, slot, past, query, new_key, new_value, visible_new, 1, output);
            return;
        }
        const int end = past + visible_new;
        std::array<float, Heads> largest, denom{};
        largest.fill(-INFINITY);
        const auto compute_scores = [&](const float* keys, int first, int count) {
            for (int head = 0; head < Heads; ++head) {
                const int offset = (head / HeadsPerKv) * Head;
                const float* q = query + head * Head;
                float* score = scores_.data() + head * capacity_ + first;
                for (int t = 0; t < count; ++t) {
                    score[t] = dot(q, keys + t * Kv + offset, Head) * 0.125F;
                    largest[head] = std::max(largest[head], score[t]);
                }
            }
        };
        for (int first = 0; first < past; first += Rows) {
            const int count = std::min(past - first, Rows);
            cache.restore_block(slot, past, first, count, block_.data(), nullptr);
            compute_scores(block_.data(), first, count);
        }
        if (visible_new) compute_scores(new_key, past, visible_new);

        for (int head = 0; head < Heads; ++head) {
            float* score = scores_.data() + head * capacity_;
            for (int t = 0; t < end; ++t) {
                score[t] = std::exp(score[t] - largest[head]);
                denom[head] += score[t];
            }
        }

        std::fill_n(output, Heads * Head, 0.F);
        const auto accumulate = [&](const float* values, int first, int count) {
            for (int head = 0; head < Heads; ++head) {
                const int offset = (head / HeadsPerKv) * Head;
                weighted_values(output + head * Head, values + offset,
                                scores_.data() + head * capacity_ + first, count, denom[head], true);
            }
        };
        for (int first = 0; first < past; first += Rows) {
            const int count = std::min(past - first, Rows);
            cache.restore_block(slot, past, first, count, nullptr, block_.data());
            accumulate(block_.data(), first, count);
        }
        if (visible_new) accumulate(new_value, past, visible_new);
    }

    template<typename Cache>
    void compute_prefill(const Cache& cache, int slot, int past, const float* query,
                         const float* new_key, const float* new_value, int first_visible,
                         int query_count, float* output) {
        if (past < 0 || past > capacity_ || first_visible <= 0 || first_visible > capacity_ - past ||
            query_count <= 0 || query_count - 1 > capacity_ - past - first_visible) {
            throw std::out_of_range("grouped prefill attention length");
        }
        for (int first = 0; first < query_count;) {
            const int width = std::min(PrefillQueries, query_count - first);
            const auto* queries = query + first * D;
            auto* results = output + first * D;
            const int visible = first_visible + first;
            if (width == 1) {
                compute(cache, slot, past, queries, new_key, new_value, visible, results);
            } else if (online_) {
                compute_online(cache, slot, past, queries, new_key, new_value, visible, width, results);
            } else {
                compute_prefill_batch(cache, slot, past, queries, new_key, new_value, visible, width, results);
            }
            first += width;
        }
    }

private:
    template<typename Cache>
    void compute_online(const Cache& cache, int slot, int past, const float* query,
                        const float* new_key, const float* new_value, int first_visible,
                        int query_count, float* output) {
        std::fill_n(output, query_count * D, 0.F);
        const int visible = first_visible + query_count - 1;
        for (int kv_head = 0; kv_head < KvHeads; ++kv_head) {
            const int kv_column = kv_head * Head;
            std::array<float, Heads> largest, denom{};
            largest.fill(-INFINITY);
            const auto score_block = [&](const float* keys, int first, int count, bool cached) {
                for (int i = 0; i < query_count; ++i) {
                    const int n = cached ? count : std::clamp(first_visible + i - first, 0, count);
                    if (!n) continue;
                    for (int h = 0; h < HeadsPerKv; ++h) {
                        const int row = i * HeadsPerKv + h;
                        const int head = kv_head * HeadsPerKv + h;
                        const auto* q = query + i * D + head * Head;
                        auto* score = scores_.data() + row * score_rows_;
                        auto* out = output + i * D + head * Head;
                        float maximum = largest[row];
                        for (int t = 0; t < n; ++t) {
                            score[t] = dot(q, keys + t * Kv + kv_column, Head) * 0.125F;
                            maximum = std::max(maximum, score[t]);
                        }
                        if (maximum > largest[row] && denom[row] > 0.F) {
                            const float scale = std::exp(largest[row] - maximum);
                            denom[row] *= scale;
                            for (int column = 0; column < Head; ++column) out[column] *= scale;
                        }
                        largest[row] = maximum;
                        for (int t = 0; t < n; ++t) {
                            score[t] = std::exp(score[t] - maximum);
                            denom[row] += score[t];
                        }
                    }
                }
            };
            const auto value_block = [&](const float* values, int first, int count, bool cached) {
                for (int i = 0; i < query_count; ++i) {
                    const int n = cached ? count : std::clamp(first_visible + i - first, 0, count);
                    if (!n) continue;
                    for (int h = 0; h < HeadsPerKv; ++h) {
                        const int row = i * HeadsPerKv + h;
                        const int head = kv_head * HeadsPerKv + h;
                        weighted_values(output + i * D + head * Head, values + kv_column,
                                        scores_.data() + row * score_rows_, n, 1.F, true);
                    }
                }
            };
            for (int first = 0; first < past; first += Rows) {
                const int count = std::min(past - first, Rows);
                cache.restore_head_block(slot, past, first, count, kv_head, block_.data(), nullptr);
                score_block(block_.data(), first, count, true);
                cache.restore_head_block(slot, past, first, count, kv_head, nullptr, block_.data());
                value_block(block_.data(), first, count, true);
            }
            for (int first = 0; first < visible; first += Rows) {
                const int count = std::min(visible - first, Rows);
                score_block(new_key + first * Kv, first, count, false);
                value_block(new_value + first * Kv, first, count, false);
            }
            for (int i = 0; i < query_count; ++i) {
                for (int h = 0; h < HeadsPerKv; ++h) {
                    const int head = kv_head * HeadsPerKv + h;
                    auto* out = output + i * D + head * Head;
                    const float inverse = 1.F / denom[i * HeadsPerKv + h];
                    for (int column = 0; column < Head; ++column) out[column] *= inverse;
                }
            }
        }
    }

    template<typename Cache>
    void compute_prefill_batch(const Cache& cache, int slot, int past, const float* query,
                               const float* new_key, const float* new_value, int first_visible,
                               int query_count, float* output) {
        std::fill_n(output, query_count * D, 0.F);
        for (int kv_head = 0; kv_head < KvHeads; ++kv_head) {
            const int kv_column = kv_head * Head;
            std::array<float, Heads> largest, denom{};
            largest.fill(-INFINITY);
            const auto compute_scores = [&](int i, const float* keys, int first, int count) {
                for (int h = 0; h < HeadsPerKv; ++h) {
                    const int row = i * HeadsPerKv + h;
                    const int head = kv_head * HeadsPerKv + h;
                    const auto* q = query + i * D + head * Head;
                    auto* score = scores_.data() + row * capacity_ + first;
                    for (int t = 0; t < count; ++t) {
                        score[t] = dot(q, keys + t * Kv + kv_column, Head) * 0.125F;
                        largest[row] = std::max(largest[row], score[t]);
                    }
                }
            };
            for (int first = 0; first < past; first += Rows) {
                const int count = std::min(past - first, Rows);
                cache.restore_head_block(slot, past, first, count, kv_head, block_.data(), nullptr);
                for (int i = 0; i < query_count; ++i) compute_scores(i, block_.data(), first, count);
            }
            for (int i = 0; i < query_count; ++i) {
                const int visible_new = first_visible + i;
                compute_scores(i, new_key, past, visible_new);
                for (int h = 0; h < HeadsPerKv; ++h) {
                    const int row = i * HeadsPerKv + h;
                    auto* score = scores_.data() + row * capacity_;
                    for (int t = 0; t < past + visible_new; ++t) {
                        score[t] = std::exp(score[t] - largest[row]);
                        denom[row] += score[t];
                    }
                }
            }

            const auto accumulate = [&](int i, const float* values, int first, int count) {
                for (int h = 0; h < HeadsPerKv; ++h) {
                    const int row = i * HeadsPerKv + h;
                    const int head = kv_head * HeadsPerKv + h;
                    weighted_values(output + i * D + head * Head, values + kv_column,
                                    scores_.data() + row * capacity_ + first, count, denom[row], true);
                }
            };
            for (int first = 0; first < past; first += Rows) {
                const int count = std::min(past - first, Rows);
                cache.restore_head_block(slot, past, first, count, kv_head, nullptr, block_.data());
                for (int i = 0; i < query_count; ++i) accumulate(i, block_.data(), first, count);
            }
            for (int i = 0; i < query_count; ++i) accumulate(i, new_value, past, first_visible + i);
        }
    }

    int capacity_;
    bool online_;
    int score_rows_;
    std::vector<float> scores_;
    std::array<float, Rows * Kv> block_{};
};
