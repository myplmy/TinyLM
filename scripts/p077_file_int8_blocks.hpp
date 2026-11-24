// Diagnostic-only backing for the original 8-bit codec, with one recent group in RAM.
class PackedFileGroupedInt8Cache {
public:
    PackedFileGroupedInt8Cache(int capacity, int, int key_bits, int value_bits)
        : capacity_(capacity), group_(GroupRows), file_(std::tmpfile(), &std::fclose) {
        require(capacity > 0 && capacity <= Limit && key_bits == 8 && value_bits == 8 && file_ != nullptr,
                "packed file KV needs the original INT8 codec and a temporary file");
        fd_ = fileno(file_.get());
        require(fd_ >= 0 && ftruncate(fd_, backing_bytes()) == 0, "packed file KV allocation failed");
    }

    size_t bytes() const { return group_.bytes(); }
    size_t backing_bytes() const { return plane_size<true>() + plane_size<false>(); }
    size_t bytes_read() const { return bytes_read_; }
    size_t bytes_written() const { return bytes_written_; }
    size_t allocated_file_bytes() const {
        struct stat data{};
        require(fstat(fd_, &data) == 0, "cannot read packed file KV allocation");
        return data.st_blocks * 512ULL;
    }

    void append_recent(int slot, int past, int count, const float* keys, const float* values) {
        require(slot >= 0 && slot < Slots && written_[slot] == past && count >= 0 && count <= capacity_ - past,
                "packed file KV append range");
        const int end = past + count;
        for (int position = past; position < end;) {
            const int tail = position % GroupRows;
            const int take = std::min(end - position, GroupRows - tail);
            const int offset = (position - past) * Kv;
            group_.append_recent(slot, tail, take, keys + offset, values + offset);
            if (tail + take == GroupRows) {
                save_group<true>(slot, position / GroupRows);
                save_group<false>(slot, position / GroupRows);
            }
            position += take;
        }
        written_[slot] = end;
    }

    void restore_block(int slot, int past, int first, int count, float* keys, float* values) const {
        for (int head = 0; head < KvHeads; ++head) {
            restore_head_block(slot, past, first, count, head, keys, values);
        }
    }

    void restore_head_block(int slot, int past, int first, int count, int head,
                            float* keys, float* values) const {
        require(slot >= 0 && slot < Slots && written_[slot] == past && first >= 0 && first <= past
                && count >= 0 && count <= std::min(past - first, BlockRows) && head >= 0 && head < KvHeads,
                "packed file KV restore range");
        const int complete = past / GroupRows * GroupRows;
        const int stored = std::clamp(complete - first, 0, count);
        if (stored) {
            if (keys) read_groups<true>(slot, head, first, stored, keys);
            if (values) read_groups<false>(slot, head, first, stored, values);
        }
        if (stored < count) {
            group_.restore_head_block(slot, past - complete, first + stored - complete, count - stored, head,
                                      keys ? keys + stored * Kv : nullptr, values ? values + stored * Kv : nullptr);
        }
    }

private:
    static constexpr int GroupRows = GroupedInt8Cache::GroupTokens;
    static constexpr int BlockRows = GroupedBlockAttention::Rows;
    static constexpr int KvHeads = Kv / Head;
    static constexpr int Codes = GroupRows * Head;
    static constexpr int MaxGroups = (BlockRows + 2 * GroupRows - 2) / GroupRows;

    template<bool Keys> static constexpr size_t record_size() {
        return Codes + (Keys ? Head : GroupRows) * sizeof(uint16_t);
    }

    template<bool Keys> size_t plane_size() const {
        return size_t(Slots) * KvHeads * (capacity_ / GroupRows) * record_size<Keys>();
    }

    template<bool Keys> off_t offset(int slot, int head, int group) const {
        const size_t start = Keys ? 0 : plane_size<true>();
        const size_t record = size_t(slot * KvHeads + head) * (capacity_ / GroupRows) + group;
        return start + record * record_size<Keys>();
    }

    void transfer(bool write, size_t length, off_t location) const {
        auto* data = tile_.data();
        while (length) {
            const ssize_t size = write ? pwrite(fd_, data, length, location) : pread(fd_, data, length, location);
            if (size < 0 && errno == EINTR) continue;
            require(size > 0, "incomplete packed file KV transfer");
            if (write) bytes_written_ += size;
            else bytes_read_ += size;
            length -= size;
            location += size;
            data += size;
        }
    }

    template<bool Keys> void save_group(int slot, int group) {
        const auto& codes = Keys ? group_.key_codes_ : group_.value_codes_;
        for (int head = 0; head < KvHeads; ++head) {
            const int base = slot * GroupRows * Kv + head * Head;
            for (int row = 0; row < GroupRows; ++row) {
                std::copy_n(codes.data() + base + row * Kv, Head, tile_.data() + row * Head);
            }
            if constexpr (Keys) {
                std::memcpy(tile_.data() + Codes, group_.key_scales_.data() + slot * Kv + head * Head,
                            Head * sizeof(uint16_t));
            } else {
                for (int row = 0; row < GroupRows; ++row) {
                    const auto& scale = group_.value_scales_[(slot * GroupRows + row) * KvHeads + head];
                    std::memcpy(tile_.data() + Codes + row * sizeof(scale), &scale, sizeof(scale));
                }
            }
            transfer(true, record_size<Keys>(), offset<Keys>(slot, head, group));
        }
    }

    template<bool Keys> void read_groups(int slot, int head, int first, int count, float* output) const {
        const int initial = first / GroupRows;
        const int end = first + count;
        const int groups = (end - 1) / GroupRows - initial + 1;
        transfer(false, groups * record_size<Keys>(), offset<Keys>(slot, head, initial));
        for (int i = 0; i < groups; ++i) {
            const auto* code = tile_.data() + i * record_size<Keys>();
            const auto* scale = code + Codes;
            const int start = (initial + i) * GroupRows;
            const int begin = std::max(first - start, 0);
            const int stop = std::min(end - start, GroupRows);
            constexpr GroupedInt8Cache::CodeGroup codec{0, 8, 0};
            if constexpr (Keys) {
                for (int column = 0; column < Head; column += 8) {
                    const auto packed = _mm_loadu_si128(reinterpret_cast<const __m128i*>(scale + 2 * column));
                    const auto factor = _mm256_cvtph_ps(packed);
                    for (int row = begin; row < stop; ++row) {
                        auto* target = output + (start + row - first) * Kv + head * Head + column;
                        GroupedInt8Cache::restore8(target, code, codec, row * Head + column, factor, _mm256_setzero_ps());
                    }
                }
            } else {
                for (int row = begin; row < stop; ++row) {
                    uint16_t half_scale;
                    std::memcpy(&half_scale, scale + row * sizeof(half_scale), sizeof(half_scale));
                    const auto factor = _mm256_set1_ps(_cvtsh_ss(half_scale));
                    auto* target = output + (start + row - first) * Kv + head * Head;
                    for (int column = 0; column < Head; column += 8) {
                        GroupedInt8Cache::restore8(target + column, code, codec, row * Head + column, factor, _mm256_setzero_ps());
                    }
                }
            }
        }
    }

    int capacity_;
    GroupedInt8Cache group_;
    std::unique_ptr<FILE, int(*)(FILE*)> file_;
    int fd_ = -1;
    std::array<int, Slots> written_{};
    mutable std::array<uint8_t, MaxGroups * (Codes + 2 * std::max(GroupRows, Head))> tile_{};
    mutable size_t bytes_read_ = 0, bytes_written_ = 0;
};
