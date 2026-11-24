#include "p109_win64_qbpe.hpp"

#include <cwchar>

namespace {

bool read_frame(std::string& text) {
    uint32_t size = 0;
    const size_t bytes = std::fread(&size, 1, sizeof(size), stdin);
    if (bytes == 0 && std::feof(stdin)) return false;
    require(bytes == sizeof(size) && size <= 65536, "invalid UTF-8 request frame header");
    text.resize(size);
    require(std::fread(text.data(), 1, size, stdin) == size, "truncated UTF-8 request");
    return true;
}

void json_string(std::string_view text) {
    std::fputc('"', stdout);
    for (const unsigned char byte : text) {
        if (byte == '"' || byte == '\\') {
            std::fputc('\\', stdout);
            std::fputc(byte, stdout);
        } else if (byte < 0x20) {
            std::printf("\\u%04x", static_cast<unsigned>(byte));
        } else {
            std::fputc(byte, stdout);
        }
    }
    std::fputc('"', stdout);
}

void json_ids(const std::vector<uint32_t>& ids) {
    std::fputc('[', stdout);
    for (size_t i = 0; i < ids.size(); ++i) std::printf(i ? ",%u" : "%u", ids[i]);
    std::fputc(']', stdout);
}

void tokenizer_check(const wchar_t* path) {
    const Mapping mapped(path);
    const win_qbpe::Archive tokenizer(mapped.data, mapped.size);
    win_qbpe::Scaffold scanner;
    std::string text;
    while (read_frame(text)) {
        const auto ids = tokenizer.encode(text, scanner);
        std::fputs("{\"ids\":", stdout);
        json_ids(ids);
        std::fputs(",\"kept\":", stdout);
        json_string(tokenizer.decode(ids, false));
        std::fputs(",\"stripped\":", stdout);
        json_string(tokenizer.decode(ids, true));
        std::puts("}");
    }
}

void vocabulary_check(const wchar_t* path) {
    const Mapping mapped(path);
    const win_qbpe::Archive tokenizer(mapped.data, mapped.size);
    std::vector<uint32_t> id(1);
    for (id[0] = 0; id[0] < win_qbpe::Assigned; ++id[0]) {
        json_string(tokenizer.decode(id, false));
        std::fputc('\n', stdout);
    }
}

void text_request(const wchar_t* model_path, const wchar_t* tokenizer_path, uint32_t generate) {
    const auto entered = Clock::now();
    const Memory start = read_memory();
    std::vector<uint32_t> ids;
    std::array<uint8_t, 4> unicode{};
    Memory encoding{}, prefilled{};
    {
        std::string text;
        require(read_frame(text) && std::fgetc(stdin) == EOF && !std::ferror(stdin), "expected one UTF-8 request");
        const Mapping mapped(tokenizer_path);
        const win_qbpe::Archive tokenizer(mapped.data, mapped.size);
        win_qbpe::Scaffold scanner;
        unicode = scanner.unicode_version();
        ids = tokenizer.encode(text, scanner);
        encoding = read_memory();
    }
    require(!ids.empty() && ids.size() + generate - 1 <= Limit, "unsupported tokenized request shape");
    const bool icu_released = GetModuleHandleW(L"icu.dll") == nullptr;
    const double encode_seconds = std::chrono::duration<double>(Clock::now() - entered).count();
    const Memory encoded = read_memory();
    std::vector<uint32_t> generated;
    generated.reserve(generate);
    std::array<double, 256> steps{};
    size_t model_bytes, kv_bytes;
    double loaded_seconds;
    Memory loaded{}, complete{};
    {
        const auto opened = Clock::now();
        const Mapping packed(model_path);
        const Model model(packed);
        const uint32_t prefix = static_cast<uint32_t>(ids.size());
        Runtime runtime(model, prefix + generate - 1, false);
        model_bytes = packed.size;
        kv_bytes = runtime.kv_bytes();
        loaded_seconds = std::chrono::duration<double>(Clock::now() - opened).count();
        loaded = read_memory();
        for (uint32_t i = 0; i < generate; ++i) {
            const auto began = Clock::now();
            uint32_t next;
            if (i == 0) {
                uint32_t offset = 0;
                for (; prefix - offset > static_cast<uint32_t>(PrefillTokens); offset += PrefillTokens)
                    runtime.next(ids.data() + offset, PrefillTokens, offset, false);
                next = runtime.next(ids.data() + offset, prefix - offset, offset);
            } else {
                next = runtime.next(&generated.back(), 1, prefix + i - 1);
            }
            steps[i] = std::chrono::duration<double>(Clock::now() - began).count();
            if (i == 0) prefilled = read_memory();
            generated.push_back(next);
            if (next == 248044) break;
        }
        complete = read_memory();
    }
    const auto decode_started = Clock::now();
    const Memory released = read_memory();
    std::string decoded;
    {
        const Mapping mapped(tokenizer_path);
        const win_qbpe::Archive tokenizer(mapped.data, mapped.size);
        decoded = tokenizer.decode(generated, true);
    }
    const double decode_seconds = std::chrono::duration<double>(Clock::now() - decode_started).count();
    std::printf("{\"pid\":%lu,\"icu_released\":%s,\"unicode\":[%u,%u,%u,%u],"
                "\"encode_seconds\":%.9f,\"load_seconds\":%.9f,\"decode_seconds\":%.9f,"
                "\"model_bytes\":%zu,\"kv_bytes\":%zu,\"finish\":\"%s\",\"input_ids\":",
                GetCurrentProcessId(), icu_released ? "true" : "false",
                unsigned(unicode[0]), unsigned(unicode[1]), unsigned(unicode[2]), unsigned(unicode[3]),
                encode_seconds, loaded_seconds, decode_seconds, model_bytes, kv_bytes,
                generated.back() == 248044 ? "eos" : "length");
    json_ids(ids);
    std::fputs(",\"ids\":", stdout);
    json_ids(generated);
    std::fputs(",\"seconds\":[", stdout);
    for (size_t i = 0; i < generated.size(); ++i) std::printf(i ? ",%.9f" : "%.9f", steps[i]);
    std::fputs("],\"decoded\":", stdout);
    json_string(decoded);
    print_memory("start", start);
    print_memory("encoding", encoding);
    print_memory("encoded", encoded);
    print_memory("loaded", loaded);
    print_memory("prefilled", prefilled);
    print_memory("complete", complete);
    print_memory("released", released);
    print_memory("finished", read_memory());
    std::puts("}");
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        require(_setmode(_fileno(stdin), _O_BINARY) != -1 &&
                _setmode(_fileno(stdout), _O_BINARY) != -1, "cannot set binary streams");
        if (argc == 3 && std::wstring_view(argv[1]) == L"--tokenizer") {
            tokenizer_check(argv[2]);
        } else if (argc == 3 && std::wstring_view(argv[1]) == L"--vocab") {
            vocabulary_check(argv[2]);
        } else {
            require(argc == 4, "expected model path, QBPE path and token limit");
            wchar_t* end = nullptr;
            const unsigned long steps = std::wcstoul(argv[3], &end, 10);
            require(end && *end == 0 && steps > 0 && steps <= 256, "unsupported generation limit");
            text_request(argv[1], argv[2], static_cast<uint32_t>(steps));
        }
        require(std::fflush(stdout) == 0 && !std::ferror(stdout), "incomplete native output");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "Windows text request: %s\n", error.what());
        return 1;
    }
}
