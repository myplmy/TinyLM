"""Profile every remaining v11 source without proposing edits or admissions.

The original interval/hash reader and write-once shard manifests are reused.
Raw syntax signals are explicitly before editing and may be false positives.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
import heapq
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v11 as policy

BASE = inv.BASE
source = BASE / "draft_proposals_v11"
out = BASE / "remaining_profile_v11_v1"
inv.require(not out.exists(), "immutable profile namespace required")
report = inv.cache.read(source / "complete.json")
inv.verify(source / "unique", report["unique_manifest"])
pins = {str(path.relative_to(ROOT)): inv.file_sha(path)
        for path in [source / "complete.json", Path(__file__)]}
counts, features, fields, unknown_tail, repeat_shapes = Counter(), Counter(), Counter(), Counter(), Counter()
heaps, examples = defaultdict(list), defaultdict(list)
started = last = time.monotonic()


def example(kind, row, context=None):
    features[kind] += 1
    if context is not None and len(examples[kind]) < 2:
        examples[kind].append(dict(id=row["id"], source_sha256=row["original_text_sha256"], context=context))
    entry = (-int(row["original_text_sha256"], 16), row["id"], row)
    if not heaps[kind]:
        heapq.heappush(heaps[kind], entry)
    elif entry[:2] > heaps[kind][0][:2]:
        heapq.heapreplace(heaps[kind], entry)


with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / "scope.json"), stack)
    for row in inv.cache.rows(source / "unique", report["unique_manifest"]):
        if row["decision"] != "PENDING":
            continue
        counts.update(unique_pending=1, occurrences=row["occurrences"])
        if any("PRIOR_INDIVIDUAL_OR_SPAN" in reason for reason in row["reasons"]):
            counts.update(prior_individual_metadata_only=1)
            continue
        inv.require(row["id"] not in {"expanded_train:756966", "expanded_train:14760"},
                    "restricted source cannot enter general source profile")
        raw, complete, valid = reader.text(row)
        inv.require(complete and valid, "unexpected unfinished residual source")
        counts.update(raw_bodies_profiled=1)
        plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                        for protected, part in policy.v1.protected_parts(raw)[0])
        identified = policy.previous.previous.intro(raw)
        topic = "IDENTIFIED" if identified else "OTHER_INTRO"
        language = row["language_bucket"]
        primary = row["reasons"][0]
        size = "SHORT" if len(raw) < 700 else "MEDIUM" if len(raw) < 7000 else "LONG"
        example("SOURCE/" + primary + "/" + language + "/" + topic + "/" + size, row)
        if "UNRESOLVED_FIELD_OR_TITLE" in row["reasons"]:
            hits = sorted(list(policy.v1.cache.MISSING_FIELD.finditer(plain)) +
                          list(policy.previous.DANGLING_FIELD.finditer(plain)), key=lambda match: match.start())
            kinds = set()
            for match in hits:
                literal = match[0]
                fields[literal] += 1
                left, right = plain[max(0, match.start() - 90):match.start()], plain[match.end():match.end() + 90]
                kind = "EMPTY_BOOK_TITLE" if "《" in literal else "SEPARATOR_SLOT" if "," in literal or "，" in literal else "EMPTY_PAREN"
                before = "NOMINAL_HANGUL" if re.search(r"[가-힣》〉」』][ \t]*$", left) else "LATIN_WORD" if re.search(r"[A-Za-z_][A-Za-z0-9_:.]*[ \t]*$", left) else "OTHER_LEFT"
                after = "KOREAN_PARTICLE" if re.match(r"\s*(?:은|는|이|가|의|에|을|를|로|와|과|도|란|라고)", right) else "OTHER_RIGHT"
                key = "/".join(["FIELD", kind, before, after, topic, language])
                if key not in kinds:
                    example(key, row, dict(left=left, literal=literal, right=right))
                kinds.add(key)
            if not hits:
                example("FIELD/NO_RAW_MATCH/" + topic + "/" + language, row)
        if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in row["reasons"]:
            lines = [line.strip() for line in plain.splitlines() if line.strip()]
            tail = lines[-24:]
            years = [line for line in tail if policy.YEAR.fullmatch(line)]
            categories = [line for line in tail if policy.CATEGORY.fullmatch(line)]
            unknown = [line for line in tail if len(line) < 100 and re.search(r"[가-힣]", line)
                       and policy.v1.normalize_heading(line) not in policy.v4.LABELS
                       and line not in years + categories and not re.search(r"[.!?。]$", line)]
            unknown_tail.update(unknown)
            key = "/".join(["APPENDIX", topic, "YEAR_" + str(min(len(years), 2)),
                            "CATEGORY_" + str(min(len(categories), 2)), language])
            example(key, row, dict(tail=tail))
        if "MAIN_BODY_REPETITION_REQUIRES_CONTEXT" in row["reasons"]:
            lines = [line.strip() for line in plain.splitlines() if line.strip()]
            frequency = Counter(line for line in lines if len(line) >= 6)
            repeated = [line for line, number in frequency.items() if number > 1]
            shape = "PROSE" if any(re.search(r"[.!?。]$", line) for line in repeated) else "LIST_OR_LABEL"
            shape += "/LONG_REPEAT" if any(len(line) > 180 for line in repeated) else "/SHORT_REPEAT"
            repeat_shapes[shape] += 1
            example("REPEAT/" + shape + "/" + topic + "/" + language, row,
                    dict(repeated=sorted(repeated, key=lambda line: -len(line))[:3]))
        if time.monotonic() - last >= 20:
            print(json.dumps(dict(phase="raw_remaining_v11_profile", counts=dict(counts),
                                  seconds=round(time.monotonic() - started, 1))), flush=True)
            last = time.monotonic()
    inv.require(counts["unique_pending"] == report["unique_counts"]["PENDING"] and
                counts["occurrences"] == report["occurrence_counts"]["PENDING"], "remaining coverage differs")
    chosen = {}
    for key, heap in heaps.items():
        for _, _, row in heap:
            chosen.setdefault(row["original_text_sha256"], dict(row, profile_kinds=[]))["profile_kinds"].append(key)
    directory = out / "review_packets"
    directory.mkdir(parents=True)
    packets = []
    for row in sorted(chosen.values(), key=lambda item: item["id"]):
        raw, _, _ = reader.text(row)
        path = directory / (row["id"].replace(":", "_") + "_original.txt")
        payload = raw.encode("utf-8")
        inv.require(len(payload) < 20_000_000, "source review packet needs ordered splitting")
        with path.open("xb") as stream:
            stream.write(payload)
        packets.append(dict(row, path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)))

inv.require(pins[str(Path(__file__).relative_to(ROOT))] == inv.file_sha(Path(__file__)), "profile source changed")
def write_parts(name, values):
    writer = inv.ShardWriter(out / name, name, limit=19_999_999)
    for value in values:
        writer.append(value)
    return writer.close(lineage=pins)

context_manifest = write_parts("contexts", (dict(feature=key, examples=value) for key, value in sorted(examples.items())))
tail_manifest = write_parts("tail_literals", (dict(literal=key, occurrences=number) for key, number in unknown_tail.most_common()))
inv.write_json(directory / "manifest.json", dict(status="RAW_SOURCE_COUNTEREXAMPLES_NOT_ADMISSION", rows=packets))
result = dict(status="FULL_REMAINING_RAW_PROFILE_NOT_REPAIR_OR_ADMISSION", pins=pins, counts=dict(counts),
              features=dict(features), field_literals=dict(fields), repeat_shapes=dict(repeat_shapes),
              unknown_tail_literals_manifest=tail_manifest, contexts_manifest=context_manifest,
              packets=len(packets), root_adopted=0, raw_hits_before_edits=True,
              seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.write_json(out / "complete.json", result)
print(json.dumps(dict(status=result["status"], counts=dict(counts), features=len(features), packets=len(packets),
                      seconds=result["seconds"])), flush=True)
