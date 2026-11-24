#pragma once

#include <Windows.h>
#include <icu.h>

#include <array>
#include <cstdint>
#include <cstring>
#include <functional>
#include <queue>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

namespace win_qbpe {

struct AddedToken {
    std::string_view text;
    uint32_t id;
    bool special;
};

#include "p109_win64_qbpe_contract.inc"

inline void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

inline std::wstring wide(std::string_view text) {
    const int bytes = static_cast<int>(text.size());
    const int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), bytes, nullptr, 0);
    check(count > 0, "invalid UTF-8 input");
    std::wstring value(count, L'\0');
    check(MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), bytes, value.data(), count) == count,
          "incomplete UTF-8 conversion");
    return value;
}

inline std::string utf8(const UChar* start, int count) {
    const std::wstring value(start, start + count);
    const int bytes = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), count, nullptr, 0, nullptr, nullptr);
    check(bytes > 0, "invalid normalized UTF-16 span");
    std::string result(bytes, '\0');
    check(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), count, result.data(), bytes,
                             nullptr, nullptr) == bytes, "incomplete normalized UTF-16 conversion");
    return result;
}

class IcuModule {
public:
    IcuModule() : handle(LoadLibraryExW(L"icu.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32)) {
        check(handle != nullptr, "system ICU could not be opened");
    }
    IcuModule(const IcuModule&) = delete;
    IcuModule& operator=(const IcuModule&) = delete;
    ~IcuModule() { FreeLibrary(handle); }

    template<class Function> Function bind(const char* name) const {
        const auto address = GetProcAddress(handle, name);
        check(address != nullptr, "required ICU export missing");
        return reinterpret_cast<Function>(address);
    }

private:
    const HMODULE handle;
};

class Scaffold {
public:
    Scaffold() {
        UErrorCode status = U_ZERO_ERROR;
        const std::vector<UChar> pattern(RegexPattern, RegexPattern + sizeof(RegexPattern)/sizeof(wchar_t) - 1);
        expression = open(pattern.data(), static_cast<int32_t>(pattern.size()), 0, nullptr, &status);
        if (U_FAILURE(status) || !expression) {
            if (expression) close(expression);
            throw std::runtime_error("sealed split regex could not be compiled");
        }
    }
    Scaffold(const Scaffold&) = delete;
    Scaffold& operator=(const Scaffold&) = delete;
    ~Scaffold() { if (expression) close(expression); }

    std::array<uint8_t, 4> unicode_version() const {
        std::array<uint8_t, 4> version{};
        unicode(version.data());
        return version;
    }

    template<class Emit> void split(std::string_view text, Emit emit) {
        if (text.empty()) return;
        auto current = normalize_text(text);
        UErrorCode status = U_ZERO_ERROR;
        const int32_t size = static_cast<int32_t>(current.size());
        // Retain the buffer until ICU changes its input or closes the expression.
        set_text(expression, current.data(), size, &status);
        if (U_FAILURE(status)) {
            close(expression);
            expression = nullptr;
            throw std::runtime_error("ICU could not bind normalized text");
        }
        normalized.swap(current);
        int32_t previous = 0;
        while (find_next(expression, &status)) {
            const int32_t left = start(expression, 0, &status);
            const int32_t right = end(expression, 0, &status);
            check(U_SUCCESS(status) && previous <= left && left < right && right <= size, "invalid ICU span");
            if (left > previous) emit(utf8(normalized.data() + previous, left - previous));
            emit(utf8(normalized.data() + left, right - left));
            previous = right;
        }
        check(U_SUCCESS(status), "ICU split failed");
        if (previous < size) emit(utf8(normalized.data() + previous, size - previous));
    }

private:
    std::vector<UChar> normalize_text(std::string_view text) const {
        const auto source = wide(text);
        const std::vector<UChar> input(source.begin(), source.end());
        UErrorCode status = U_ZERO_ERROR;
        const auto* form = nfc(&status);
        check(U_SUCCESS(status) && form, "ICU NFC unavailable");
        const auto length = static_cast<int32_t>(input.size());
        const int32_t needed = normalize(form, input.data(), length, nullptr, 0, &status);
        check((U_SUCCESS(status) || status == U_BUFFER_OVERFLOW_ERROR) && needed > 0, "cannot size ICU NFC");
        status = U_ZERO_ERROR;
        std::vector<UChar> output(needed);
        check(normalize(form, input.data(), length, output.data(), needed, &status) == needed &&
              U_SUCCESS(status), "ICU NFC failed");
        return output;
    }

