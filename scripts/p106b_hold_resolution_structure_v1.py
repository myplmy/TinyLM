#!/usr/bin/env python3
"""Prove source structures without writing values or changing source text."""
from collections import Counter, defaultdict
from html.parser import HTMLParser
import ast
import json
import re
from scripts import p106b_hold_resolution_policy_v20 as policy

CREDIT = re.compile(r"^[ \t]*(?:작사|작곡|편곡|작사·작곡·편곡|작곡·편곡|보컬|가|노래)[ \t]*[:：][ \t]*\S")
TRACK_SECTION = {policy.v1.normalize_heading(value) for value in ["수록곡", "수록 곡", "수록곡 목록", "트랙 목록", "track listing"]}
DISC = re.compile(r"(?i)^(?:disc|cd)[ \t]*[0-9]+$|^앵콜$|^앙코르$")
CAST_SECTION = {policy.v1.normalize_heading(value) for value in ["등장 인물", "등장인물", "배역", "출연진", "캐스트"]}
PERSON_RECORD = re.compile(r"^[ \t]*([가-힣A-Za-z\u3040-\u30ff\u3400-\u9fff ·ㆍ'’\-]+)[ \t]*[:：][ \t]*"
                           r"([가-힣A-Za-z\u3040-\u30ff\u3400-\u9fff ·ㆍ'’\-]+)[ \t]*$")
FIELD_LABELS = {"성우", "배우", "역", "캐릭터", "이름", "나이", "연출", "각본", "프로듀서", "가", "작사", "작곡", "편곡"}
COMMENT = re.compile(r"^[ \t]*(?://|--)[^\n]+$")
ASSIGNMENT = re.compile(r"^[ \t]*(?:(?:const|let|var|final)[ \t]+)?(?:[A-Za-z_][A-Za-z0-9_]*[ \t*&]+)?"
                        r"[*&]?[A-Za-z_][A-Za-z0-9_.\[\]]*[ \t]*=(?!=).+;[ \t]*(?://[^\n]*)?$")
PROGRAM_LANGUAGES = {"python", "py", "json", "c", "cpp", "c++", "java", "javascript", "js", "typescript", "ts",
                     "go", "rust", "csharp", "cs", "php", "ruby", "rb", "sql", "bash", "sh", "powershell", "ps1"}


def actual_repeat_contexts(text):
    """All repeated full source lines need an explicit local record context."""
    lines = text.splitlines()
    labels = policy.v4.LABELS | TRACK_SECTION | CAST_SECTION
    counts = Counter(line.strip() for line in lines if len(line.strip()) >= 6
                     and policy.v1.normalize_heading(line) not in labels)
    repeated = {line for line, count in counts.items() if count > 1}
    if not repeated:
        return True  # Different actual inline-code values cannot be duplicates.
    nonempty = [index for index, line in enumerate(lines) if line.strip()]
    next_line = {index: lines[nonempty[pos + 1]].strip() if pos + 1 < len(nonempty) else ""
                 for pos, index in enumerate(nonempty)}
    occurrences = defaultdict(list)
    track_active = cast_active = False
    disc, track, person = "", None, None
    for index, original in enumerate(lines):
        line = original.strip()
        if not line:
            continue
        label = policy.v1.normalize_heading(line)
        if label in TRACK_SECTION:
            track_active, cast_active, track = True, False, None
        elif label in CAST_SECTION:
            cast_active, track_active, person = True, False, None
        elif label in policy.v4.APPENDICES | policy.v4.LABELS | policy.v9.SECTION_NAMES:
            cast_active = track_active = False
            person = track = None
        if track_active:
            if DISC.fullmatch(line):
                disc, track = line, None
            elif not CREDIT.match(line) and CREDIT.match(next_line.get(index, "")):
                track = disc, line
        record = PERSON_RECORD.fullmatch(line) if cast_active else None
        if record and record[1].strip() not in FIELD_LABELS:
            person = record[1].strip(), record[2].strip()
        if line not in repeated:
            continue
        if track_active and CREDIT.match(line) and track is not None:
            context = ("TRACK_CREDIT", *track)
        elif cast_active and person is not None and record is None:
            context = ("CAST_VALUE", *person)
        elif COMMENT.fullmatch(line) and ASSIGNMENT.fullmatch(next_line.get(index, "")):
            context = ("SOURCE_COMMENT_FOR_DISTINCT_EXPRESSION", next_line[index])
        else:
            return False
        occurrences[line].append(context)
    return all(len(values) == len(set(values)) for values in occurrences.values())


