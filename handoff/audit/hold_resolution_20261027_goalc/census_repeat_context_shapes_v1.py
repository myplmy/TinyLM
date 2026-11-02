"""Census every remaining repeat shape without deleting or releasing a line."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

SOURCE = inv.BASE / "draft_proposals_v26_delta_v1"
OUT = inv.BASE / "repeat_context_shape_census_v1"
inv.require(not OUT.exists(), "new immutable shape census required")
report_path = SOURCE / "complete.json"
report = inv.cache.read(report_path)
inv.verify(SOURCE / "unique", report["unique_manifest"])
for name, digest in report["lineage"]["source_code_sha256"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
writer = inv.ShardWriter(OUT / "rows", "repeat_shapes", limit=19_999_999)
counts, features, buckets, global_lines = Counter(), Counter(), Counter(), Counter()
examples, global_examples = defaultdict(list), defaultdict(list)
BYLINE = re.compile(r"(?i)^(?:by[ \t]+|author[ \t]*[:：]|written by[ \t]+|글[ \t]*[:：]|저자[ \t]*[:：]|작성자[ \t]*[:：])\S.{1,110}$")
restricted = {"expanded_train:" + str(n) for n in [14760, 756966, 15695, 1216576, 1250821, 20624, 6030]}
started = time.monotonic()
for row in inv.cache.rows(SOURCE / "unique", report["unique_manifest"]):
    if row["decision"] != "PENDING" or "MAIN_BODY_REPETITION_REQUIRES_CONTEXT" not in row["reasons"]:
        continue
    counts.update(unique=1, occurrences=row["occurrences"])
    if row["id"] in restricted:
        counts["restricted_metadata_only"] += 1
        continue
    candidate = row.get("diagnostic_candidate", "")
    plain = policy.plain_text(candidate)
    lines = plain.splitlines()
    positions = defaultdict(list)
    for number, line in enumerate(lines):
        value = line.strip()
        if len(value) >= 6 and policy.v1.normalize_heading(value) not in policy.v1.LABELS:
            positions[value].append(number)
    repeated = {value: places for value, places in positions.items() if len(places) > 1}
    record_features, details = [], []
    nonempty = [i for i, value in enumerate(lines) if value.strip()]
    neighbors = {index: (lines[nonempty[i - 1]].strip() if i else "",
                         lines[nonempty[i + 1]].strip() if i + 1 < len(nonempty) else "")
                 for i, index in enumerate(nonempty)}
    maximum = max(map(len, repeated), default=0)
    if not repeated:
        record_features.append("NO_UNPROTECTED_REPEAT_AT_CURRENT_LINE_SCOPE")
        bucket = "NO_UNPROTECTED_REPEAT"
    elif all(BYLINE.fullmatch(value) for value in repeated):
        bucket = "ONLY_TYPED_BYLINES"
    elif maximum <= 80 and not any(re.search(r"[.!?。！？]$|(?:이다|했다|한다|된다|있다|없다)[.]?$", value) for value in repeated):
        bucket = "ALL_SHORT_NON_SENTENCE_LINES"
    elif maximum <= 160:
        bucket = "REPEATED_LINES_UP_TO160_CHARACTERS"
    else:
        bucket = "LONGER_REPEATED_FULL_LINES"
    if len(row["reasons"]) == 1:
        record_features.append("ONLY_REPETITION_REASON")
    if repeated and all(len({neighbors[i] for i in places}) == len(places) for places in repeated.values()):
        record_features.append("ALL_LOCAL_NEIGHBOR_PAIRS_DISTINCT_DIAGNOSTIC_ONLY")
    if any(any(right == left + 1 for left, right in zip(places, places[1:])) for places in repeated.values()):
        record_features.append("ADJACENT_IDENTICAL_FULL_LINE")
    if any(len({neighbors[i] for i in places}) < len(places) for places in repeated.values()):
        record_features.append("IDENTICAL_LOCAL_NEIGHBOR_PAIR")
    for value, places in repeated.items():
        digest = inv.sha(value)
        global_lines[digest] += 1
        if len(global_examples[digest]) < 3:
            global_examples[digest].append(dict(id=row["id"], preview=value[:160], characters=len(value)))
        details.append(dict(line_sha256=digest, preview=value[:200], characters=len(value),
            candidate_line_numbers=[i + 1 for i in places], repeats=len(places), typed_byline=bool(BYLINE.fullmatch(value)),
            local_neighbor_sha_pairs=[[inv.sha(before), inv.sha(after)] for before, after in [neighbors[i] for i in places]]))
    features.update(record_features)
    buckets[bucket] += 1
    if len(examples[bucket]) < 12:
        examples[bucket].append(dict(id=row["id"], repeated_lines=len(repeated), longest_repeat=maximum,
            repeated_previews=[dict(preview=value[:160], characters=len(value), occurrences=len(places)) for value, places in repeated.items()][:5]))
    writer.append(dict({key: row[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256",
        "original_text_sha256", "input_ids", "occurrences", "language_bucket"]},
        candidate_sha256=inv.sha(candidate), previous_reasons=row["reasons"], bucket=bucket,
        diagnostic_features=record_features, repeated_lines=details,
        classification_only=True, root_approved=False, cache_admitted=False))
inv.require(counts["unique"] == 21891, "all verified26 repeat sources must be counted")
lineage = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in [report_path, Path(__file__)]}
manifest = writer.close(lineage=lineage)
result = dict(status="ALL21891_REPEAT_SHAPES_COUNTED_NO_RELEASE_OR_TEXT_CHANGE", counts=dict(counts),
    buckets=dict(buckets), features=dict(features), examples=dict(examples),
    top_repeated_line_families=[dict(line_sha256=digest, source_count=count, examples=global_examples[digest])
                              for digest, count in global_lines.most_common(60)],
    rows=manifest, input_pins=lineage, full_native_source_rerun=False,
    body_changed=0, cache_admitted=0, goal_complete=False, training_authorized=False,
    seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", result)
print(json.dumps({key: result[key] for key in ["status", "counts", "buckets", "features", "seconds"]}))
