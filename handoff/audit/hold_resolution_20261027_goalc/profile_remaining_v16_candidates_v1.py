"""Profile every v16 pending diagnostic body, never mistaking it for raw text.

This is a census and representative packet export, not a repair or admission.
Previously restricted/individual sources remain metadata-only. The draft's
original identity and the diagnostic body's separate SHA are both preserved.
"""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v16 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
SOURCE = BASE / "draft_proposals_v16"
OUT = BASE / "remaining_candidate_profile_v16_v1"
inv.require(not OUT.exists(), "candidate census namespace must be new")
report_path = SOURCE / "complete.json"
report = inv.cache.read(report_path)
pins = {str(path.relative_to(ROOT)): inv.file_sha(path)
        for path in [report_path, Path(__file__)]}
inv.verify(SOURCE / "unique", report["unique_manifest"])
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695",
              "expanded_train:1216576", "expanded_train:1250821", "expanded_train:20624"}
counts, reasons, fields, tails, repeat_shapes = (Counter() for _ in range(5))
features, examples, selected = Counter(), defaultdict(list), {}
started = last = time.monotonic()


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def feature(name, row, candidate, context=None):
    features[name] += 1
    if context is not None and len(examples[name]) < 2:
        examples[name].append(dict(id=row["id"], context=context))
    rank = (row["original_text_sha256"], row["id"])
    previous = selected.get(name)
    if previous is None or rank < previous[0]:
        metadata = {key: row[key] for key in ["id", "original_text_sha256", "source", "split",
                    "source_ids", "source_ids_sha256", "input_ids", "language_bucket", "occurrences", "reasons"]}
        selected[name] = (rank, metadata, candidate)


for row in inv.cache.rows(SOURCE / "unique", report["unique_manifest"]):
    if row["decision"] != "PENDING":
        continue
    counts.update(unique_pending=1, occurrences=row["occurrences"])
    reasons.update(row["reasons"])
    if row["id"] in restricted or any("PRIOR_INDIVIDUAL_OR_SPAN" in value for value in row["reasons"]):
        counts.update(individual_or_restricted_metadata_only=1)
        continue
    candidate = row.get("diagnostic_candidate")
    if not isinstance(candidate, str) or not candidate.strip():
        counts.update(no_diagnostic_body_metadata_only=1)
        continue
    counts.update(diagnostic_bodies_profiled=1, diagnostic_characters=len(candidate))
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in policy.v1.protected_parts(candidate)[0])
    topic = "IDENTIFIED" if policy.intro(candidate) else "OTHER_INTRO"
    language = row["language_bucket"]
    size = "SHORT" if len(candidate) < 700 else "MEDIUM" if len(candidate) < 7000 else "LONG"
    primary = row["reasons"][0]
    feature("BODY/" + "/".join([primary, language, topic, size]), row, candidate)
    hits = sorted(list(policy.v1.cache.MISSING_FIELD.finditer(plain)) +
                  list(policy.v10.DANGLING_FIELD.finditer(plain)), key=lambda value: value.start())
    doc_fields = set()
    for match in hits:
        fields[match[0]] += 1
        left = plain[max(0, match.start() - 100):match.start()]
        right = plain[match.end():match.end() + 100]
        kind = "EMPTY_BOOK_TITLE" if "《" in match[0] else "SEPARATOR_SLOT" if any(value in match[0] for value in [",", "，"]) else "EMPTY_PAREN"
        before = "NOMINAL_HANGUL" if re.search(r"[가-힣》〉」』][ \t]*$", left) else "LATIN_WORD" if re.search(r"[A-Za-z_][A-Za-z0-9_:.]*[ \t]*$", left) else "OTHER_LEFT"
        after = "KOREAN_PARTICLE" if re.match(r"\s*(?:은|는|이|가|의|에|을|를|로|와|과|도|란|라고)", right) else "OTHER_RIGHT"
        paragraph = plain[plain.rfind(chr(10) * 2, 0, match.start()) + 2:]
        paragraph = paragraph.split(chr(10) * 2, 1)[0]
        technical = "TECHNICAL" if policy.v2.TECHNICAL.search(paragraph) else "OTHER_CONTEXT"
        key = "/".join(["FIELD", kind, before, after, technical, topic, language])
        if key not in doc_fields:
            feature(key, row, candidate, dict(left=left, literal=match[0], right=right))
        doc_fields.add(key)
    if hits:
        counts.update(candidate_bodies_with_field_signal=1)
    if "UNRESOLVED_FIELD_OR_TITLE" in row["reasons"] and not hits:
        feature("FIELD/NO_POST_CANDIDATE_MATCH/" + topic + "/" + language, row, candidate)
    if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in row["reasons"]:
        blocks = list(policy.BLOCK.finditer(plain))
        values = [value.strip() for value in blocks[-1][0].splitlines() if value.strip()] if blocks else []
        years = [value for value in values if policy.YEAR.fullmatch(value)]
        categories = [value for value in values if policy.CATEGORY.fullmatch(value)]
        unknown = [value for value in values if value not in years + categories]
        tails.update(value for value in unknown if len(value) < 100)
        anchor = "LIFE_PAIR" if (any(re.search(r"출생$", value) for value in years)
                    and any(re.search(r"사망$|살아있는 사람$", value) for value in years)) else "YEAR" if years else "NO_YEAR"
        shape = "NOMINAL" if all(len(value) <= 100 and not re.search(r"[.!?。《》\[\]<>]", value) for value in values) else "MIXED"
        key = "/".join(["APPENDIX", anchor, shape, "UNKNOWN_" + str(min(len(unknown), 2)), topic, language])
        feature(key, row, candidate, dict(final_paragraph=values[-30:]))
    if "MAIN_BODY_REPETITION_REQUIRES_CONTEXT" in row["reasons"]:
        lines = [value.strip() for value in plain.splitlines() if value.strip()]
        frequency = Counter(value for value in lines if len(value) >= 6)
        repeated = [value for value, number in frequency.items() if number > 1]
        shape = "NO_POST_REPEAT" if not repeated else "PROSE" if any(re.search(r"[.!?。]$", value) for value in repeated) else "LIST_OR_LABEL"
        if repeated:
            shape += "/LONG_REPEAT" if any(len(value) > 180 for value in repeated) else "/SHORT_REPEAT"
        repeat_shapes[shape] += 1
        feature("REPEAT/" + shape + "/" + topic + "/" + language, row, candidate,
                dict(repeated=sorted(repeated, key=lambda value: -len(value))[:3]))
    if "RAW_TABLE_OR_TEMPLATE_REQUIRES_CONTEXT" in row["reasons"] or "BROKEN_TABLE_OR_WIKI_MARKUP" in row["reasons"]:
        first = plain.lstrip().split(chr(10), 1)[0]
        shape = "OPEN_TEMPLATE" if first.startswith("{{") else "ORPHAN_CLOSE_ONLY" if "|}" in plain and "{|" not in plain else "OTHER_MARKUP"
        feature("MARKUP/" + shape + "/" + topic + "/" + language, row, candidate, dict(first_line=first[:180]))
    if time.monotonic() - last >= 20:
        print(json.dumps(dict(phase="v16_diagnostic_candidate_census", counts=dict(counts),
                         seconds=round(time.monotonic() - started, 1))), flush=True)
        last = time.monotonic()

