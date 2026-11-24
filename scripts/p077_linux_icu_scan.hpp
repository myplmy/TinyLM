#pragma once

#include <codecvt>
#include <cstdint>
#include <dlfcn.h>
#include <locale>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

namespace p077_icu {

struct Regex;
struct ParseError;

// ICU 74 is provided by the WSL system. These are the C ABI signatures used here.
using Status = int32_t;
using Open = Regex* (*)(const char16_t*, int32_t, uint32_t, ParseError*, Status*);
using Close = void (*)(Regex*);
using SetText = void (*)(Regex*, const char16_t*, int32_t, Status*);
using FindNext = int8_t (*)(Regex*, Status*);
using GetOffset = int32_t (*)(Regex*, int32_t, Status*);

inline void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

class Module {
public:
    Module() : handle_(dlopen("/lib/x86_64-linux-gnu/libicui18n.so.74", RTLD_NOW | RTLD_LOCAL)) {
        require(handle_ != nullptr, "the installed ICU 74 library could not be opened");
    }
    Module(const Module&) = delete;
    Module& operator=(const Module&) = delete;
    ~Module() { dlclose(handle_); }

    template<class Function>
    Function bind(const char* name) const {
        auto* address = dlsym(handle_, name);
        require(address != nullptr, "required ICU 74 export is missing");
        return reinterpret_cast<Function>(address);
    }

private:
    void* const handle_;
};

class Scanner {
public:
    explicit Scanner(const char16_t* pattern) {
        Status status = 0;
        expression_ = open_(pattern, -1, 0, nullptr, &status);
        if (status > 0 || !expression_) {
            if (expression_) close_(expression_);
            throw std::runtime_error("cannot compile the ByteLevel split regex");
        }
    }
    Scanner(const Scanner&) = delete;
    Scanner& operator=(const Scanner&) = delete;
    ~Scanner() { if (expression_) close_(expression_); }

    template<class Emit>
    void split(std::string_view text, Emit emit) {
        if (text.empty()) return;
        std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> converter;
        auto next = converter.from_bytes(text.data(), text.data() + text.size());
        Status status = 0;
        const auto length = static_cast<int32_t>(next.size());
        set_text_(expression_, next.data(), length, &status);
        if (status > 0) {
            close_(expression_);
            expression_ = nullptr;
            throw std::runtime_error("cannot bind ByteLevel input to ICU");
        }
        text_.swap(next);
        int32_t previous = 0;
        auto span = [&](int32_t left, int32_t right) {
            if (left < right) emit(converter.to_bytes(text_.data() + left, text_.data() + right));
        };
        while (find_next_(expression_, &status)) {
            const auto left = start_(expression_, 0, &status);
            const auto right = end_(expression_, 0, &status);
            require(status <= 0 && previous <= left && left < right && right <= length, "invalid ICU split span");
            span(previous, left);
            span(left, right);
            previous = right;
        }
        require(status <= 0, "ICU split failed");
        span(previous, length);
    }

private:
    const Module library_;
    const Open open_ = library_.bind<Open>("uregex_open_74");
    const Close close_ = library_.bind<Close>("uregex_close_74");
    const SetText set_text_ = library_.bind<SetText>("uregex_setText_74");
    const FindNext find_next_ = library_.bind<FindNext>("uregex_findNext_74");
    const GetOffset start_ = library_.bind<GetOffset>("uregex_start_74");
    const GetOffset end_ = library_.bind<GetOffset>("uregex_end_74");
    Regex* expression_ = nullptr;
    std::u16string text_;
};

}  // namespace p077_icu
