#include "p077_qbpe_generated.hpp"
#include "p077_named_section_selector.hpp"

#include <cerrno>
#include <charconv>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

using Clock = std::chrono::steady_clock;
using win_qbpe::check;
constexpr uint32_t generation = 32;

class Asset {
public:
    explicit Asset(int fd) {
        struct stat info{};
        check(fstat(fd, &info) == 0 && info.st_size > 0, "cannot size QBPE asset");
        size = static_cast<size_t>(info.st_size);
        mapping = mmap(nullptr, size, PROT_READ, MAP_PRIVATE, fd, 0);
        check(mapping != MAP_FAILED, "cannot map QBPE asset");
    }
    Asset(const Asset&) = delete;
    Asset& operator=(const Asset&) = delete;
    ~Asset() { munmap(mapping, size); }
    const uint8_t* data() const { return static_cast<const uint8_t*>(mapping); }
    size_t size = 0;
private:
    void* mapping = MAP_FAILED;
};

size_t memory(const char* path, std::string_view key) {
    std::ifstream stream(path);
    for (std::string line; std::getline(stream, line);) {
        if (line.compare(0, key.size(), key) != 0) continue;
        std::istringstream value(line.substr(key.size()));
        size_t kb = 0;
        if (value >> kb) return kb * 1024;
    }
    throw std::runtime_error("cannot read process memory");
}

std::string snapshot() {
    return "{\"vm_hwm_bytes\":" + std::to_string(memory("/proc/self/status", "VmHWM:"))
           + ",\"rss_bytes\":" + std::to_string(memory("/proc/self/smaps_rollup", "Rss:")) + "}";
}

double elapsed(Clock::time_point started) {
    return std::chrono::duration<double>(Clock::now() - started).count();
}

void write_all(int fd, const void* data, size_t bytes) {
    auto* start = static_cast<const char*>(data);
    while (bytes) {
        const auto n = write(fd, start, bytes);
        if (n < 0 && errno == EINTR) continue;
        check(n > 0, "short descriptor write");
        start += n;
        bytes -= static_cast<size_t>(n);
    }
}

std::string read_descriptor(int fd) {
    check(lseek(fd, 0, SEEK_SET) == 0, "cannot rewind descriptor");
    std::string result;
    std::array<char, 4096> chunk{};
    for (;;) {
        auto n = read(fd, chunk.data(), chunk.size());
        if (n < 0 && errno == EINTR) continue;
        check(n >= 0, "cannot read descriptor");
        if (!n) return result;
        result.append(chunk.data(), static_cast<size_t>(n));
        check(result.size() <= 1048576, "descriptor report exceeds the limit");
    }
}

void json_ids(std::ostream& stream, const std::vector<uint32_t>& ids) {
    stream << '[';
    for (size_t i = 0; i < ids.size(); ++i) {
        if (i) stream << ',';
        stream << ids[i];
    }
    stream << ']';
}

void json_string(std::ostream& out, std::string_view value) {
    constexpr char hex[] = "0123456789abcdef";
    out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << static_cast<char>(c);
        else if (c < 32) out << "\\u00" << hex[c >> 4] << hex[c & 15];
        else out << static_cast<char>(c);
    }
    out << '"';
}