inv.require(counts["unique_pending"] == report["unique_counts"]["PENDING"] and
            counts["occurrences"] == report["occurrence_counts"]["PENDING"], "pending census conservation failed")
inv.require(counts["diagnostic_bodies_profiled"] + counts["individual_or_restricted_metadata_only"] +
            counts["no_diagnostic_body_metadata_only"] == counts["unique_pending"], "unexplained profile omission")
packets = {}
for name, (_, metadata, body) in selected.items():
    item = packets.setdefault(metadata["id"], dict(metadata, profile_kinds=[], diagnostic_candidate=body))
    item["profile_kinds"].append(name)
directory = OUT / "review_packets"
directory.mkdir(parents=True)
rows = []
for ident, item in sorted(packets.items()):
    payload = item.pop("diagnostic_candidate").encode("utf-8")
    inv.require(len(payload) < 20_000_000, "candidate packet needs ordered splitting")
    path = directory / (ident.replace(":", "_") + "_diagnostic_candidate.txt")
    with path.open("xb") as stream:
        stream.write(payload)
    rows.append(dict(item, candidate=dict(path=str(path.relative_to(ROOT)), sha256=sha(payload)),
                     packet_text_kind="V16_DIAGNOSTIC_CANDIDATE_NOT_ORIGINAL"))


def write_parts(name, values):
    writer = inv.ShardWriter(OUT / name, name, limit=19_999_999)
    for value in values:
        writer.append(value)
    return writer.close(lineage=pins)


context_manifest = write_parts("contexts", (dict(feature=key, examples=value) for key, value in sorted(examples.items())))
tail_manifest = write_parts("tail_literals", (dict(literal=key, occurrences=value) for key, value in tails.most_common()))
inv.write_json(directory / "manifest.json", dict(status="CANDIDATE_CENSUS_PACKETS_NOT_ADMISSION", rows=rows))
for path, expected in pins.items():
    inv.require(inv.file_sha(ROOT / path) == expected, "census input changed")
result = dict(status="ALL_V16_PENDING_CANDIDATES_PROFILED_OR_EXPLICIT_METADATA_ONLY", counts=dict(counts),
              source_reasons=dict(reasons), features=dict(features), field_literals=dict(fields),
              repeat_shapes=dict(repeat_shapes), contexts_manifest=context_manifest,
              unknown_tail_literals_manifest=tail_manifest, packets=len(rows), input_pins=pins,
              packet_text_kind="DIAGNOSTIC_CANDIDATE_NOT_ORIGINAL", raw_originals_opened=False,
              restricted_parent_content_opened=False, seconds=time.monotonic() - started,
              root_adopted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "complete.json", result)
print(json.dumps(dict(status=result["status"], counts=dict(counts), features=len(features), packets=len(rows),
                      seconds=result["seconds"])), flush=True)
