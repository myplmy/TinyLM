// Experimental backing for the existing G4 INT8 codec and grouped attention.
class FileGroupedInt8Cache {
public:
    FileGroupedInt8Cache(int capacity, int, int key_bits, int value_bits)
        : capacity_(capacity), group_(GroupRows), file_(std::tmpfile(), &std::fclose) {
        require(capacity > 0 && capacity <= Limit && key_bits == 8 && value_bits == 8 && file_ != nullptr,
                "file-backed cache needs the original full INT8 codec and a temporary file");
        fd_ = fileno(file_.get());
        require(fd_ >= 0 && ftruncate(fd_, backing_bytes()) == 0, "file-backed cache allocation failed");
    }

    size_t bytes() const { return group_.bytes(); }
    size_t backing_bytes() const { return 2ULL * Slots * capacity_ * Kv * sizeof(uint16_t); }
    size_t bytes_read() const { return bytes_read_; }
    size_t bytes_written() const { return bytes_written_; }
    size_t allocated_file_bytes() const {
        struct stat data{};
        require(fstat(fd_, &data) == 0, "cannot read file-backed cache allocation");
        return data.st_blocks * 512ULL;
    }

    void append_recent(int slot, int past, int count, const float* keys, const float* values) {
        require(slot >= 0 && slot < Slots && written_[slot] == past && count >= 0 && count <= capacity_ - past,
                "file-backed cache append range");
        const int end = past + count;
        for (int position = past; position < end;) {
            const int tail = position % GroupRows;
            const int take = std::min(end - position, GroupRows - tail);
            const int offset = (position - past) * Kv;
            group_.append_recent(slot, tail, take, keys + offset, values + offset);
            if (tail + take == GroupRows) {
                group_.restore(slot, GroupRows, keys_.data(), values_.data());
                save_plane(0, slot, position - tail, keys_.data());
                save_plane(1, slot, position - tail, values_.data());
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
                && count >= 0 && count <= std::min(past-first, BlockRows) && head >= 0 && head < KvHeads,
                "file-backed cache restore range");
        const int complete = past / GroupRows * GroupRows;
        const int stored = std::clamp(complete - first, 0, count);
        if (stored) {
            if (keys) read_plane(0, slot, head, first, stored, keys);
            if (values) read_plane(1, slot, head, first, stored, values);
        }
        if (stored < count) {
            group_.restore_head_block(slot, past-complete, first+stored-complete, count-stored, head,
                                      keys ? keys + stored*Kv : nullptr, values ? values + stored*Kv : nullptr);
        }
    }

private:
    static constexpr int GroupRows = GroupedInt8Cache::GroupTokens;
    static constexpr int BlockRows = GroupedBlockAttention::Rows;
    static constexpr int KvHeads = Kv / Head;

    off_t offset(int plane, int slot, int head, int position) const {
        return (((plane * Slots + slot) * KvHeads + head) * capacity_ + position) * Head * sizeof(uint16_t);
    }

    void transfer(bool write, size_t length, off_t location) const {
        auto* data = reinterpret_cast<uint8_t*>(tile_.data());
        while (length) {
            const ssize_t size = write ? pwrite(fd_, data, length, location) : pread(fd_, data, length, location);
            if (size < 0 && errno == EINTR) continue;
            require(size > 0, "incomplete file-backed cache transfer");
            if (write) bytes_written_ += size;
            else bytes_read_ += size;
            length -= size;
            location += size;
            data += size;
        }
    }

    void save_plane(int plane, int slot, int start, const float* rows) {
        for (int head = 0; head < KvHeads; ++head) {
            for (int row = 0; row < GroupRows; ++row) {
                store_half(tile_.data() + row*Head, rows + row*Kv + head*Head, Head);
            }
            transfer(true, GroupRows*Head*sizeof(uint16_t), offset(plane, slot, head, start));
        }
    }

    void read_plane(int plane, int slot, int head, int first, int count, float* rows) const {
        transfer(false, count*Head*sizeof(uint16_t), offset(plane, slot, head, first));
        for (int row = 0; row < count; ++row) {
            load_half(rows + row*Kv + head*Head, tile_.data() + row*Head, Head);
        }
    }

    int capacity_;
    GroupedInt8Cache group_;
    std::unique_ptr<FILE, int(*)(FILE*)> file_;
    int fd_ = -1;
    std::array<int, Slots> written_{};
    std::array<float, GroupRows * Kv> keys_{}, values_{};
    mutable std::array<uint16_t, BlockRows * Head> tile_{};
    mutable size_t bytes_read_ = 0, bytes_written_ = 0;
};