    const IcuModule dll;
    const decltype(&uregex_open) open = dll.bind<decltype(&uregex_open)>("uregex_open");
    const decltype(&uregex_close) close = dll.bind<decltype(&uregex_close)>("uregex_close");
    const decltype(&uregex_setText) set_text = dll.bind<decltype(&uregex_setText)>("uregex_setText");
    const decltype(&uregex_findNext) find_next = dll.bind<decltype(&uregex_findNext)>("uregex_findNext");
    const decltype(&uregex_start) start = dll.bind<decltype(&uregex_start)>("uregex_start");
    const decltype(&uregex_end) end = dll.bind<decltype(&uregex_end)>("uregex_end");
    const decltype(&unorm2_getNFCInstance) nfc = dll.bind<decltype(&unorm2_getNFCInstance)>("unorm2_getNFCInstance");
    const decltype(&unorm2_normalize) normalize = dll.bind<decltype(&unorm2_normalize)>("unorm2_normalize");
    const decltype(&u_getUnicodeVersion) unicode = dll.bind<decltype(&u_getUnicodeVersion)>("u_getUnicodeVersion");
    URegularExpression* expression = nullptr;
    std::vector<UChar> normalized;
};

class Archive {
public:
    Archive(const uint8_t* bytes, size_t size) : data(bytes) {
        check(size == Pieces + PieceBytes && std::memcmp(data, "TLQBPE1", 8) == 0 &&
              read<uint32_t>(8) == Assigned && read<uint32_t>(12) == Ordinary &&
              read<uint32_t>(16) == Rules && read<uint32_t>(20) == PreprocessorBytes &&
              read<uint32_t>(24) == PieceBytes && offset(0) == 0 && offset(Assigned) == PieceBytes,
              "compact QBPE header differs");
    }

    std::vector<uint32_t> encode(std::string_view text, Scaffold& scanner) const {
        std::vector<uint32_t> tokens;
        const auto ordinary = [&](std::string_view part) {
            scanner.split(part, [&](std::string_view word) { merge_word(word, tokens); });
        };
        size_t previous = 0;
        for (size_t at = 0; at < text.size();) {
            const AddedToken* match = nullptr;
            for (const auto& token : Added) {
                if (text[at] == token.text.front() && text.substr(at, token.text.size()) == token.text &&
                    (!match || token.text.size() > match->text.size())) match = &token;
            }
            if (match) {
                ordinary(text.substr(previous, at - previous));
                tokens.push_back(match->id);
                at += match->text.size();
                previous = at;
            } else {
                ++at;
            }
        }
        ordinary(text.substr(previous));
        return tokens;
    }

    std::string decode(const std::vector<uint32_t>& ids, bool skip_special) const {
        std::string raw;
        for (uint32_t id : ids) {
            check(id < Assigned, "token outside the assigned QBPE vocabulary");
            if (skip_special && id >= Ordinary && Added[id - Ordinary].special) continue;
            const auto piece = token_text(id);
            const size_t initial = raw.size();
            if (!append_byte_level(piece, raw)) {
                raw.resize(initial);
                raw.append(piece);
            }
        }
        return utf8_with_replacement(raw);
    }

private:
    struct Choice {
        uint32_t rank, output;
        int left, right;
        uint32_t first, second;
        bool operator>(const Choice& other) const {
            return std::tie(rank, left, right) > std::tie(other.rank, other.left, other.right);
        }
    };
    static constexpr size_t Offsets = 28;
    static constexpr size_t Merges = Offsets + (Assigned + 1) * sizeof(uint32_t);
    static constexpr size_t RuleBytes = 16;
    static constexpr size_t Pieces = Merges + Rules * RuleBytes + PreprocessorBytes;

    template<class Value> Value read(size_t offset_bytes) const {
        Value value;
        std::memcpy(&value, data + offset_bytes, sizeof(value));
        return value;
    }

    uint32_t offset(uint32_t id) const { return read<uint32_t>(Offsets + id * sizeof(uint32_t)); }

