#include "p077_qbpe_generated.hpp"

#include <cstdio>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

class Map {
public:
    explicit Map(const char* path) {
        const int fd = open(path, O_RDONLY | O_CLOEXEC);
        win_qbpe::check(fd >= 0, "cannot open QBPE asset");
        struct stat info{};
        if (fstat(fd, &info) || info.st_size <= 0) {
            close(fd);
            throw std::runtime_error("cannot size QBPE asset");
        }
        size = static_cast<size_t>(info.st_size);
        bytes = mmap(nullptr, size, PROT_READ, MAP_PRIVATE, fd, 0);
        close(fd);
        win_qbpe::check(bytes != MAP_FAILED, "cannot map QBPE asset");
    }
    Map(const Map&) = delete;
    Map& operator=(const Map&) = delete;
    ~Map() { munmap(bytes, size); }
    void* bytes = MAP_FAILED;
    size_t size = 0;
};

template<class Value>
void write_word(Value value) {
    win_qbpe::check(fwrite(&value, sizeof(Value), 1, stdout) == 1, "cannot write fixture header");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        win_qbpe::check(argc == 2, "expected the QBPE asset path");
        Map file(argv[1]);
        win_qbpe::Archive tokenizer(static_cast<const uint8_t*>(file.bytes), file.size);
        win_qbpe::Scaffold scanner;
        uint32_t length = 0;
        size_t got = 0;
        while ((got = fread(&length, 1, sizeof(length), stdin)) == sizeof(length)) {
            win_qbpe::check(length <= 65536, "fixture exceeds the UTF-8 limit");
            std::string request(length, '\0');
            win_qbpe::check(fread(request.data(), 1, length, stdin) == length, "truncated fixture input");
            auto ids = tokenizer.encode(request, scanner);
            auto text = tokenizer.decode(ids, false);
            write_word(static_cast<uint32_t>(ids.size()));
            win_qbpe::check(fwrite(ids.data(), sizeof(uint32_t), ids.size(), stdout) == ids.size(),
                            "cannot write token IDs");
            write_word(static_cast<uint32_t>(text.size()));
            win_qbpe::check(fwrite(text.data(), 1, text.size(), stdout) == text.size(), "cannot write decoded UTF-8");
        }
        win_qbpe::check(got == 0 && feof(stdin) && fflush(stdout) == 0, "partial fixture stream");
        return 0;
    } catch (const std::exception& error) {
        fprintf(stderr, "%s\n", error.what());
        return 2;
    }
}
