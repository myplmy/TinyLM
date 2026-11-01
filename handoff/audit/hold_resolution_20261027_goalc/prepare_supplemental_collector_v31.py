"""Handle one explicitly superseded working review, without ignoring unknowns."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
directory = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/historical_review/root_selected_signal_counter_v2"
working, final = directory / "review_012_work.md", directory / "review_012_v2.md"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rows(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^[|][ \t]*(14643|1411355)[ \t]*[|]", line)
        if match:
            ident = "expanded_train:" + match[1]
            assert ident not in result
            assert "expanded_train_" + match[1] + "_v2.txt" in line
            result[ident] = line
    return result


old_rows, final_rows = rows(working), rows(final)
assert old_rows.keys() == final_rows.keys() == {"expanded_train:14643", "expanded_train:1411355"}
registry = AUDIT / "AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V1.json"
record = dict(path=str(working.relative_to(ROOT)), sha256=sha(working),
    canonical_review=str(final.relative_to(ROOT)), canonical_review_sha256=sha(final),
    ids=sorted(old_rows), auxiliary_rows=old_rows, canonical_matching_rows=final_rows,
    root_approved=True, disposition="NONFINAL_WORKING_REVIEW_SUPERSEDED_BY_EXPLICIT_FINAL_REVIEW",
    reason="같은 TASK의 동일 두 ID와 최종 TXT를 명시한 완결 표 review012_v2가 존재한다. 작업중 보조 파일은 보존·해시고정하고 중복 결정으로 세지 않는다.",
    original_auxiliary_preserved=True, root_body_authorship=False, cache_admitted=0)
with registry.open("x", encoding="utf-8") as stream:
    json.dump(dict(schema="EXACT_AUXILIARY_REVIEW_DISPOSITIONS_V1", rows=[record]), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
source = (AUDIT / "collect_supplemental_candidates_v30.py").read_text(encoding="utf-8")
source = source.replace("supplemental_candidates_snapshot_v30.json", "supplemental_candidates_snapshot_v31.json")
anchor = "retracted_history = []"
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '''
auxiliary_path = AUDIT / "AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V1.json"
auxiliary_records = inv.cache.read(auxiliary_path)["rows"]
auxiliary_by_path = {row["path"]: row for row in auxiliary_records}
inv.require(len(auxiliary_records) == len(auxiliary_by_path), "duplicate auxiliary review disposition")
auxiliary_review_history = []
input_pins[str(auxiliary_path.relative_to(ROOT))] = inv.file_sha(auxiliary_path)
for auxiliary in auxiliary_records:
    inv.require(auxiliary["root_approved"] is True and auxiliary["original_auxiliary_preserved"] is True,
                "auxiliary review lacks explicit preserved root disposition")
    inv.require(inv.file_sha(ROOT / auxiliary["path"]) == auxiliary["sha256"], "auxiliary review changed")
    inv.require(inv.file_sha(ROOT / auxiliary["canonical_review"]) == auxiliary["canonical_review_sha256"],
                "explicit final review superseding the auxiliary changed")
    input_pins[auxiliary["path"]] = auxiliary["sha256"]
    input_pins[auxiliary["canonical_review"]] = auxiliary["canonical_review_sha256"]
''')
anchor = '    for review in sorted(directory.glob("review*.md"), key=bound_rank):'
assert source.count(anchor) == 1
source = source.replace(anchor, '''    explicit_reviews = []
    for review in directory.glob("review*.md"):
        auxiliary = auxiliary_by_path.get(str(review.relative_to(ROOT)))
        if auxiliary is None:
            explicit_reviews.append(review)
            continue
        payload = stable(review)
        inv.require(digest(payload) == auxiliary["sha256"], "registered auxiliary changed during collection")
        saved, key = save_content(archive_dir, payload, ".md")
        auxiliary_review_history.append(dict(auxiliary, archive=saved, excluded_as_duplicate_decision=True))
    for review in sorted(explicit_reviews, key=bound_rank):''')
anchor = '              unparsed_review_history=unparsed_review_history,'
assert source.count(anchor) == 1
source = source.replace(anchor, '              auxiliary_review_history=auxiliary_review_history,' + chr(10) + anchor)
anchor = 'inv.require(len(retracted_history) == len(retractions) == 3,'
assert source.count(anchor) == 1
source = source.replace(anchor, '''inv.require(len(auxiliary_review_history) == len(auxiliary_records),
            "registered auxiliary history was not completely preserved")
''' + anchor)
output = AUDIT / "collect_supplemental_candidates_v31.py"
compile(source, str(output), "exec")
with output.open("x", encoding="utf-8") as stream:
    stream.write(source)
print(json.dumps(dict(registry=str(registry.relative_to(ROOT)), registry_sha256=sha(registry),
    auxiliary_files=1, canonical_covered_ids=2, output=str(output.relative_to(ROOT))), ensure_ascii=False))
