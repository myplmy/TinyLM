"""Verify a two-example, newline-only Python repair without executing examples."""
from pathlib import Path
import ast
import hashlib
import io
import json
import tokenize

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
AUDIT = Path(__file__).resolve().parent
source = BASE / "inventory_v1/review_packets/expanded_train_1163026.txt"
candidate = BASE / "agents/context_latin/family_resolution_v1/expanded_train_1163026.txt"
source_bytes, candidate_bytes = source.read_bytes(), candidate.read_bytes()
sha = lambda value: hashlib.sha256(value).hexdigest().upper()
assert sha(source_bytes) == "0D8679409408EEF9CC34AACC36681C50F5BA612AE0426D189269297585A6E2A5"
assert sha(candidate_bytes) == "252BAF0D348BF6FA62D5A6568FE5ED8BC79F1787146A4B4AEBB313B4B68FFF9C"
original, cleaned = source_bytes.decode("utf-8"), candidate_bytes.decode("utf-8")
newline = chr(10)
snippets = [line for line in original.splitlines() if line.startswith("import datetime today = ")]
assert len(snippets) == 2
expected, rows = original, []
ignored = {tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.ENCODING}


def tokens(text):
    result = list(tokenize.generate_tokens(io.StringIO(text).readline))
    assert all(item.type not in {tokenize.INDENT, tokenize.DEDENT} for item in result)
    return [(item.type, item.string) for item in result if item.type not in ignored]


for snippet in snippets:
    assert original.count(snippet) == 1 and snippet.count(" print(") == 1
    replacement = snippet.replace("import datetime today = ", "import datetime" + newline + "today = ", 1)
    replacement = replacement.replace(" print(", newline + "print(", 1)
    assert tokens(snippet) == tokens(replacement)
    tree = ast.parse(replacement)
    assert [type(item).__name__ for item in tree.body] == ["Import", "Assign", "Expr"]
    assert isinstance(tree.body[1].value, ast.Call)
    assert isinstance(tree.body[2].value, ast.Call) and isinstance(tree.body[2].value.func, ast.Name)
    assert tree.body[2].value.func.id == "print"
    rows.append(dict(source=snippet, formatted=replacement, significant_tokens=tokens(snippet),
                     ast_top_level=[type(item).__name__ for item in tree.body], no_indentation_tokens=True))
    expected = expected.replace(snippet, replacement, 1)
assert not original.endswith(newline)
assert cleaned == expected + newline
assert source.read_bytes() == source_bytes and candidate.read_bytes() == candidate_bytes
receipt = dict(status="STATIC_ONLY_NEWLINES_AND_FINAL_LF_VERIFIED", id="expanded_train:1163026",
    source=dict(path=str(source.relative_to(ROOT)), sha256=sha(source_bytes)),
    candidate=dict(path=str(candidate.relative_to(ROOT)), sha256=sha(candidate_bytes)),
    verifier_sha256=sha(Path(__file__).read_bytes()), examples=rows,
    inserted_statement_newlines=4, appended_final_lf=1, other_text_changed=False,
    example_execution=False, example_import_execution=False, runtime_behavior_claim=False)
output = AUDIT / "PYTHON_WHITESPACE_1163026_RECEIPT_V1.json"
with output.open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write(newline)
print(json.dumps(dict(status=receipt["status"], examples=2, output=str(output.relative_to(ROOT))), ensure_ascii=False))
