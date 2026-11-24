#pragma once

#include "p077_native_table_select.hpp"
#include <set>

namespace p077_description {

using p077_table::split;

struct Record {
    std::string_view title;
    std::string_view summary;
    std::string_view table;
};

inline Record parse_record(std::string_view section) {
    const auto [title, latter] = split(section, "\n<DESCRIPTION>\n");
    const auto [summary, table] = split(latter, "\n<VALUES>\n");
    return {title,summary,table};
}

inline std::set<std::u16string> grams(const std::u16string& text) {
    std::set<std::u16string> result;
    for (size_t i=0; i+3<=text.size(); ++i) result.insert(text.substr(i,3));
    return result;
}

inline p077_table::Selection choose(std::string_view raw, size_t tail, bool use_summary) {
    const auto [lead, remainder] = split(raw,"<SECTION>\n");
    const auto [left, background_and_table] = split(remainder,"\n<BACKGROUND>\n");
    const auto [background, table_and_request] = split(background_and_table,"\n<SECTION>\n");
    const auto [right, request] = split(table_and_request,"\n<REQUEST>\n");
    const auto [hint, question] = split(request,"\n");
    const std::array<Record,2> entries{parse_record(left),parse_record(right)};
    const p077_table::Key key;
    const auto query = key.normalized(hint);
    const auto left_title = key.normalized(entries[0].title);
    const auto right_title = key.normalized(entries[1].title);
    p077_icu::require(!left_title.empty() && !right_title.empty(),"empty table title");
    const bool match_left = query.find(left_title)!=std::u16string::npos;
    const bool match_right = query.find(right_title)!=std::u16string::npos;
    int chosen = match_left && !match_right ? 0 : 1;
    if (use_summary && !match_left && !match_right) {
        const auto query_grams = grams(query);
        const auto left_grams = grams(key.normalized(entries[0].summary));
        const auto right_grams = grams(key.normalized(entries[1].summary));
        int scores[2]{};
        for (const auto& piece : query_grams) {
            const bool has_left = left_grams.count(piece)!=0;
            const bool has_right = right_grams.count(piece)!=0;
            if (has_left != has_right) ++scores[has_left ? 0 : 1];
        }
        if (scores[0]>=2 && scores[0]>scores[1]) chosen=0;
    }
    std::string result(lead);
    result.append(p077_table::suffix(background,tail));
    result.push_back('\n');
    result.append(entries[chosen].table);
    result.append(question);
    return {std::move(result),chosen};
}

}  // namespace p077_description
