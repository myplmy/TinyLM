"""Read-only profile of actual remaining draft risks; never an admission gate."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import heapq
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inventory
from scripts import p106b_hold_resolution_policy as policy

cache = inventory.cache
base = inventory.BASE
source = base / "draft_proposals_v1"
report = cache.read(source / "complete.json")
out = base / "pending_profile_v1"
inventory.require(not out.exists(), "new immutable profile required")
inventory.verify(source / "unique", report["unique_manifest"])
pin = dict(draft_sha256=inventory.file_sha(source / "complete.json"),
           profiler_sha256=inventory.file_sha(Path(__file__)))
counts = Counter()
features = Counter()
literal_fields = Counter()
heaps = defaultdict(list)
start = last = time.monotonic()
with ExitStack() as stack:
    reader = inventory.OriginalReader(cache.read(base / "scope.json"), stack)
    for row in cache.rows(source / "unique", report["unique_manifest"]):
        if row["decision"] != "PENDING":
            continue
        counts.update(documents=1, occurrences=row["occurrences"])
        if "INDIVIDUAL_SOURCE_REVIEW_NOT_YET_ADOPTED" in row["reasons"]:
            continue
        text, _, _ = reader.text(row)
        kinds = set()
        raw_intro = policy.identified_korean_intro(text)
        stripped_intro = policy.identified_korean_intro(text.lstrip())
        kinds.add("INTRO_RAW" if raw_intro else "INTRO_AFTER_LEADING_SPACE" if stripped_intro else "NO_IDENTIFIED_INTRO")
        if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in row["reasons"]:
            tail = [line.strip() for line in text.splitlines() if line.strip()][-24:]
            anchors = sum(bool(policy.HARD_CATEGORY.fullmatch(line)) for line in tail)
            kinds.add("CATEGORY_ANCHORS_" + str(min(anchors, 2)))
            kinds.add("TAIL_HAS_LINK_LABEL" if any(policy.LINK_OR_REFERENCE.search(line) for line in tail) else "TAIL_NO_LINK_LABEL")
        if "UNRESOLVED_FIELD_OR_TITLE" in row["reasons"]:
            masked = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                             for protected, part in policy.v1.protected_parts(text)[0])
            offset = len(text) - len(text.lstrip())
            first_end = offset + len(text[offset:].split(chr(10) + chr(10), 1)[0])
            hits = list(cache.MISSING_FIELD.finditer(masked)) + list(policy.v1.DANGLING_FIELD.finditer(masked))
            for match in hits:
                literal = match[0]
                literal_fields[literal] += 1
                where = "INTRO" if match.start() < first_end else "AFTER_INTRO"
                kind = "EMPTY_TITLE" if "《" in literal else "EMPTY_COMMA_SLOT" if "," in literal or "，" in literal else "EMPTY_PAREN"
                kinds.add(kind + "/" + where)
            if not hits:
                kinds.add("NO_RAW_FIELD_HIT")
        reason = row["reasons"][0]
        for kind in kinds:
            key = reason + "/" + row["language_bucket"] + "/" + kind
            features[key] += 1
            entry = (-int(row["original_text_sha256"], 16), row["id"], row)
            heap = heaps[key]
            if len(heap) < 2:
                heapq.heappush(heap, entry)
            elif entry[:2] > heap[0][:2]:
                heapq.heapreplace(heap, entry)
        if time.monotonic() - last >= 20:
            print(json.dumps(dict(phase="pending_raw_shape_profile", counts=dict(counts), seconds=round(time.monotonic()-start, 1))), flush=True)
            last = time.monotonic()
    out.mkdir()
    chosen = {}
    for kind, heap in heaps.items():
        for _, _, row in heap:
            chosen.setdefault(row["original_text_sha256"], dict(row, profile_kinds=[]))["profile_kinds"].append(kind)
    directory = out / "review_packets"
    directory.mkdir()
    packets = []
    for row in sorted(chosen.values(), key=lambda x: x["id"]):
        text, _, _ = reader.text(row)
        path = directory / (row["id"].replace(":", "_") + ".txt")
        payload = text.encode("utf-8")
        inventory.require(len(payload) < 20_000_000, "ordered source packet split required")
        with path.open("xb") as stream:
            stream.write(payload)
        packets.append(dict(row, path=str(path.relative_to(ROOT)), sha256=inventory.file_sha(path)))
inventory.require(inventory.file_sha(Path(__file__)) == pin["profiler_sha256"], "profile source changed during run")
value = dict(pin=pin, counts=dict(counts), raw_features=dict(features), raw_field_hits=dict(literal_fields),
             fields_may_overlap=True, source_hits_are_before_draft_edits=True,
             admission="NONE_READ_ONLY_PROFILE", seconds=time.monotonic()-start)
inventory.write_json(directory / "manifest.json", dict(rows=packets, purpose="RAW_RISK_SHAPE_COUNTEREXAMPLES"))
inventory.write_json(out / "complete.json", value)
print(json.dumps(dict(counts=dict(counts), seconds=value["seconds"], packets=len(packets))), flush=True)
