#pragma once

#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <string>
#include <string_view>

namespace p077 {

inline std::string select_named_section(std::string_view request) {
    constexpr std::string_view header = "<|im_start|>user\n";
    constexpr std::string_view query_marker = "\n[request ";
    constexpr std::string_view end_marker = "\n[/section]";
    const auto query_start = request.rfind(query_marker);
    if (request.substr(0, header.size()) != header || query_start == std::string_view::npos) {
        throw std::runtime_error("a named section request needs a ChatML user header and a request marker");
    }
    const auto key_start = query_start + query_marker.size();
    const auto key_end = request.find("]\n", key_start);
    if (key_end == std::string_view::npos || key_end <= key_start || key_end - key_start > 32) {
        throw std::runtime_error("the requested section name is malformed");
    }
    const auto key = request.substr(key_start, key_end - key_start);
    if (!std::all_of(key.begin(), key.end(), [](unsigned char c) {
            return std::isalnum(c) || c == '-' || c == '_';
        })) {
        throw std::runtime_error("the requested section name contains an invalid character");
    }
    const auto content = request.substr(header.size() - 1, query_start - header.size() + 1);
    const auto opening = "\n[section " + std::string(key) + "]\n";
    const auto start = content.find(opening);
    if (start == std::string_view::npos || content.find(opening, start + opening.size()) != std::string_view::npos) {
        throw std::runtime_error("the request must name exactly one input section");
    }
    const auto body_start = start + opening.size();
    const auto end = content.find(end_marker, body_start);
    if (end == std::string_view::npos || end == body_start || end - body_start > 4096
            || (end + end_marker.size() < content.size() && content[end + end_marker.size()] != '\n')
            || content.substr(body_start, end - body_start).find("\n[section ") != std::string_view::npos) {
        throw std::runtime_error("the selected section is empty, nested, unclosed, or too large");
    }
    return std::string(header) + std::string(content.substr(body_start, end - body_start)) + " "
        + std::string(request.substr(key_end + 2));
}

}  // namespace p077