    std::string_view token_text(uint32_t id) const {
        const auto left = offset(id), right = offset(id + 1);
        check(left <= right && right <= PieceBytes, "invalid QBPE piece bounds");
        return {reinterpret_cast<const char*>(data + Pieces + left), right - left};
    }

    bool find_merge(Choice& choice) const {
        const uint64_t wanted = (static_cast<uint64_t>(choice.first) << 32) | choice.second;
        size_t low = 0, high = Rules;
        while (low < high) {
            const size_t middle = (low + high) / 2;
            const size_t index = Merges + middle * RuleBytes;
            const auto key = read<uint64_t>(index);
            if (key == wanted) {
                choice.rank = read<uint32_t>(index + 8);
                choice.output = read<uint32_t>(index + 12);
                check(choice.rank < Rules && choice.output >= 256 && choice.output < Ordinary, "invalid QBPE merge");
                return true;
            }
            if (key < wanted) low = middle + 1;
            else high = middle;
        }
        return false;
    }

    void merge_word(std::string_view word, std::vector<uint32_t>& output) const {
        const int count = static_cast<int>(word.size());
        if (count == 1) {
            output.push_back(ByteToId[static_cast<uint8_t>(word[0])]);
            return;
        }
        std::vector<uint32_t> ids(count);
        std::vector<int> previous(count), following(count);
        for (int i = 0; i < count; ++i) {
            ids[i] = ByteToId[static_cast<uint8_t>(word[i])];
            previous[i] = i - 1;
            following[i] = i + 1 < count ? i + 1 : -1;
        }
        std::priority_queue<Choice, std::vector<Choice>, std::greater<Choice>> queue;
        const auto push = [&](int left, int right) {
            if (left < 0 || right < 0) return;
            Choice choice{0, 0, left, right, ids[left], ids[right]};
            if (find_merge(choice)) queue.push(choice);
        };
        for (int i = 1; i < count; ++i) push(i - 1, i);
        while (!queue.empty()) {
            const auto choice = queue.top();
            queue.pop();
            const int left = choice.left, right = choice.right;
            if (following[left] != right || ids[left] != choice.first || ids[right] != choice.second) continue;
            ids[left] = choice.output;
            const int after = following[right];
            following[left] = after;
            following[right] = -1;
            if (after >= 0) previous[after] = left;
            push(previous[left], left);
            push(left, after);
        }
        for (int i = 0; i >= 0; i = following[i]) output.push_back(ids[i]);
    }

    static bool append_byte_level(std::string_view text, std::string& bytes) {
        for (size_t index = 0; index < text.size();) {
            unsigned point = static_cast<uint8_t>(text[index++]);
            if (point >= 128) {
                if (point < 0xc2 || point > 0xdf || index == text.size()) return false;
                const unsigned tail = static_cast<uint8_t>(text[index++]);
                if (tail < 0x80 || tail > 0xbf) return false;
                point = ((point & 0x1f) << 6) | (tail & 0x3f);
            }
            if (point >= PointToByte.size() || PointToByte[point] < 0) return false;
            bytes.push_back(static_cast<char>(PointToByte[point]));
        }
        return true;
    }

    static unsigned sequence_width(unsigned lead) {
        if (lead <= 0x7f) return 1;
        if (lead >= 0xc2 && lead <= 0xdf) return 2;
        if (lead >= 0xe0 && lead <= 0xef) return 3;
        if (lead >= 0xf0 && lead <= 0xf4) return 4;
        return 0;
    }

    static std::string utf8_with_replacement(std::string_view raw) {
        std::string text;
        for (size_t at = 0; at < raw.size();) {
            const unsigned lead = static_cast<uint8_t>(raw[at]);
            const unsigned width = sequence_width(lead);
            unsigned length = 1;
            while (length < width && at + length < raw.size()) {
                const unsigned byte = static_cast<uint8_t>(raw[at + length]);
                unsigned first = 0x80, last = 0xbf;
                if (length == 1) {
                    if (lead == 0xe0) first = 0xa0;
                    if (lead == 0xed) last = 0x9f;
                    if (lead == 0xf0) first = 0x90;
                    if (lead == 0xf4) last = 0x8f;
                }
                if (byte < first || byte > last) break;
                ++length;
            }
            if (length == width) text.append(raw.substr(at, length));
            else text.append("\xef\xbf\xbd");
            at += length;
        }
        return text;
    }

    const uint8_t* data;
};

}  // namespace win_qbpe