def complete_fenced_code_body(text):
    blocks, opened = policy.v1.real_code_blocks(text)
    if opened or not blocks:
        return False
    outside = text
    for lo, hi, body in reversed(blocks):
        lines = body.splitlines()
        language = re.sub(r"^[`~]+", "", lines[0]).strip().lower()
        if language not in PROGRAM_LANGUAGES or not "".join(lines[1:-1]).strip():
            return False
        code = chr(10).join(lines[1:-1])
        if language in {"python", "py", "json"}:
            try:
                if language == "json":
                    json.loads(code)
                else:
                    ast.parse(code)
            except (ValueError, SyntaxError):
                return False
        elif not complete_braced_function(code):
            return False
        outside = outside[:lo] + outside[hi:]
    return not outside.strip()


def complete_braced_function(code):
    if re.search(r"(?m)^[ \t]*[.]{3}[ \t]*;?[ \t]*$", code):
        return False
    stripped = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/', "", code)
    if '"' in stripped or "'" in stripped or "/*" in stripped:
        return False
    definition = re.search(r"(?m)^[ \t]*(?:(?:[A-Za-z_][A-Za-z0-9_<>\[\]]*)[ \t*&]+)+"
                           r"[A-Za-z_][A-Za-z0-9_]*[ \t]*\([^;{}]*\)[ \t]*\{", stripped)
    if definition is None or not stripped.rstrip().endswith("}"):
        return False
    stack, pairs = [], {")": "(", "]": "[", "}": "{"}
    for char in stripped:
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack


