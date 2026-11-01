"""Prove whole source programs and explicit sparse table axes, without edits."""
import ast
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_structure_v1 as previous

ORIGINAL_FILLED_TABLE = previous.filled_wiki_table
ORIGINAL_TABLE_COVER = previous.complete_wiki_tables_cover_markup
LITERALS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
FUNCTION = re.compile(
    r"(?:(?:public|private|protected|static|inline|virtual|extern|const)[ \t]+)*"
    r"(?:unsigned[ \t]+|signed[ \t]+)?"
    r"(?:void|int|char|float|double|bool|long|short|size_t|u?int(?:8|16|32|64)_t|String)"
    r"[ \t*&]+[A-Za-z_][A-Za-z0-9_]*[ \t]*\([^;{}]*\)[ \t\r\n]*\{")
TABLE_BLOCK = re.compile(r"(?ms)^[ \t]*\{\|[^\n]*\n.*?^[ \t]*\|\}[ \t]*(?:\n|\Z)")


def complete_source_program(text):
    """Every character must belong to proved code, not nearby prose."""
    if previous.complete_fenced_code_body(text):
        return True
    try:
        module = ast.parse(text)
    except (SyntaxError, ValueError):
        module = None
    if module is not None and any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                                   ast.Import, ast.ImportFrom)) for item in module.body):
        return True
    masked = re.sub(r'(?m)^[ \t]*#include[ \t]+(?:<[\w./]+>|"[\w./]+")[ \t]*$',
                    lambda match: " " * len(match[0]), text)
    masked = LITERALS.sub(lambda match: re.sub(r"[^\r\n]", " ", match[0]), masked)
    cursor, functions = 0, 0
    while cursor < len(masked):
        if masked[cursor].isspace():
            cursor += 1
            continue
        match = FUNCTION.match(masked, cursor)
        if match is None:
            return False
        start, depth, end = cursor, 1, match.end()
        while end < len(masked) and depth:
            if masked[end] == "{":
                depth += 1
            elif masked[end] == "}":
                depth -= 1
            end += 1
        if depth or not previous.complete_braced_function(text[start:end]):
            return False
        functions += 1
        cursor = end
    return bool(functions)


def explicit_sparse_wiki_table(lines):
    """Retain explicit blanks only with unambiguous named row/column axes."""
    if ORIGINAL_FILLED_TABLE(lines):
        return True
    if len(lines) < 4 or not lines[0].startswith("{|") or lines[-1] != "|}":
        return False
    if any(re.search(r"rowspan|colspan|\{\{|\}\}|\{\||<|>", line, re.I) for line in lines[1:-1]):
        return False
    headers = [line for line in lines[1:-1] if line.startswith("!")]
    if len(headers) != 1:
        return False
    header = [part.strip() for part in headers[0][1:].split("!!")]
    if len(header) < 2 or not all(header) or len(set(header)) != len(header):
        return False
    # The virtual marker is parser input only and is never written to corpus text.
    marker = "P106B_VALIDATION_ONLY_EXPLICIT_EMPTY_CELL"
    if any(marker in line for line in lines):
        return False
    virtual, rows, blanks = [lines[0]], 0, 0
    for line in lines[1:-1]:
        if not line or line.startswith(("!", "|-", "|+")):
            virtual.append(line)
            continue
        if not line.startswith("|") or "|" in line.replace("||", "")[1:] or "=" in line:
            return False
        cells = [part.strip() for part in line[1:].split("||")]
        if len(cells) != len(header) or not cells[0] or not any(cells[1:]):
            return False
        rows += 1
        blanks += sum(not cell for cell in cells)
        virtual.append("|" + "||".join(cell or marker for cell in cells))
    virtual.append(lines[-1])
    return bool(rows and blanks and ORIGINAL_FILLED_TABLE(virtual))


def complete_tables_with_explicit_blanks(text):
    with patch.object(previous, "filled_wiki_table", explicit_sparse_wiki_table):
        return ORIGINAL_TABLE_COVER(text)


def complete_source_table_body(text):
    if previous.complete_markdown_table_body(text):
        return True
    return complete_tables_with_explicit_blanks(text) and not TABLE_BLOCK.sub("", text).strip()