void encode(char* self, char* engine, char* model, char* archive_fd, bool select) {
    const auto begin = Clock::now();
    const auto startup = snapshot();
    std::array<char, 65537> text{};
    const auto bytes = fread(text.data(), 1, text.size(), stdin);
    check(bytes > 0 && bytes < text.size() && feof(stdin), "invalid UTF-8 request size");
    const int tokens = memfd_create("p077-native-tokens", 0);
    const int encoding = memfd_create("p077-native-encoding", 0);
    const int native = memfd_create("p077-native-engine-report", 0);
    const int stdout_fd = dup(STDOUT_FILENO);
    check(tokens >= 0 && encoding >= 0 && native >= 0 && stdout_fd >= 0, "cannot allocate request descriptors");
    std::ostringstream report;
    {
        Asset asset(std::atoi(archive_fd));
        const win_qbpe::Archive tokenizer(asset.data(), asset.size);
        win_qbpe::Scaffold scanner;
        const auto loaded = snapshot();
        const std::string_view raw(text.data(), bytes);
        const std::string selected = select ? p077::select_named_section(raw) : std::string{};
        const auto input = tokenizer.encode(select ? std::string_view(selected) : raw, scanner);
        check(!input.empty() && input.size() + generation - 1 <= 8192, "input is outside the model context cap");
        const uint32_t header[] = {static_cast<uint32_t>(input.size()), generation};
        write_all(tokens, header, sizeof(header));
        write_all(tokens, input.data(), input.size() * sizeof(uint32_t));
        report << "{\"pid\":" << getpid() << ",\"bytes\":" << bytes << ",\"ids\":";
        json_ids(report,input);
        report << ",\"startup\":" << startup << ",\"loaded\":" << loaded << ",\"complete\":" << snapshot()
               << ",\"seconds\":" << elapsed(begin) << '}';
    }
    const auto encoder_report = report.str();
    write_all(encoding, encoder_report.data(), encoder_report.size());
    check(lseek(tokens, 0, SEEK_SET) == 0 && dup2(tokens, STDIN_FILENO) >= 0 && dup2(native, STDOUT_FILENO) >= 0,
          "cannot connect native engine descriptors");
    close(tokens);
    auto output_arg = std::to_string(stdout_fd), encoding_arg = std::to_string(encoding), native_arg = std::to_string(native);
    char unused[] = "-1";
    char* args[] = {engine, model, output_arg.data(), self, self, archive_fd, unused,
                    encoding_arg.data(), native_arg.data(), nullptr};
    execv(engine, args);
    throw std::runtime_error("cannot exec the pinned model engine");
}

std::vector<uint32_t> read_ids(std::string_view engine) {
    constexpr std::string_view field = "\"ids\":[";
    const auto found = engine.find(field);
    check(found != std::string_view::npos, "engine report missing output IDs");
    size_t pos = found + field.size();
    std::vector<uint32_t> ids;
    while (pos < engine.size() && engine[pos] != ']') {
        uint32_t id = 0;
        const auto converted = std::from_chars(engine.data() + pos, engine.data() + engine.size(), id);
        check(converted.ec == std::errc{} && id < win_qbpe::Assigned, "invalid output ID");
        pos = static_cast<size_t>(converted.ptr - engine.data());
        check(pos < engine.size() && (engine[pos] == ',' || engine[pos] == ']'), "invalid output field delimiter");
        ids.push_back(id);
        if (engine[pos] == ',') ++pos;
    }
    check(pos < engine.size() && !ids.empty() && ids.size() <= generation, "invalid generated token count");
    return ids;
}

void decode(int archive_fd, int encoding_fd, int native_fd) {
    const auto begin = Clock::now();
    const auto startup = snapshot();
    const auto encoded = read_descriptor(encoding_fd);
    const auto engine = read_descriptor(native_fd);
    const auto pid = std::to_string(getpid());
    const auto header = "{\"pid\":" + pid + ",\"native\":";
    check(encoded.compare(0, pid.size()+8, "{\"pid\":" + pid + ",") == 0
          && engine.compare(0, header.size(), header) == 0, "inherited process ID differs");
    const auto end = engine.rfind('}');
    check(end != std::string::npos && end > header.size(), "incomplete native result");
    const auto native = std::string_view(engine).substr(header.size(), end-header.size());
    const auto ids = read_ids(native);
    const Asset asset(archive_fd);
    const win_qbpe::Archive tokenizer(asset.data(), asset.size);
    const auto loaded = snapshot();
    const auto text = tokenizer.decode(ids, true);
    std::ostringstream report;
    report << "{\"encoding\":" << encoded << ",\"native\":" << native << ",\"native_pid\":" << pid
           << ",\"decoding\":{\"pid\":" << pid << ",\"startup\":" << startup << ",\"loaded\":" << loaded
           << ",\"complete\":" << snapshot() << ",\"seconds\":" << elapsed(begin) << ",\"text\":";
    json_string(report,text);
    report << "}}\n";
    const auto result = report.str();
    write_all(STDOUT_FILENO, result.data(), result.size());
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 5 && (std::strcmp(argv[1], "encode") == 0 || std::strcmp(argv[1], "select") == 0))
            encode(argv[0],argv[2],argv[3],argv[4],std::strcmp(argv[1], "select") == 0);
        else if (argc == 12 && std::strcmp(argv[7], "decode") == 0) {
            decode(std::atoi(argv[8]),std::atoi(argv[10]),std::atoi(argv[11]));
        } else throw std::runtime_error("unsupported native QBPE invocation");
        return 0;
    } catch (const std::exception& exception) {
        fprintf(stderr, "%s\n", exception.what());
        return 2;
    }
}