def complete_markdown_table_body(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3 or not all(line.startswith("|") and line.endswith("|") for line in lines):
        return False
    cells = [[part.strip() for part in line[1:-1].split("|")] for line in lines]
    width = len(cells[0])
    return (width > 0 and all(cells[0]) and len(cells[1]) == width
            and all(re.fullmatch(r":?-+:?", value) for value in cells[1])
            and all(len(row) == width and all(row) for row in cells[2:]))


def complete_wiki_tables_cover_markup(text):
    """Accept only closed, filled rectangular source tables with a header."""
    plain = policy.plain_text(text)
    lines = plain.splitlines(keepends=True)
    ranges, start, table, offset = [], None, [], 0
    for line in lines:
        value = line.strip()
        if value.startswith("{|"):
            if start is not None:
                return False
            start, table = offset, [value]
        elif start is not None:
            table.append(value)
            if value == "|}":
                if not filled_wiki_table(table):
                    return False
                ranges.append((start, offset + len(line)))
                start, table = None, []
        offset += len(line)
    if start is not None or not ranges:
        return False
    outside = plain
    for lo, hi in reversed(ranges):
        outside = outside[:lo] + re.sub(r"[^\r\n]", " ", outside[lo:hi]) + outside[hi:]
    return not (any(token in outside for token in ["{{", "}}", "[[", "]]", "{|", "|}"])
                or re.search(r"(?m)^[ \t]*\|", outside))


def filled_wiki_table(lines):
    if not lines or not lines[0].startswith("{|") or lines[-1] != "|}":
        return False
    if any(re.search(r"rowspan|colspan|\{\{|\}\}|\{\|", line, re.I) for line in lines[1:-1]):
        return False
    header, row, data = [], [], []
    for line in lines[1:-1]:
        if not line:
            continue
        if line.startswith("|+"):
            if not line[2:].strip() or header or row or data:
                return False
        elif line.startswith("|-"):
            if row:
                data.append(row)
                row = []
        elif line.startswith("!"):
            if row or data:
                return False
            header.extend(value.strip() for value in line[1:].split("!!"))
        elif line.startswith("|"):
            row.extend(value.strip() for value in line[1:].split("||"))
        else:
            if not row:
                return False
            row[-1] += chr(10) + line
    if row:
        data.append(row)
    def populated(value):
        if "|" in value and re.search(r"\b[a-z-]+[ \t]*=", value.split("|", 1)[0], re.I):
            value = value.split("|", 1)[1].strip()
        if not value or value.count("[[") != value.count("]]"):
            return False
        for match in re.finditer(r"\[\[([^\[\]]*)\]\]", value):
            if any(not item.strip() for item in match[1].split("|")):
                return False
        return True
    return bool(header and all(populated(value) for value in header) and data
                and all(len(values) == len(header) and all(populated(value) for value in values) for values in data))


class InlineMarkup(HTMLParser):
    allowed = {"i", "b", "em", "strong", "u", "span", "font", "sup", "sub", "br"}
    css = {"color", "font-weight", "font-style", "text-decoration", "vertical-align", "font-size", "font-family"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack, self.valid, self.seen = [], True, False

    def handle_starttag(self, tag, attrs):
        self.seen = True
        if tag not in self.allowed:
            self.valid = False
        for key, value in attrs:
            if key == "style" and value:
                declarations = [part.strip() for part in value.split(";") if part.strip()]
                if any(part.partition(":")[0].strip().lower() not in self.css or not part.partition(":")[2].strip()
                       for part in declarations):
                    self.valid = False
            elif key not in {"color", "face", "size"} or not value:
                self.valid = False
        if tag != "br":
            self.stack.append([tag, False])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            self.valid = False
        else:
            _, populated = self.stack.pop()
            if not populated:
                self.valid = False

    def handle_data(self, data):
        if data.strip():
            for item in self.stack:
                item[1] = True

    def handle_entityref(self, name):
        from html.entities import name2codepoint
        if name not in name2codepoint:
            self.valid = False
        elif name != "nbsp":
            self.handle_data("entity")

    def handle_charref(self, name):
        try:
            value = int(name[1:], 16) if name.lower().startswith("x") else int(name)
            if not 0 < value <= 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                self.valid = False
            elif not chr(value).isspace():
                self.handle_data("character")
        except ValueError:
            self.valid = False

    def handle_comment(self, data):
        self.valid = False


def complete_semantic_inline_markup(text):
    plain = policy.plain_text(text)
    without_tags = re.sub(r"<[^<>]*>", "", plain)
    if "<" in without_tags or ">" in without_tags:
        return False
    parser = InlineMarkup()
    try:
        parser.feed(plain)
        parser.close()
    except Exception:
        return False
    return parser.seen and parser.valid and not parser.stack


def unbound_source_record_legend(text):
    """A prose number elsewhere is not a value row for a sports-table legend."""
    plain = re.sub(r"<[^<>]+>", "", policy.plain_text(text))
    lines = plain.splitlines()
    heading = re.compile(r"^(?:연도별\s*(?:타격|투구|투수|수비)\s*성적|감독으로서의\s*팀\s*성적|통산\s*성적)$")
    legend = re.compile(r"굵은\s*글씨는[^\n]*최고\s*성적")
    for index, line in enumerate(lines):
        if not legend.search(line):
            continue
        earlier = [pos for pos in range(index) if heading.fullmatch(lines[pos].strip())]
        if not earlier:
            continue
        last = earlier[-1]
        end = index + 1
        while end < len(lines):
            label = policy.v1.normalize_heading(lines[end])
            if (heading.fullmatch(lines[end].strip()) or label in policy.v4.LABELS | policy.v4.APPENDICES | policy.v9.SECTION_NAMES):
                break
            end += 1
        block = chr(10).join(lines[last:end])
        if complete_wiki_tables_cover_markup(block):
            continue
        populated = False
        for row in lines[last:end]:
            cells = [value.strip() for value in row.strip(" |\t").split("|")] if "|" in row else row.split()
            if (len(cells) >= 3 and re.fullmatch(r"[12][0-9]{3}", cells[0])
                    and all(re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?|[-—]", cell) for cell in cells[1:])):
                populated = True
                break
        if not populated:
            return True
    return False
