#pragma once

#include "p077_linux_icu_scan.hpp"
#include <array>

namespace p077_table {

inline std::pair<std::string_view, std::string_view> split(std::string_view text, std::string_view marker) {
    const auto i = text.find(marker);
    p077_icu::require(i != std::string_view::npos, "missing table request delimiter");
    return {text.substr(0, i), text.substr(i + marker.size())};
}

class Key {
public:
    std::u16string normalized(std::string_view value) const {
        std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> codec;
        const auto original = codec.from_bytes(value.data(), value.data() + value.size());
        std::u16string folded(4 * original.size() + 4, u'\0');
        p077_icu::Status status = 0;
        const auto length = fold_(folded.data(), static_cast<int32_t>(folded.size()), original.data(),
                                  static_cast<int32_t>(original.size()), 0, &status);
        p077_icu::require(status <= 0 && length >= 0 && static_cast<size_t>(length) <= folded.size(),
                          "cannot fold table title");
        std::u16string result;
        for (int32_t i = 0; i < length;) {
            const auto begin = i;
            char32_t scalar = folded[i++];
            if (scalar >= 0xd800 && scalar <= 0xdbff) {
                p077_icu::require(i < length && folded[i] >= 0xdc00 && folded[i] <= 0xdfff,
                                  "invalid folded Unicode pair");
                scalar = 0x10000 + ((scalar - 0xd800) << 10) + (folded[i++] - 0xdc00);
            }
            const auto category = category_(static_cast<int32_t>(scalar));
            if (scalar == U'_' || (category >= 1 && category <= 5) || (category >= 9 && category <= 11)) {
                result.append(folded.data() + begin, static_cast<size_t>(i - begin));
            }
        }
        return result;
    }

private:
    using Fold = int32_t (*)(char16_t*, int32_t, const char16_t*, int32_t, uint32_t, p077_icu::Status*);
    using Category = int8_t (*)(int32_t);
    const p077_icu::Module icu_;
    const Fold fold_ = icu_.bind<Fold>("u_strFoldCase_74");
    const Category category_ = icu_.bind<Category>("u_charType_74");
};

inline std::string_view suffix(std::string_view source, size_t count) {
    auto offset = source.size();
    for (size_t i = 0; offset && i < count; ++i) {
        --offset;
        while (offset && (static_cast<unsigned char>(source[offset]) & 0xc0) == 0x80) --offset;
    }
    return source.substr(offset);
}

struct Selection {
    std::string text;
    int table;
};

inline Selection choose(std::string_view input, size_t tail_chars) {
    const auto [lead, rest] = split(input, "<SECTION>\n");
    const auto [first, background_and_table] = split(rest, "\n<BACKGROUND>\n");
    const auto [background, table_and_request] = split(background_and_table, "\n<SECTION>\n");
    const auto [second, request] = split(table_and_request, "\n<REQUEST>\n");
    const auto [hint, question] = split(request, "\n");
    const auto [left_title, left_table] = split(first, "\n");
    const auto [right_title, right_table] = split(second, "\n");
    const Key key;
    const auto normalized = key.normalized(hint);
    const auto left = key.normalized(left_title);
    const auto right = key.normalized(right_title);
    p077_icu::require(!left.empty() && !right.empty(), "missing normalized table title");
    const bool left_match = normalized.find(left) != std::u16string::npos;
    const bool right_match = normalized.find(right) != std::u16string::npos;
    const int chosen = left_match && !right_match ? 0 : 1;
    const std::array<std::string_view, 2> tables{left_table, right_table};
    std::string rendered(lead);
    rendered.append(suffix(background, tail_chars));
    rendered.push_back('\n');
    rendered.append(tables[chosen]);
    rendered.append(question);
    return {std::move(rendered), chosen};
}

}  // namespace p077_table
